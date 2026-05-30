from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path
from urllib.error import URLError
from unittest.mock import patch

import pandas as pd

from src.cli import normalize_filters
from src.config import Config
from src.main import _apply_runtime_defaults, build_parser
from src.providers import build_provider
from src.providers.base import OnlineDataError
from src.providers.live import TencentLiveProvider
from src.skill import ASharesSkill
from src.utils.time import shanghai_today_str


REPO_ROOT = Path(__file__).resolve().parents[2]


def parse_frontmatter(text: str) -> dict[str, str]:
    lines = text.splitlines()
    assert lines[0] == "---"
    payload: dict[str, str] = {}
    for line in lines[1:]:
        if line == "---":
            break
        key, value = line.split(":", 1)
        payload[key.strip()] = value.strip()
    return payload


def extract_sections(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.startswith("## ")]


def make_offline_config() -> Config:
    return Config(offline_mode=True)


class DummyResponse:
    def __init__(self, text: str):
        self._text = text

    def read(self) -> bytes:
        return self._text.encode("gbk", errors="ignore")

    def __enter__(self) -> "DummyResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


class SkillCompatibilityTests(unittest.TestCase):
    def test_config_defaults_to_offline_mode(self) -> None:
        with patch.dict(os.environ, {"A_SHARE_SKILL_OFFLINE_MODE": ""}, clear=False):
            os.environ.pop("A_SHARE_SKILL_OFFLINE_MODE", None)
            config = Config.from_env()
        self.assertFalse(config.offline_mode)
        self.assertTrue(config.validate())
        self.assertEqual(config.live_source, "tencent")

    def test_self_check_is_available_without_credentials(self) -> None:
        payload = ASharesSkill(config=make_offline_config()).self_check()
        self.assertTrue(payload["config_valid"])
        self.assertEqual(payload["workflow"], "self-check")
        self.assertIn("generated_at", payload)
        self.assertIn("diagnose", payload["supported_scenarios"])
        self.assertIn("market-cycle", payload["supported_scenarios"])
        self.assertIn("playbook", payload["supported_scenarios"])
        self.assertIn("news", payload["supported_scenarios"])
        self.assertIn("health_checks", payload)
        self.assertIn("credential_status", payload)
        self.assertIn("dependency_status", payload)
        check_names = {item["name"] for item in payload["health_checks"]}
        self.assertIn("provider-bootstrap", check_names)
        self.assertIn("quotes", check_names)
        self.assertIn("consensus-eps", check_names)
        self.assertIn("iwencai-search", check_names)

    def test_diagnose_returns_actionable_result(self) -> None:
        payload = ASharesSkill(config=make_offline_config()).diagnose("300750", date="2026-05-28")
        self.assertEqual(payload["risk"]["risk_level"], "R1")
        self.assertIn(payload["conclusion"]["action"], {"可以买", "观望", "不买"})
        self.assertGreater(payload["conclusion"]["target_price"], payload["conclusion"]["stop_loss"])
        self.assertIn("strategy_system", payload)
        self.assertIn("market_cycle", payload["strategy_system"])
        self.assertIn("trade_setup", payload["strategy_system"])
        self.assertIn(payload["strategy_system"]["market_cycle"]["stage"], {"犹豫期/试探期", "亢奋期/加速期", "退潮期/补跌期"})

    def test_risk_scan_blocks_stocks_with_red_flags(self) -> None:
        payload = ASharesSkill(config=make_offline_config()).risk("600290", "2026-04-25")
        self.assertEqual(payload["risk_level"], "R3")
        self.assertIn("退市预警", payload["red_flags"])
        self.assertIn("strategy_discipline", payload)
        self.assertIn("must_avoid", payload["strategy_discipline"])

    def test_stock_picker_accepts_comma_separated_filters(self) -> None:
        self.assertEqual(normalize_filters(["basic,tech"]), ["basic", "tech"])

    def test_run_skill_cli_outputs_json(self) -> None:
        env = {
            **os.environ,
            "PYTHONDONTWRITEBYTECODE": "1",
            "A_SHARE_SKILL_OFFLINE_MODE": "true",
        }
        result = subprocess.run(
            [sys.executable, "scripts/run_skill.py", "--format", "json", "risk", "--code", "300750"],
            cwd=REPO_ROOT,
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )
        payload = json.loads(result.stdout)
        self.assertEqual(payload["stock_code"], "300750")

    def test_module_entrypoint_outputs_json(self) -> None:
        env = {
            **os.environ,
            "PYTHONDONTWRITEBYTECODE": "1",
            "A_SHARE_SKILL_OFFLINE_MODE": "true",
        }
        result = subprocess.run(
            [sys.executable, "-m", "src.main", "--format", "json", "self-check"],
            cwd=REPO_ROOT,
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )
        payload = json.loads(result.stdout)
        self.assertEqual(payload["workflow"], "self-check")

    def test_main_applies_runtime_date_defaults(self) -> None:
        parser = build_parser()
        args = _apply_runtime_defaults(parser.parse_args(["quick-research", "--code", "300750"]))
        self.assertEqual(args.date, shanghai_today_str())
        market_cycle_args = _apply_runtime_defaults(parser.parse_args(["market-cycle"]))
        self.assertEqual(market_cycle_args.date, shanghai_today_str())

    def test_full_stack_skill_endpoints_work_in_offline_mode(self) -> None:
        skill = ASharesSkill(config=make_offline_config())
        picks = skill.pick(["basic", "tech"])
        self.assertTrue(skill.stock_news("300750", 2)["items"])
        self.assertTrue(skill.market_telegraph(2)["items"])
        self.assertTrue(skill.global_news(2)["items"])
        self.assertTrue(skill.announcements("300750", 2)["items"])
        self.assertTrue(skill.fund_flow("300750", "minute")["items"])
        self.assertTrue(skill.fund_flow("300750", "120d", 5)["items"])
        self.assertTrue(skill.sector_rankings(2)["top"])
        self.assertTrue(skill.hot_stocks("2026-05-28", 2)["items"])
        self.assertTrue(skill.concept_blocks("300750")["concept"])
        self.assertTrue(skill.research_reports("300750", 2)["items"])
        self.assertTrue(skill.dragon_tiger("300750", "2026-05-28", 30)["records"])
        self.assertTrue(skill.daily_dragon_tiger("2026-05-28")["stocks"])
        self.assertTrue(skill.margin_trading("300750", 2)["items"])
        self.assertTrue(skill.block_trades("300750", 2)["items"])
        self.assertTrue(skill.holder_numbers("300750", 2)["items"])
        self.assertTrue(skill.dividend_history("300750", 2)["items"])
        self.assertTrue(skill.lockup_expiry("300750", "2026-05-28", 90)["history"])
        self.assertTrue(skill.northbound_flow(5)["history"])
        self.assertEqual(skill.stock_info("300750")["code"], "300750")
        self.assertTrue(skill.realtime_quotes(["300750", "000300", "510300"])["items"])
        market_cycle = skill.market_cycle_report("2026-05-28")
        playbook = skill.strategy_playbook("300750", "2026-05-28")
        valuation = skill.valuation("300750")
        self.assertEqual(valuation["stock_code"], "300750")
        self.assertEqual(valuation["workflow"], "valuation")
        self.assertIn("coverage", valuation)
        self.assertTrue(skill.compare_valuations(["300750", "002594"])["items"])
        self.assertEqual(market_cycle["workflow"], "market-cycle")
        self.assertEqual(playbook["workflow"], "playbook")
        self.assertIn("buy_strategy", market_cycle["playbook"])
        self.assertIn("entry_signals", playbook["playbook"])
        self.assertTrue(picks)
        self.assertIn("methodology_score", picks[0])
        self.assertIn("style", picks[0])
        theme_research = skill.thematic_research(["机器人", "储能"], "report", 2, 1)
        self.assertTrue(theme_research["available"])
        self.assertEqual(theme_research["workflow"], "theme-research")
        self.assertIn("query_hits", theme_research)
        self.assertTrue(theme_research["articles"])
        self.assertTrue(theme_research["supplements"])
        research = skill.quick_research("300750", "2026-05-28")
        self.assertEqual(research["stock_code"], "300750")
        self.assertEqual(research["workflow"], "quick-research")
        self.assertIn("summary", research)
        self.assertIn("strategy_system", research)
        self.assertTrue(skill.price_bars("300750", 4, 3)["items"])
        self.assertTrue(skill.order_book("300750")["bids"])
        self.assertTrue(skill.transactions("300750", 0, 3)["items"])
        self.assertTrue(skill.financial_snapshot("300750")["data"])
        self.assertTrue(skill.f10_profile("300750")["items"])
        self.assertTrue(skill.financial_report("300750", "lrb", 2)["items"])
        self.assertTrue(skill.consensus_eps("300750")["items"])
        self.assertTrue(skill.iwencai_search("机器人", "report", 2)["items"])
        self.assertTrue(skill.iwencai_query("宁德时代 ROE", 1, 2)["items"])

    def test_run_skill_cli_supports_news_command(self) -> None:
        env = {
            **os.environ,
            "PYTHONDONTWRITEBYTECODE": "1",
            "A_SHARE_SKILL_OFFLINE_MODE": "true",
        }
        result = subprocess.run(
            [sys.executable, "scripts/run_skill.py", "--format", "json", "news", "--code", "300750", "--page-size", "2"],
            cwd=REPO_ROOT,
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )
        payload = json.loads(result.stdout)
        self.assertEqual(payload["stock_code"], "300750")
        self.assertEqual(len(payload["items"]), 2)

    def test_run_skill_cli_supports_hot_stocks_command(self) -> None:
        env = {
            **os.environ,
            "PYTHONDONTWRITEBYTECODE": "1",
            "A_SHARE_SKILL_OFFLINE_MODE": "true",
        }
        result = subprocess.run(
            [sys.executable, "scripts/run_skill.py", "--format", "json", "hot-stocks", "--date", "2026-05-28", "--page-size", "2"],
            cwd=REPO_ROOT,
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )
        payload = json.loads(result.stdout)
        self.assertEqual(len(payload["items"]), 2)
        self.assertEqual(payload["items"][0]["code"], "300750")

    def test_run_skill_cli_supports_quotes_command(self) -> None:
        env = {
            **os.environ,
            "PYTHONDONTWRITEBYTECODE": "1",
            "A_SHARE_SKILL_OFFLINE_MODE": "true",
        }
        result = subprocess.run(
            [sys.executable, "scripts/run_skill.py", "--format", "json", "quotes", "--codes", "300750,000300,510300", "--kind", "auto"],
            cwd=REPO_ROOT,
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )
        payload = json.loads(result.stdout)
        self.assertTrue(payload["available"])
        self.assertEqual(len(payload["items"]), 3)

    def test_run_skill_cli_supports_valuation_command(self) -> None:
        env = {
            **os.environ,
            "PYTHONDONTWRITEBYTECODE": "1",
            "A_SHARE_SKILL_OFFLINE_MODE": "true",
        }
        result = subprocess.run(
            [sys.executable, "scripts/run_skill.py", "--format", "json", "valuation", "--code", "300750"],
            cwd=REPO_ROOT,
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )
        payload = json.loads(result.stdout)
        self.assertEqual(payload["stock_code"], "300750")
        self.assertIsNotNone(payload["pe_fwd"])

    def test_run_skill_cli_supports_compare_command(self) -> None:
        env = {
            **os.environ,
            "PYTHONDONTWRITEBYTECODE": "1",
            "A_SHARE_SKILL_OFFLINE_MODE": "true",
        }
        result = subprocess.run(
            [sys.executable, "scripts/run_skill.py", "--format", "json", "compare", "--codes", "300750,002594"],
            cwd=REPO_ROOT,
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )
        payload = json.loads(result.stdout)
        self.assertEqual(len(payload["items"]), 2)

    def test_run_skill_cli_supports_theme_research_command(self) -> None:
        env = {
            **os.environ,
            "PYTHONDONTWRITEBYTECODE": "1",
            "A_SHARE_SKILL_OFFLINE_MODE": "true",
        }
        result = subprocess.run(
            [
                sys.executable,
                "scripts/run_skill.py",
                "--format",
                "json",
                "theme-research",
                "--queries",
                "机器人,储能",
                "--channel",
                "report",
                "--size",
                "2",
                "--supplement-per-stock",
                "1",
            ],
            cwd=REPO_ROOT,
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )
        payload = json.loads(result.stdout)
        self.assertTrue(payload["available"])
        self.assertEqual(payload["queries"], ["机器人", "储能"])
        self.assertTrue(payload["articles"])
        self.assertTrue(payload["supplements"])

    def test_run_skill_cli_supports_quick_research_command(self) -> None:
        env = {
            **os.environ,
            "PYTHONDONTWRITEBYTECODE": "1",
            "A_SHARE_SKILL_OFFLINE_MODE": "true",
        }
        result = subprocess.run(
            [sys.executable, "scripts/run_skill.py", "--format", "json", "quick-research", "--code", "300750", "--date", "2026-05-28"],
            cwd=REPO_ROOT,
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )
        payload = json.loads(result.stdout)
        self.assertEqual(payload["stock_code"], "300750")
        self.assertIn("valuation", payload)

    def test_run_skill_cli_supports_market_cycle_command(self) -> None:
        env = {
            **os.environ,
            "PYTHONDONTWRITEBYTECODE": "1",
            "A_SHARE_SKILL_OFFLINE_MODE": "true",
        }
        result = subprocess.run(
            [sys.executable, "scripts/run_skill.py", "--format", "json", "market-cycle", "--date", "2026-05-28"],
            cwd=REPO_ROOT,
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )
        payload = json.loads(result.stdout)
        self.assertEqual(payload["workflow"], "market-cycle")
        self.assertIn("playbook", payload)

    def test_run_skill_cli_supports_playbook_command(self) -> None:
        env = {
            **os.environ,
            "PYTHONDONTWRITEBYTECODE": "1",
            "A_SHARE_SKILL_OFFLINE_MODE": "true",
        }
        result = subprocess.run(
            [sys.executable, "scripts/run_skill.py", "--format", "json", "playbook", "--code", "300750", "--date", "2026-05-28"],
            cwd=REPO_ROOT,
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )
        payload = json.loads(result.stdout)
        self.assertEqual(payload["workflow"], "playbook")
        self.assertEqual(payload["stock_code"], "300750")
        self.assertIn("entry_signals", payload["playbook"])

    def test_run_skill_cli_supports_quarterly_snapshot_command(self) -> None:
        env = {
            **os.environ,
            "PYTHONDONTWRITEBYTECODE": "1",
            "A_SHARE_SKILL_OFFLINE_MODE": "true",
        }
        result = subprocess.run(
            [sys.executable, "scripts/run_skill.py", "--format", "json", "quarterly-snapshot", "--code", "300750"],
            cwd=REPO_ROOT,
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )
        payload = json.loads(result.stdout)
        self.assertTrue(payload["available"])
        self.assertEqual(payload["stock_code"], "300750")

    def test_run_skill_cli_supports_kline_command(self) -> None:
        env = {
            **os.environ,
            "PYTHONDONTWRITEBYTECODE": "1",
            "A_SHARE_SKILL_OFFLINE_MODE": "true",
        }
        result = subprocess.run(
            [sys.executable, "scripts/run_skill.py", "--format", "json", "kline", "--code", "300750", "--frequency", "4", "--limit", "3"],
            cwd=REPO_ROOT,
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )
        payload = json.loads(result.stdout)
        self.assertTrue(payload["available"])
        self.assertEqual(len(payload["items"]), 3)

    def test_run_skill_cli_supports_order_book_command(self) -> None:
        env = {
            **os.environ,
            "PYTHONDONTWRITEBYTECODE": "1",
            "A_SHARE_SKILL_OFFLINE_MODE": "true",
        }
        result = subprocess.run(
            [sys.executable, "scripts/run_skill.py", "--format", "json", "order-book", "--code", "300750"],
            cwd=REPO_ROOT,
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )
        payload = json.loads(result.stdout)
        self.assertTrue(payload["available"])
        self.assertEqual(len(payload["bids"]), 5)

    def test_run_skill_cli_supports_transactions_command(self) -> None:
        env = {
            **os.environ,
            "PYTHONDONTWRITEBYTECODE": "1",
            "A_SHARE_SKILL_OFFLINE_MODE": "true",
        }
        result = subprocess.run(
            [sys.executable, "scripts/run_skill.py", "--format", "json", "transactions", "--code", "300750", "--start", "0", "--limit", "2"],
            cwd=REPO_ROOT,
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )
        payload = json.loads(result.stdout)
        self.assertTrue(payload["available"])
        self.assertEqual(len(payload["items"]), 2)

    def test_run_skill_cli_supports_f10_command(self) -> None:
        env = {
            **os.environ,
            "PYTHONDONTWRITEBYTECODE": "1",
            "A_SHARE_SKILL_OFFLINE_MODE": "true",
        }
        result = subprocess.run(
            [sys.executable, "scripts/run_skill.py", "--format", "json", "f10", "--code", "300750", "--category", "最新提示"],
            cwd=REPO_ROOT,
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )
        payload = json.loads(result.stdout)
        self.assertTrue(payload["available"])
        self.assertIn("最新提示", payload["items"])

    def test_run_skill_cli_supports_dragon_tiger_command(self) -> None:
        env = {
            **os.environ,
            "PYTHONDONTWRITEBYTECODE": "1",
            "A_SHARE_SKILL_OFFLINE_MODE": "true",
        }
        result = subprocess.run(
            [
                sys.executable,
                "scripts/run_skill.py",
                "--format",
                "json",
                "dragon-tiger",
                "--code",
                "300750",
                "--date",
                "2026-05-28",
            ],
            cwd=REPO_ROOT,
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )
        payload = json.loads(result.stdout)
        self.assertEqual(payload["stock_code"], "300750")
        self.assertTrue(payload["records"])

    def test_run_skill_cli_supports_lockup_command(self) -> None:
        env = {
            **os.environ,
            "PYTHONDONTWRITEBYTECODE": "1",
            "A_SHARE_SKILL_OFFLINE_MODE": "true",
        }
        result = subprocess.run(
            [
                sys.executable,
                "scripts/run_skill.py",
                "--format",
                "json",
                "lockup",
                "--code",
                "300750",
                "--date",
                "2026-05-28",
            ],
            cwd=REPO_ROOT,
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )
        payload = json.loads(result.stdout)
        self.assertEqual(payload["stock_code"], "300750")
        self.assertTrue(payload["history"])

    def test_run_skill_cli_supports_stock_info_command(self) -> None:
        env = {
            **os.environ,
            "PYTHONDONTWRITEBYTECODE": "1",
            "A_SHARE_SKILL_OFFLINE_MODE": "true",
        }
        result = subprocess.run(
            [sys.executable, "scripts/run_skill.py", "--format", "json", "stock-info", "--code", "300750"],
            cwd=REPO_ROOT,
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )
        payload = json.loads(result.stdout)
        self.assertEqual(payload["code"], "300750")

    def test_run_skill_cli_supports_consensus_eps_command(self) -> None:
        env = {
            **os.environ,
            "PYTHONDONTWRITEBYTECODE": "1",
            "A_SHARE_SKILL_OFFLINE_MODE": "true",
        }
        result = subprocess.run(
            [sys.executable, "scripts/run_skill.py", "--format", "json", "consensus-eps", "--code", "300750"],
            cwd=REPO_ROOT,
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )
        payload = json.loads(result.stdout)
        self.assertEqual(payload["stock_code"], "300750")
        self.assertTrue(payload["items"])

    def test_iwencai_returns_structured_error_without_key(self) -> None:
        payload = ASharesSkill(config=Config()).iwencai_search("机器人", "report", 5)
        self.assertFalse(payload["available"])
        self.assertIn("IWENCAI_API_KEY", payload["error"])

    def test_theme_research_returns_structured_error_without_key(self) -> None:
        payload = ASharesSkill(config=Config()).thematic_research(["机器人"], "report", 5, 1)
        self.assertFalse(payload["available"])
        self.assertEqual(payload["workflow"], "theme-research")
        self.assertIn("IWENCAI_API_KEY", payload["error"])
        self.assertIn("iwencai_unavailable", payload["degraded_reasons"])
        self.assertIn("IWENCAI_API_KEY", payload["errors"][0])
        self.assertEqual(payload["articles"], [])

    def test_news_returns_structured_error_when_provider_fails(self) -> None:
        skill = ASharesSkill(config=make_offline_config())
        with patch.object(skill.provider, "get_stock_news", side_effect=RuntimeError("news down")):
            payload = skill.stock_news("300750", 2)
        self.assertFalse(payload["available"])
        self.assertEqual(payload["items"], [])
        self.assertIn("news down", payload["error"])

    def test_self_check_reports_degraded_capabilities_in_live_mode(self) -> None:
        skill = ASharesSkill(config=Config())
        with (
            patch.object(skill.provider, "list_stock_candidates", return_value=[]),
            patch.object(skill, "realtime_quotes", return_value={"available": False, "error": "quote down", "items": []}),
            patch.object(skill, "consensus_eps", return_value={"available": True, "items": []}),
        ):
            payload = skill.self_check()
        self.assertFalse(payload["available"])
        self.assertIn("valuation", payload["degraded_reasons"])
        self.assertTrue(payload["recommended_actions"])
        self.assertEqual(payload["sample_stock_codes"][0], "300750")

    def test_skill_frontmatter_is_agent_friendly(self) -> None:
        text = (REPO_ROOT / "SKILL.md").read_text(encoding="utf-8")
        frontmatter = parse_frontmatter(text)
        metadata = json.loads(frontmatter["metadata"])
        self.assertEqual(frontmatter["name"], "a-shares-master")
        self.assertEqual(frontmatter["user-invocable"], "true")
        description = frontmatter["description"].strip('"')
        self.assertLessEqual(len(description), 60)
        self.assertTrue(description.endswith("."))
        self.assertEqual(frontmatter["platforms"], "[linux, macos]")
        self.assertEqual(metadata["openclaw"]["skillKey"], "a-shares-master")
        self.assertIn("python3", metadata["openclaw"]["requires"]["bins"])
        env_vars = {item["name"] for item in metadata["openclaw"]["envVars"]}
        self.assertIn("A_SHARE_SKILL_OFFLINE_MODE", env_vars)
        self.assertEqual(metadata["hermes"]["category"], "research")
        self.assertIn("stocks", metadata["hermes"]["tags"])
        self.assertIn("## Verification", text)

    def test_pyproject_declares_console_script_and_dev_extra(self) -> None:
        text = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
        self.assertIn("[project.scripts]", text)
        self.assertIn('a-shares-skill = "src.main:main"', text)
        self.assertIn("dev =", text)

    def test_ci_workflow_exists(self) -> None:
        text = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
        self.assertIn("actions/setup-python", text)
        self.assertIn("python -m src.main --format json self-check", text)
        self.assertIn("sh scripts/run_tests.sh", text)

    def test_skill_body_follows_hermes_section_order(self) -> None:
        text = (REPO_ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("# A-Shares Master Skill", text)
        sections = extract_sections(text)
        self.assertEqual(
            sections,
            [
                "## When To Use",
                "## Prerequisites",
                "## How To Run",
                "## Quick Reference",
                "## Procedure",
                "## Pitfalls",
                "## Verification",
            ],
        )

    def test_run_tests_script_supports_single_test_target(self) -> None:
        if os.environ.get("A_SHARE_SKILL_NESTED_TEST") == "1":
            return
        env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
        env["A_SHARE_SKILL_NESTED_TEST"] = "1"
        env["A_SHARE_SKILL_OFFLINE_MODE"] = "true"
        result = subprocess.run(
            [
                "sh",
                "scripts/run_tests.sh",
                "tests/skills/test_a_shares_master_skill.py",
            ],
            cwd=REPO_ROOT,
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )
        output = result.stdout + result.stderr
        self.assertIn("OK", output)

    def test_provider_factory_prefers_live_source_by_default(self) -> None:
        with patch.dict(os.environ, {"A_SHARE_SKILL_OFFLINE_MODE": ""}, clear=False):
            os.environ.pop("A_SHARE_SKILL_OFFLINE_MODE", None)
            provider = build_provider(Config())
        self.assertEqual(provider.source_name, "live-tencent-finance")

    def test_live_provider_parses_online_quote_payload(self) -> None:
        quote_text = (
            'v_sz300750="51~宁德时代~300750~414.80~402.50~413.92~533729~257157~276572~414.80~8~414.79~2~414.77~8~414.76~1~414.75~11~414.81~8~414.84~22~414.88~2~414.89~1~414.92~6~~20260527161424~12.30~3.06~428.90~411.29~414.80/533729/22373358897~533729~2237336~1.25~24.30~~428.90~411.29~4.38~17657.60~19190.76~5.87~483.00~322.00~1.64~-9~419.19~23.14~26.58~~~1.17~2237335.8897~41.4800~10~ A~GP-A-CYB~15.11~0.01~1.88~22.11~8.09~468.75~230.12~-4.43~-6.77~22.33~4256894122~4626509252~-13.04~48.00~4256894122~~~68.56~-0.17~~CNY~0~~415.00~-256~";'
        )
        kline_text = json.dumps(
            {
                "code": 0,
                "data": {
                    "sz300750": {
                        "qfqday": [
                            ["2026-05-01", "400.00", "401.00", "403.00", "398.00", "100000.000"],
                            ["2026-05-02", "401.00", "402.00", "404.00", "399.00", "100000.000"],
                            ["2026-05-03", "402.00", "403.00", "405.00", "400.00", "100000.000"],
                            ["2026-05-04", "403.00", "404.00", "406.00", "401.00", "100000.000"],
                            ["2026-05-05", "404.00", "405.00", "407.00", "402.00", "100000.000"],
                            ["2026-05-06", "405.00", "406.00", "408.00", "403.00", "100000.000"],
                            ["2026-05-07", "406.00", "407.00", "409.00", "404.00", "100000.000"],
                            ["2026-05-08", "407.00", "408.00", "410.00", "405.00", "100000.000"],
                            ["2026-05-09", "408.00", "409.00", "411.00", "406.00", "100000.000"],
                            ["2026-05-10", "409.00", "410.00", "412.00", "407.00", "100000.000"],
                            ["2026-05-11", "410.00", "411.00", "413.00", "408.00", "100000.000"],
                            ["2026-05-12", "411.00", "412.00", "414.00", "409.00", "100000.000"],
                            ["2026-05-13", "412.00", "413.00", "415.00", "410.00", "100000.000"],
                            ["2026-05-14", "413.00", "414.00", "416.00", "411.00", "100000.000"],
                            ["2026-05-15", "414.00", "415.00", "417.00", "412.00", "100000.000"],
                            ["2026-05-16", "415.00", "416.00", "418.00", "413.00", "100000.000"],
                            ["2026-05-17", "416.00", "417.00", "419.00", "414.00", "100000.000"],
                            ["2026-05-18", "417.00", "418.00", "420.00", "415.00", "100000.000"],
                            ["2026-05-19", "418.00", "419.00", "421.00", "416.00", "100000.000"],
                            ["2026-05-20", "419.00", "420.00", "422.00", "417.00", "100000.000"],
                        ]
                    }
                },
            },
            ensure_ascii=False,
        )

        def fake_urlopen(request, timeout=0):
            url = request.full_url
            if "qt.gtimg.cn" in url:
                return DummyResponse(quote_text)
            if "fqkline" in url:
                return DummyResponse(kline_text)
            raise AssertionError(url)

        with patch("src.providers.live.urlopen", side_effect=fake_urlopen):
            provider = TencentLiveProvider(Config())
            snapshot = provider.get_stock_snapshot("300750")
        self.assertEqual(snapshot.code, "300750")
        self.assertEqual(snapshot.name, "宁德时代")
        self.assertEqual(snapshot.data_source, "live-tencent-finance")
        self.assertGreater(snapshot.ma20, 0)
        self.assertGreater(snapshot.turnover_million, 0)

    def test_live_provider_wraps_network_errors_with_online_data_error(self) -> None:
        provider = TencentLiveProvider(Config())
        with patch("src.providers.live.urlopen", side_effect=URLError("timeout")):
            with self.assertRaises(OnlineDataError):
                provider._http_get_json("https://example.com/api")

    def test_live_provider_parses_full_stack_payloads(self) -> None:
        provider = TencentLiveProvider(Config())
        news_jsonp = json.dumps(
            {
                "result": {
                    "cmsArticleWebOld": {
                        "list": [
                            {
                                "title": "<em>宁德时代</em> 获机构看好",
                                "content": "<p>盈利预测继续上修</p>",
                                "date": "2026-05-29 09:30:00",
                                "mediaName": "东财",
                                "url": "https://example.com/news1",
                            }
                        ]
                    }
                }
            },
            ensure_ascii=False,
        )
        telegraph_payload = {
            "data": {
                "roll_data": [
                    {"title": "财联社快讯", "content": "市场情绪回暖", "ctime": "2026-05-29 10:00:00"}
                ]
            }
        }
        global_news_payload = {
            "data": {
                "fastNewsList": [
                    {"title": "全球市场波动", "summary": "美元指数回落", "showTime": "2026-05-29 10:05:00"}
                ]
            }
        }
        sector_payload = {
            "data": {
                "diff": [
                    {"f14": "储能", "f3": 2.31, "f12": "BK1001", "f104": 12, "f105": 3, "f140": "宁德时代", "f136": 3.5},
                    {"f14": "白酒", "f3": -1.25, "f12": "BK1002", "f104": 2, "f105": 14, "f140": "贵州茅台", "f136": -0.8},
                ]
            }
        }
        breadth_payload = {
            "data": {
                "diff": [
                    {"f12": "300750", "f14": "宁德时代", "f3": 3.07, "f6": 22373358897},
                    {"f12": "002594", "f14": "比亚迪", "f3": 1.25, "f6": 18200000000},
                    {"f12": "600519", "f14": "贵州茅台", "f3": 0.0, "f6": 9800000000},
                    {"f12": "600036", "f14": "招商银行", "f3": -1.42, "f6": 7600000000},
                ]
            }
        }
        hot_stocks_payload = {
            "errocode": 0,
            "data": [
                {
                    "code": "300750",
                    "name": "宁德时代",
                    "reason": "储能+固态电池",
                    "close": "412.50",
                    "zhangdie": "12.30",
                    "zhangfu": "3.07",
                    "huanshou": "5.87",
                    "chengjiaoe": "22373358897",
                    "chengjiaoliang": "53372900",
                    "ddejingliang": "1.17",
                    "market": "创业板",
                }
            ],
        }
        hot_stocks_sparse_payload = {
            "errocode": 0,
            "data": [
                {
                    "code": "300750",
                    "name": "宁德时代",
                    "reason": "储能+固态电池",
                    "close": "",
                    "zhangdie": "",
                    "zhangfu": "",
                    "huanshou": "",
                    "chengjiaoe": "",
                    "chengjiaoliang": "",
                    "ddejingliang": "",
                    "market": "创业板",
                }
            ],
        }
        report_payload = {
            "data": [
                {
                    "title": "盈利预测上修",
                    "publishDate": "2026-05-28 08:00:00",
                    "orgSName": "中信证券",
                    "emRatingName": "买入",
                    "predictThisYearEps": 12.3,
                    "predictNextYearEps": 13.4,
                    "predictNextTwoYearEps": 14.5,
                    "indvInduName": "储能",
                    "infoCode": "ABC123",
                }
            ]
        }
        minute_payload = {
            "data": {
                "klines": [
                    "2026-05-29 09:31,1000000,-200000,100000,50000,30000",
                    "2026-05-29 09:32,1200000,-150000,120000,60000,40000",
                ]
            }
        }
        fund_120d_payload = {
            "data": {
                "klines": [
                    "2026-05-28,10000000,-2000000,1000000,600000,400000",
                    "2026-05-29,11000000,-1800000,1200000,700000,450000",
                ]
            }
        }
        announcement_payload = {
            "announcements": [
                {
                    "announcementTitle": "<em>宁德时代</em> 关于回购股份的公告",
                    "announcementTypeName": "临时公告",
                    "announcementTime": 1780012800000,
                    "announcementId": "123456",
                }
            ]
        }
        datacenter_payloads = {
            "RPT_DAILYBILLBOARD_DETAILSNEW": [
                {
                    "TRADE_DATE": "2026-05-29",
                    "EXPLANATION": "日涨幅偏离值达7%",
                    "BILLBOARD_NET_AMT": 50_000_000,
                    "TURNOVERRATE": 12.5,
                    "SECURITY_CODE": "300750",
                    "SECURITY_NAME_ABBR": "宁德时代",
                    "CLOSE_PRICE": 420.5,
                    "CHANGE_RATE": 4.32,
                    "BILLBOARD_BUY_AMT": 80_000_000,
                    "BILLBOARD_SELL_AMT": 30_000_000,
                }
            ],
            "RPT_BILLBOARD_DAILYDETAILSBUY": [
                {"OPERATEDEPT_NAME": "机构专用", "BUY": 20_000_000, "SELL": 1_000_000, "NET": 19_000_000, "OPERATEDEPT_CODE": "0"},
                {"OPERATEDEPT_NAME": "某游资席位", "BUY": 10_000_000, "SELL": 2_000_000, "NET": 8_000_000, "OPERATEDEPT_CODE": "123"},
            ],
            "RPT_BILLBOARD_DAILYDETAILSSELL": [
                {"OPERATEDEPT_NAME": "机构专用", "BUY": 500_000, "SELL": 6_000_000, "NET": -5_500_000, "OPERATEDEPT_CODE": "0"}
            ],
            "RPTA_WEB_RZRQ_GGMX": [
                {"DATE": "2026-05-29", "RZYE": 1_000_000_000, "RZMRE": 80_000_000, "RZCHE": 75_000_000, "RQYE": 50_000_000, "RQMCL": 12_000, "RQCHL": 11_000, "RZRQYE": 1_050_000_000}
            ],
            "RPT_DATA_BLOCKTRADE": [
                {"TRADE_DATE": "2026-05-28", "DEAL_PRICE": 410.0, "DEAL_NUM": 100_000, "DEAL_AMT": 41_000_000, "BUYER_NAME": "机构专用", "SELLER_NAME": "某营业部", "CLOSE_PRICE": 420.0}
            ],
            "RPT_HOLDERNUMLATEST": [
                {"END_DATE": "2026-03-31", "HOLDER_NUM": 520000, "HOLDER_NUM_CHANGE": -18000, "HOLDER_NUM_RATIO": -3.35, "AVG_FREE_SHARES": 11200}
            ],
            "RPT_SHAREBONUS_DET": [
                {"EX_DIVIDEND_DATE": "2026-05-20", "PRETAX_BONUS_RMB": 1.2, "TRANSFER_RATIO": 0, "BONUS_RATIO": 0, "ASSIGN_PROGRESS": "实施完成"}
            ],
            "RPT_LIFT_STAGE": [
                {"FREE_DATE": "2026-04-15", "LIMITED_STOCK_TYPE": "股权激励限售股份", "FREE_SHARES_NUM": 12_000_000, "FREE_RATIO": 0.45},
                {"FREE_DATE": "2026-07-20", "LIMITED_STOCK_TYPE": "首发机构配售股份", "FREE_SHARES_NUM": 25_000_000, "FREE_RATIO": 0.92},
            ],
        }
        northbound_payload = {
            "time": ["09:30", "10:30", "15:00"],
            "hgt": [5.2, 12.6, 18.4],
            "sgt": [3.8, 8.1, 11.7],
        }
        stock_info_payload = {
            "data": {
                "f57": "300750",
                "f58": "宁德时代",
                "f84": 2_500_000_000,
                "f85": 2_100_000_000,
                "f127": "电池",
                "f116": 1_000_000_000_000,
                "f117": 850_000_000_000,
                "f189": 20180611,
                "f43": 412.5,
            }
        }
        finance_payload = {
            "result": {
                "data": {
                    "report_list": {
                        "20260331": {
                            "data": [
                                {"item_title": "净利润", "item_value": "13963200000"},
                                {"item_title": "营业总收入", "item_value": "84705000000"},
                            ]
                        }
                    }
                }
            }
        }
        class FakeMootdxClient:
            def bars(self, symbol: str, frequency: int = 4, offset: int = 20):
                return pd.DataFrame(
                    [
                        {"open": 411.28, "close": 402.88, "high": 414.5, "low": 400.0, "vol": 381977.0, "amount": 15479408640.0, "datetime": "2026-05-25 15:00"},
                        {"open": 406.19, "close": 402.5, "high": 408.77, "low": 400.36, "vol": 350627.0, "amount": 14152427520.0, "datetime": "2026-05-26 15:00"},
                    ]
                )

            def quotes(self, symbol=None, **kwargs):
                return pd.DataFrame(
                    [
                        {
                            "market": 0,
                            "code": "300750",
                            "price": 424.79,
                            "last_close": 415.68,
                            "open": 423.0,
                            "high": 430.86,
                            "low": 416.55,
                            "servertime": "13:52:12.132",
                            "vol": 368205,
                            "amount": 15639648256.0,
                            "bid1": 424.78,
                            "ask1": 424.79,
                            "bid_vol1": 2,
                            "ask_vol1": 3,
                            "bid2": 424.77,
                            "ask2": 424.80,
                            "bid_vol2": 14,
                            "ask_vol2": 22,
                            "bid3": 424.76,
                            "ask3": 424.81,
                            "bid_vol3": 4,
                            "ask_vol3": 2,
                            "bid4": 424.75,
                            "ask4": 424.85,
                            "bid_vol4": 17,
                            "ask_vol4": 1,
                            "bid5": 424.74,
                            "ask5": 424.86,
                            "bid_vol5": 3,
                            "ask_vol5": 8,
                        }
                    ]
                )

            def transaction(self, symbol: str, start: int = 0, offset: int = 50, **kwargs):
                return pd.DataFrame(
                    [
                        {"time": "13:16", "price": 427.4, "vol": 29, "num": 18, "buyorsell": 1},
                        {"time": "13:16", "price": 427.4, "vol": 16, "num": 13, "buyorsell": 1},
                        {"time": "13:16", "price": 427.3, "vol": 23, "num": 12, "buyorsell": 1},
                    ]
                )

            def finance(self, symbol: str):
                return {
                    "eps": 5.58,
                    "roe": 24.8,
                    "profit": 13_963_200_000,
                    "income": 84_705_000_000,
                    "liutongguben": 2_100_000_000,
                    "zongguben": 2_500_000_000,
                }

            def F10(self, symbol: str, name: str):
                return f"{name}\n这是 {symbol} 的样例 F10 文本。"

        consensus_html = """
        <table class="m_table m_hl">
          <caption class="hltip m_cap"><span class="fr tip">单位：元</span>汇总--预测年报每股收益</caption>
          <tbody>
            <tr><th>2026</th><td class="tc">31</td><td>19.13</td><td>20.77</td><td>22.57</td><td>2.58</td></tr>
            <tr><th>2027</th><td class="tc">30</td><td>22.90</td><td>25.72</td><td>29.52</td><td>3.29</td></tr>
          </tbody>
        </table>
        """
        concept_html = """
        <table class="gnContent">
          <tbody>
            <tr>
              <td>1</td>
              <td class="gnName" clid="1">储能</td>
              <td><a class="gnltg" href="javascript:void(0)" code="300750">宁德时代</a></td>
              <td class="wider">新能源链条核心概念</td>
            </tr>
          </tbody>
        </table>
        """
        quote_text = (
            'v_sz300750="51~宁德时代~300750~424.79~415.68~423.00~~~~~~~ ~20260529140101~8.55~2.06~430.86~416.55~424.79/373574/15867486208~373574~1586749~1.25~24.30~~430.86~416.55~3.44~410.88~380.12~4.52~457.25~374.11~1.98";'
            'v_sh000001="1~上证指数~000001~3098.76~3075.20~3080.00~~~~~~~ ~20260529140101~23.56~0.77~3102.50~3068.90~0/0/154000000000~0~1540000~0.00~0.00~~3102.50~3068.90~1.09~0~0~0~0~0~0";'
            'v_sh000300="1~沪深300~000300~3812.45~3798.12~3805.00~~~~~~~ ~20260529140101~14.33~0.38~3821.20~3792.80~0/0/0~0~0~0.00~0.00~~3821.20~3792.80~0.75~0~0~0~0~0~0";'
            'v_sz399001="0~深证成指~399001~9588.66~9522.18~9530.00~~~~~~~ ~20260529140101~66.48~0.70~9601.20~9490.50~0/0/132000000000~0~1320000~0.00~0.00~~9601.20~9490.50~1.16~0~0~0~0~0~0";'
            'v_sz399006="0~创业板指~399006~1888.88~1866.66~1870.00~~~~~~~ ~20260529140101~22.22~1.19~1895.10~1858.00~0/0/64000000000~0~640000~0.00~0.00~~1895.10~1858.00~1.99~0~0~0~0~0~0";'
            'v_sh510300="51~沪深300ETF~510300~3.912~3.876~3.884~~~~~~~ ~20260529140101~0.036~0.93~3.926~3.871~18652300/0/0~186523~0~2.14~0.00~~3.926~3.871~1.42~0~0~0~0~0~0";'
        )
        iwencai_search_payload = {
            "status_code": 0,
            "data": [
                {"uid": "1", "title": "机器人行业深度", "publish_date": "2026-05-28", "score": 95, "extra": {"organization": "中信证券"}},
                {"uid": "1", "title": "机器人行业深度", "publish_date": "2026-05-28", "score": 90, "extra": {"organization": "中信证券"}},
            ],
        }
        iwencai_query_payload = {
            "status_code": 0,
            "datas": [{"股票代码": "300750", "股票简称": "宁德时代", "ROE": 24.8}],
        }

        def fake_get_text(url: str, encoding: str = "gbk") -> str:
            if "qt.gtimg.cn" in url:
                return quote_text
            if "search-api-web.eastmoney.com" in url:
                return f"jQuery_news({news_jsonp})"
            if "basic.10jqka.com.cn" in url:
                if "concept.html" in url:
                    return concept_html
                return consensus_html
            raise AssertionError(url)

        def fake_get_json(url: str, headers=None) -> dict:
            if "datacenter-web.eastmoney.com" in url:
                for report_name, records in datacenter_payloads.items():
                    if f"reportName={report_name}" in url:
                        return {"result": {"data": records}}
                raise AssertionError(url)
            if "nodeapi/telegraphList" in url:
                return telegraph_payload
            if "getFastNewsList" in url:
                return global_news_payload
            if "qt/clist/get" in url:
                if "fs=m%3A90%2Bt%3A2" in url:
                    return sector_payload
                if "fs=m%3A0%2Bt%3A6" in url:
                    return breadth_payload
                return sector_payload
            if "getharden" in url:
                return hot_stocks_payload
            if "hsgtApi/method/dayChart" in url:
                return northbound_payload
            if "qt/stock/get" in url:
                return stock_info_payload
            if "reportapi.eastmoney.com" in url:
                return report_payload
            if "CompanyFinanceService.getFinanceReport2022" in url:
                return finance_payload
            if "fflow/kline/get" in url:
                return minute_payload
            if "daykline/get" in url:
                return fund_120d_payload
            raise AssertionError(url)

        with (
            patch.object(provider, "_http_get_text", side_effect=fake_get_text),
            patch.object(provider, "_http_get_json", side_effect=fake_get_json),
            patch.object(provider, "_http_post_form_json", return_value=announcement_payload),
            patch.object(provider, "_get_mootdx_client", return_value=FakeMootdxClient()),
        ):
            news = provider.get_stock_news("300750", 1)
            telegraph = provider.get_market_telegraph(1)
            global_news = provider.get_global_news(1)
            announcements = provider.get_announcements("300750", 1)
            minute_flow = provider.get_fund_flow_minute("300750")
            daily_flow = provider.get_fund_flow_120d("300750", 2)
            sectors = provider.get_sector_rankings(1)
            hot_stocks = provider.get_hot_stocks("2026-05-29", 1)
            concept_blocks = provider.get_concept_blocks("300750")
            reports = provider.get_research_reports("300750", 1)
            dragon_tiger = provider.get_dragon_tiger_board("300750", "2026-05-29", 30)
            daily_dragon_tiger = provider.get_daily_dragon_tiger("2026-05-29", 1000)
            margin = provider.get_margin_trading("300750", 1)
            block_trades = provider.get_block_trades("300750", 1)
            holders = provider.get_holder_numbers("300750", 1)
            dividends = provider.get_dividend_history("300750", 1)
            lockup = provider.get_lockup_expiry("300750", "2026-05-28", 90)
            northbound = provider.get_northbound_flow(5)
            stock_info = provider.get_stock_info("300750")
            quotes = provider.get_realtime_quotes(["300750", "000300", "510300"])
            bars = provider.get_price_bars("300750", 4, 2)
            order_book = provider.get_order_book("300750")
            transactions = provider.get_transactions("300750", 0, 3)
            financial_snapshot = provider.get_financial_snapshot("300750")
            f10_profile = provider.get_f10_profile("300750", "最新提示")
            finance = provider.get_financial_report("300750", "lrb", 1)
            consensus = provider.get_consensus_eps("300750")
            with patch.object(provider, "_http_post_json", side_effect=[iwencai_search_payload, iwencai_query_payload]):
                iwencai_search = provider.iwencai_search("机器人", "report", 5)
                iwencai_query = provider.iwencai_query("宁德时代 ROE", 1, 5)
            market_snapshot = provider.get_market_snapshot("2026-05-29")
            with patch.object(provider, "_http_get_json", side_effect=lambda url, headers=None: hot_stocks_sparse_payload if "getharden" in url else fake_get_json(url, headers)):
                hot_stocks_fallback = provider.get_hot_stocks("2026-05-29", 1)

        self.assertEqual(news[0]["title"], "宁德时代 获机构看好")
        self.assertEqual(telegraph[0]["source"], "财联社")
        self.assertEqual(global_news[0]["source"], "东方财富")
        self.assertEqual(announcements[0]["type"], "临时公告")
        self.assertEqual(minute_flow[-1]["main_net"], 1200000.0)
        self.assertEqual(daily_flow[-1]["main_net"], 11000000.0)
        self.assertEqual(sectors["top"][0]["name"], "储能")
        self.assertEqual(hot_stocks[0]["reason"], "储能+固态电池")
        self.assertEqual(hot_stocks_fallback[0]["change_pct"], 2.06)
        self.assertEqual(hot_stocks_fallback[0]["turnover_pct"], 24.3)
        self.assertEqual(concept_blocks["concept_tags"], ["储能"])
        self.assertEqual(concept_blocks["industry"][0]["name"], "电池")
        self.assertEqual(market_snapshot.advancers, 2)
        self.assertEqual(market_snapshot.decliners, 1)
        self.assertEqual(market_snapshot.unchanged, 1)
        self.assertEqual(market_snapshot.hot_sectors[0], "储能")
        self.assertTrue(reports[0]["pdfUrl"].endswith("ABC123_1.pdf"))
        self.assertEqual(dragon_tiger["institution"]["net_amt"], 1400.0)
        self.assertEqual(daily_dragon_tiger["stocks"][0]["code"], "300750")
        self.assertEqual(margin[0]["rzrqye"], 1_050_000_000)
        self.assertEqual(block_trades[0]["premium_pct"], -2.38)
        self.assertEqual(holders[0]["holder_num"], 520000)
        self.assertEqual(dividends[0]["plan"], "实施完成")
        self.assertEqual(lockup["history"][0]["type"], "股权激励限售股份")
        self.assertEqual(northbound["latest"]["hgt_yi"], 18.4)
        self.assertEqual(stock_info["industry"], "电池")
        self.assertEqual(quotes[0]["code"], "300750")
        self.assertEqual(quotes[1]["kind"], "index")
        self.assertEqual(quotes[2]["kind"], "etf")
        self.assertEqual(bars[0]["datetime"], "2026-05-25 15:00")
        self.assertEqual(order_book["bids"][0]["price"], 424.78)
        self.assertEqual(transactions[0]["price"], 427.4)
        self.assertEqual(financial_snapshot["eps"], 5.58)
        self.assertIn("最新提示", f10_profile)
        self.assertEqual(finance[0]["报告日"], "2026-03-31")
        self.assertEqual(consensus[0]["mean"], 20.77)
        self.assertEqual(len(iwencai_search), 1)
        self.assertEqual(iwencai_query[0]["股票代码"], "300750")

    def test_valuation_and_research_workflows(self) -> None:
        skill = ASharesSkill(config=make_offline_config())
        valuation = skill.valuation("300750")
        compare = skill.compare_valuations(["300750", "002594"])
        theme_research = skill.thematic_research(["机器人", "储能"], "report", 2, 1)
        research = skill.quick_research("300750", "2026-05-28")
        self.assertEqual(valuation["stock_code"], "300750")
        self.assertEqual(valuation["input"]["stock_code"], "300750")
        self.assertIsNotNone(valuation["pe_fwd"])
        self.assertTrue(valuation["coverage"]["quote_available"])
        self.assertEqual(len(compare["items"]), 2)
        self.assertGreaterEqual(theme_research["article_count"], 1)
        self.assertGreaterEqual(theme_research["stock_count"], 1)
        self.assertEqual(theme_research["input"]["queries"], ["机器人", "储能"])
        self.assertEqual(theme_research["coverage"]["query_count"], 2)
        self.assertEqual(research["stock_code"], "300750")
        self.assertIn("coverage", research)
        self.assertEqual(research["input"]["date"], "2026-05-28")
        self.assertEqual(research["strategy_system"]["trade_setup"]["stock_code"], "300750")
        self.assertIn("discipline", research["strategy_system"])
        self.assertIn("playbook", research["strategy_system"])


if __name__ == "__main__":
    unittest.main()
