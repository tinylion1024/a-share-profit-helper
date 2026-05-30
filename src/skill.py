"""Unified high-availability skill facade."""

from __future__ import annotations

import importlib.util
import math
from typing import Optional

from src.config import Config
from src.core import AnalysisPipeline, IntegratedAnalyzer, RiskChecker
from src.core.time_context import build_intent_time_context
from src.modules import HighPRStockPicker, PostMarketAnalyzer, PreMarketAnalyzer, TradingPlanGenerator
from src.providers import MarketDataProvider, build_provider
from src.user_context import UserContextStore
from src.utils.time import shanghai_timestamp_iso


class ASharesSkill:
    """Single entry point for agent-compatible skill execution."""

    DEFAULT_SAMPLE_CODES = ("300750", "002594", "600519", "000001")

    def __init__(self, config: Optional[Config] = None, provider: Optional[MarketDataProvider] = None):
        self.config = config or Config.load()
        self.provider = provider or build_provider(self.config)
        self.pipeline = AnalysisPipeline(self.config, self.provider)
        self.analyzer = IntegratedAnalyzer(self.config, self.provider)
        self.risk_checker = RiskChecker(self.config, self.provider)
        self.stock_picker = HighPRStockPicker(self.config, self.provider)
        self.pre_market = PreMarketAnalyzer(self.config, self.provider)
        self.post_market = PostMarketAnalyzer(self.config, self.provider)
        self.trading_plan = TradingPlanGenerator(self.config, self.provider)
        self.user_context = UserContextStore(self.config)

    def _timestamp(self) -> str:
        return shanghai_timestamp_iso()

    def _workflow_meta(
        self,
        workflow: str,
        input_payload: dict,
        *,
        available: bool = True,
        degraded_reasons: list[str] | None = None,
        errors: list[str] | None = None,
    ) -> dict:
        error_items = [item for item in (errors or []) if item]
        degraded_items = [item for item in (degraded_reasons or []) if item]
        return {
            "workflow": workflow,
            "generated_at": self._timestamp(),
            "provider": self.provider.source_name,
            "input": input_payload,
            "available": available,
            "degraded": bool(degraded_items),
            "degraded_reasons": degraded_items,
            "errors": error_items,
        }

    def _build_check(self, name: str, ok: bool, detail: str, *, status: str | None = None) -> dict:
        return {
            "name": name,
            "ok": ok,
            "status": status or ("ok" if ok else "error"),
            "detail": detail,
        }

    def _safe_list_payload(self, loader, base: dict, item_key: str = "items") -> dict:
        try:
            items = loader()
        except Exception as exc:
            payload = dict(base)
            payload.update({"available": False, "error": str(exc), item_key: []})
            return payload
        payload = dict(base)
        payload.update({"available": True, item_key: items})
        return payload

    def _safe_dict_payload(self, loader, base: dict) -> dict:
        try:
            data = loader()
        except Exception as exc:
            payload = dict(base)
            payload.update({"available": False, "error": str(exc)})
            return payload
        if isinstance(data, dict):
            payload = dict(base)
            payload.update(data)
            payload["available"] = True
            return payload
        payload = dict(base)
        payload.update({"available": True, "data": data})
        return payload

    def _resolve_stock_input(self, stock_identifier: str) -> dict[str, str]:
        return self.provider.resolve_stock_identifier(stock_identifier)

    def _resolved_stock_meta(self, resolved: dict[str, str]) -> dict:
        payload = {
            "stock_code": resolved["code"],
            "resolved_by": resolved.get("matched_by", ""),
        }
        if resolved.get("name"):
            payload["stock_name"] = resolved["name"]
        if resolved.get("query") and resolved["query"] != resolved["code"]:
            payload["stock_query"] = resolved["query"]
        return payload

    def _resolve_stock_inputs(self, stock_identifiers: list[str]) -> list[dict[str, str]]:
        return [self._resolve_stock_input(item) for item in stock_identifiers]

    def _community_summary(self, payload: dict) -> dict:
        return {
            "available": payload.get("available", False),
            "forum": payload.get("forum", "taoguba"),
            "sentiment_score": payload.get("sentiment_score"),
            "mood": payload.get("mood", "未知"),
            "consensus_level": payload.get("consensus_level", ""),
            "hot_topics": payload.get("hot_topics", []),
            "vip_focus": payload.get("vip_focus", []),
            "vip_views": payload.get("vip_views", []),
            "comment_count": payload.get("comment_count", 0),
            "error": payload.get("error", ""),
        }

    def _build_time_context(
        self,
        intent: str,
        requested_date: str | None = None,
        *,
        horizon: str | None = None,
    ) -> dict:
        return build_intent_time_context(intent, requested_date, horizon=horizon).to_dict()

    def _user_context_payload(self, stock_code: str | None = None) -> dict:
        return self.user_context.build_context(stock_code)

    def _remember(
        self,
        workflow: str,
        *,
        stock_code: str | None = None,
        stock_name: str | None = None,
        summary: str | None = None,
    ) -> None:
        self.user_context.remember_workflow(
            workflow,
            stock_code=stock_code,
            stock_name=stock_name,
            summary=summary,
        )

    def _observe_stock_memory(
        self,
        stock_code: str,
        *,
        stock_name: str,
        sector: str,
        style: str,
        setup: str,
        market_stage: str,
        community_mood: str,
        methodology_score: float | None,
        watchlist_match: bool,
        tags: list[str] | None = None,
        concept_tags: list[str] | None = None,
        catalysts: list[str] | None = None,
        notes: list[str] | None = None,
        themes: list[str] | None = None,
        summary: str | None = None,
    ) -> None:
        self.user_context.observe_stock_profile(
            stock_code,
            {
                "stock_name": stock_name,
                "sector": sector,
                "style": style,
                "setup": setup,
                "market_stage": market_stage,
                "community_mood": community_mood,
                "methodology_score": methodology_score,
                "watchlist_match": watchlist_match,
                "tags": tags or [],
                "concept_tags": concept_tags or [],
                "catalysts": catalysts or [],
                "notes": notes or [],
                "themes": themes or [],
                "summary": summary or "",
            },
        )

    def _observe_themes(
        self,
        themes: list[str],
        *,
        source: str,
        market_stage: str = "",
        community_mood: str = "",
        related_stocks: list[str] | None = None,
        reasons: list[str] | None = None,
        linked_tags: list[str] | None = None,
        heat_score: float | None = None,
        summary: str | None = None,
    ) -> None:
        for theme in themes:
            self.user_context.observe_theme_profile(
                theme,
                {
                    "source": source,
                    "market_stage": market_stage,
                    "community_mood": community_mood,
                    "related_stocks": related_stocks or [],
                    "reasons": reasons or [],
                    "linked_tags": linked_tags or [],
                    "heat_score": heat_score,
                    "summary": summary or "",
                },
            )

    def user_profile(self) -> dict:
        preferences = self.user_context.load_preferences().to_dict()
        memory = self.user_context.load_memory().to_dict()
        payload = self._workflow_meta("profile-show", {})
        payload.update({"preferences": preferences, "memory": memory})
        return payload

    def update_user_profile(
        self,
        *,
        risk_preference: str | None = None,
        default_horizon: str | None = None,
        preferred_sectors: list[str] | None = None,
        avoided_sectors: list[str] | None = None,
        watchlist: list[str] | None = None,
        focus_styles: list[str] | None = None,
        notes: list[str] | None = None,
    ) -> dict:
        preferences = self.user_context.update_preferences(
            risk_preference=risk_preference,
            default_horizon=default_horizon,
            preferred_sectors=preferred_sectors,
            avoided_sectors=avoided_sectors,
            watchlist=watchlist,
            focus_styles=focus_styles,
            notes=notes,
        ).to_dict()
        payload = self._workflow_meta("profile-set", {})
        payload.update({"preferences": preferences})
        return payload

    def user_memory(self, stock_code: str | None = None) -> dict:
        payload = self._workflow_meta("memory-show", {"stock_code": stock_code} if stock_code else {})
        payload.update(self._user_context_payload(stock_code))
        return payload

    def add_memory_note(self, stock_code: str, note: str) -> dict:
        resolved = self._resolve_stock_input(stock_code)
        stock_code = resolved["code"]
        memory = self.user_context.add_stock_note(stock_code, note).to_dict()
        payload = self._workflow_meta("memory-note", {"stock_code": stock_code, "note": note})
        payload.update(self._resolved_stock_meta(resolved))
        payload["memory"] = memory
        return payload

    def clear_memory(self, stock_code: str | None = None) -> dict:
        resolved_meta: dict[str, Any] = {}
        if stock_code:
            resolved = self._resolve_stock_input(stock_code)
            stock_code = resolved["code"]
            resolved_meta = self._resolved_stock_meta(resolved)
        memory = self.user_context.clear_memory(stock_code).to_dict()
        payload = self._workflow_meta("memory-clear", {"stock_code": stock_code} if stock_code else {})
        payload.update(resolved_meta)
        payload["memory"] = memory
        return payload

    def diagnose(
        self,
        stock_code: str,
        scenario: str = "诊股",
        horizon: str | None = None,
        risk_preference: str | None = None,
        date: str | None = None,
    ) -> dict:
        preferences = self.user_context.load_preferences()
        horizon = horizon or preferences.default_horizon
        risk_preference = risk_preference or preferences.risk_preference
        time_context = self._build_time_context("diagnose", date, horizon=horizon)
        effective_date = time_context["analysis_date"]
        resolved = self._resolve_stock_input(stock_code)
        stock_code = resolved["code"]
        payload = self.pipeline.run_standard_flow(
            stock_code=stock_code,
            scenario=scenario,
            horizon=horizon,
            risk_preference=risk_preference,
            date=effective_date,
        )
        evidence_plan = time_context["evidence_plan"]
        news = self.stock_news(stock_code, evidence_plan["news"]["page_size"])
        announcements = self.announcements(stock_code, evidence_plan["announcements"]["page_size"])
        payload["strategy_system"] = {
            "market_cycle": self.analyzer.assess_market_cycle(effective_date),
            "trade_setup": self.analyzer.evaluate_trade_setup(stock_code, effective_date),
            "discipline": self.analyzer.build_trade_discipline(stock_code, effective_date),
            "community": self.analyzer.analyze_stock_community(stock_code, evidence_plan["community"]["page_size"]),
        }
        payload["time_context"] = time_context
        payload["evidence_plan"] = evidence_plan
        payload["user_context"] = self._user_context_payload(stock_code)
        payload["recent_catalysts"] = {
            "news": news.get("items", []),
            "announcements": announcements.get("items", []),
        }
        payload["preference_alignment"] = {
            "risk_preference": risk_preference,
            "default_horizon": horizon,
            "watchlist_match": stock_code in preferences.watchlist,
            "preferred_sector_match": resolved.get("name", "") in preferences.preferred_sectors,
        }
        payload.update(self._resolved_stock_meta(resolved))
        payload["preference_alignment"]["preferred_sector_match"] = (
            self.provider.get_stock_snapshot(stock_code).sector in preferences.preferred_sectors
        )
        stock_snapshot = self.provider.get_stock_snapshot(stock_code)
        trade_setup = payload["strategy_system"]["trade_setup"]
        community = payload["strategy_system"]["community"]
        self._observe_stock_memory(
            stock_code,
            stock_name=resolved.get("name", "") or stock_snapshot.name,
            sector=stock_snapshot.sector,
            style=trade_setup.get("style", ""),
            setup=trade_setup.get("setup", ""),
            market_stage=trade_setup.get("market_stage", ""),
            community_mood=community.get("mood", ""),
            methodology_score=trade_setup.get("methodology_score"),
            watchlist_match=payload["preference_alignment"]["watchlist_match"],
            tags=trade_setup.get("tags", []),
            catalysts=[stock_snapshot.catalyst] if stock_snapshot.catalyst else [],
            notes=self.user_context.load_memory().stock_notes.get(stock_code, []),
            themes=[stock_snapshot.sector],
            summary=payload["conclusion"].get("summary", ""),
        )
        self._observe_themes(
            [stock_snapshot.sector],
            source="diagnose",
            market_stage=trade_setup.get("market_stage", ""),
            community_mood=community.get("mood", ""),
            related_stocks=[stock_code],
            reasons=trade_setup.get("reasons", []),
            linked_tags=trade_setup.get("tags", []),
            summary=payload["conclusion"].get("summary", ""),
        )
        self._remember(
            "diagnose",
            stock_code=stock_code,
            stock_name=resolved.get("name", ""),
            summary=payload["conclusion"].get("summary", ""),
        )
        return payload

    def risk(self, stock_code: str, date: str | None = None) -> dict:
        time_context = self._build_time_context("risk", date)
        effective_date = time_context["analysis_date"]
        resolved = self._resolve_stock_input(stock_code)
        stock_code = resolved["code"]
        payload = self.risk_checker.check(stock_code, effective_date).to_dict()
        payload["strategy_discipline"] = self.analyzer.build_trade_discipline(stock_code, effective_date)
        payload["time_context"] = time_context
        payload["evidence_plan"] = time_context["evidence_plan"]
        payload["user_context"] = self._user_context_payload(stock_code)
        payload.update(self._resolved_stock_meta(resolved))
        self._remember("risk", stock_code=stock_code, stock_name=resolved.get("name", ""), summary=payload["risk_level"])
        return payload

    def pick(self, filter_names: list[str]) -> list[dict]:
        preferences = self.user_context.load_preferences()
        items = [item.to_dict() for item in self.stock_picker.screen({"names": filter_names})]
        for item in items:
            stock = self.provider.get_stock_snapshot(item["code"])
            preferred_sector_match = stock.sector in preferences.preferred_sectors
            avoided_sector_match = stock.sector in preferences.avoided_sectors
            watchlist_match = item["code"] in preferences.watchlist
            style_match = item["style"] in preferences.focus_styles if preferences.focus_styles else False
            item["user_preference"] = {
                "watchlist_match": watchlist_match,
                "preferred_sector_match": preferred_sector_match,
                "avoided_sector_match": avoided_sector_match,
                "focus_style_match": style_match,
            }
            item["_preference_score"] = (
                (2 if watchlist_match else 0)
                + (1 if preferred_sector_match else 0)
                + (1 if style_match else 0)
                - (3 if avoided_sector_match else 0)
            )
        items.sort(key=lambda item: (item["_preference_score"], item["methodology_score"], item["risk_reward_ratio"]), reverse=True)
        for item in items:
            item.pop("_preference_score", None)
        self._remember("pick", summary=",".join(item["code"] for item in items[:3]))
        return items

    def pre_market_report(self, date: str | None = None) -> dict:
        time_context = self._build_time_context("pre-market", date)
        effective_date = time_context["analysis_date"]
        payload = self.pre_market.generate_report(effective_date).to_dict()
        payload["time_context"] = time_context
        payload["evidence_plan"] = time_context["evidence_plan"]
        payload["community"] = self.taoguba_market_sentiment(time_context["evidence_plan"]["community"]["page_size"])
        return payload

    def post_market_review(self, date: str | None = None) -> dict:
        time_context = self._build_time_context("post-market", date)
        effective_date = time_context["analysis_date"]
        payload = self.post_market.generate_review(effective_date).to_dict()
        payload["time_context"] = time_context
        payload["evidence_plan"] = time_context["evidence_plan"]
        payload["community"] = self.taoguba_market_sentiment(time_context["evidence_plan"]["community"]["page_size"])
        return payload

    def trading_plan_report(self, stock_code: str, date: str) -> dict:
        resolved = self._resolve_stock_input(stock_code)
        payload = self.trading_plan.generate_plan(resolved["code"], date).to_dict()
        payload.update(self._resolved_stock_meta(resolved))
        return payload

    def market_cycle_report(self, date: str | None = None) -> dict:
        time_context = self._build_time_context("market-cycle", date)
        evidence_plan = time_context["evidence_plan"]
        observe_date = time_context["analysis_date"]
        market = self.provider.get_market_snapshot(observe_date)
        playbook = self.analyzer.build_market_playbook(observe_date)
        community = self.analyzer.analyze_community_sentiment(evidence_plan["community"]["page_size"])
        telegraph = self.market_telegraph(evidence_plan["telegraph"]["page_size"])
        hot_stocks = self.hot_stocks(evidence_plan["hot_stocks"]["trade_date"], evidence_plan["hot_stocks"]["page_size"])
        northbound = self.northbound_flow(evidence_plan["northbound"]["history_days"])
        payload = self._workflow_meta("market-cycle", {"date": observe_date})
        payload.update(
            {
                "date": observe_date,
                "time_context": time_context,
                "evidence_plan": evidence_plan,
                "user_context": self._user_context_payload(),
                "market_snapshot": {
                    "total_volume_billion": market.total_volume_billion,
                    "sentiment_score": market.sentiment_score,
                    "trend_score": market.trend_score,
                    "advancers": market.advancers,
                    "decliners": market.decliners,
                    "hot_sectors": list(market.hot_sectors),
                    "leaders": list(market.leaders),
                },
                "community": self._community_summary(community),
                "evidence_basis": {
                    "telegraph": telegraph.get("items", []),
                    "hot_stocks": hot_stocks.get("items", []),
                    "northbound": northbound.get("history", []),
                },
                "playbook": playbook,
                "summary": {
                    "stage": playbook["stage"],
                    "environment": playbook["environment"],
                    "position_upper_bound": playbook["position_upper_bound"],
                    "community_mood": community.get("mood", "未知"),
                },
            }
        )
        self._observe_themes(
            list(market.hot_sectors) + [item.get("topic", "") for item in community.get("hot_topics", [])],
            source="market-cycle",
            market_stage=playbook["stage"],
            community_mood=community.get("mood", ""),
            related_stocks=[],
            reasons=playbook.get("signal_stack", []),
            linked_tags=list(market.hot_sectors),
            heat_score=community.get("heat_score"),
            summary=playbook.get("focus", ""),
        )
        self._remember("market-cycle", summary=playbook["stage"])
        return payload

    def strategy_playbook(self, stock_code: str, date: str | None = None) -> dict:
        time_context = self._build_time_context("playbook", date, horizon="短线")
        observe_date = time_context["analysis_date"]
        resolved = self._resolve_stock_input(stock_code)
        stock_code = resolved["code"]
        playbook = self.analyzer.build_stock_playbook(stock_code, observe_date)
        payload = self._workflow_meta(
            "playbook",
            {"stock_code": stock_code, "stock_query": resolved["query"], "date": observe_date},
        )
        payload.update(
            {
                "stock_code": stock_code,
                "date": observe_date,
                "time_context": time_context,
                "evidence_plan": time_context["evidence_plan"],
                "playbook": playbook,
                "community": self.analyzer.analyze_stock_community(
                    stock_code,
                    time_context["evidence_plan"]["community"]["page_size"],
                ),
                "user_context": self._user_context_payload(stock_code),
                "summary": {
                    "stock_name": playbook["stock_name"],
                    "stage": playbook["market_cycle"]["stage"],
                    "style": playbook["trade_setup"]["style"],
                    "setup": playbook["trade_setup"]["setup"],
                    "preferred_position": playbook["position_plan"]["preferred_position"],
                },
            }
        )
        payload.update(self._resolved_stock_meta(resolved))
        stock_snapshot = self.provider.get_stock_snapshot(stock_code)
        community = payload.get("community", {})
        self._observe_stock_memory(
            stock_code,
            stock_name=resolved.get("name", "") or stock_snapshot.name,
            sector=stock_snapshot.sector,
            style=playbook["trade_setup"].get("style", ""),
            setup=playbook["trade_setup"].get("setup", ""),
            market_stage=playbook["market_cycle"].get("stage", ""),
            community_mood=community.get("mood", ""),
            methodology_score=playbook["trade_setup"].get("methodology_score"),
            watchlist_match=payload["user_context"]["memory"].get("is_watchlist_stock", False),
            tags=playbook["trade_setup"].get("tags", []),
            catalysts=[stock_snapshot.catalyst] if stock_snapshot.catalyst else [],
            notes=self.user_context.load_memory().stock_notes.get(stock_code, []),
            themes=[stock_snapshot.sector],
            summary=playbook["trade_setup"].get("setup", ""),
        )
        self._remember("playbook", stock_code=stock_code, stock_name=resolved.get("name", ""), summary=playbook["trade_setup"]["setup"])
        return payload

    def taoguba_hot(self, page_size: int = 10, include_content: bool = False) -> dict:
        return self._safe_list_payload(
            lambda: self.provider.get_taoguba_hot_articles(page_size, include_content),
            {
                "forum": "taoguba",
                "provider": self.provider.source_name,
                "include_content": include_content,
            },
        )

    def taoguba_market_sentiment(self, page_size: int = 20) -> dict:
        return self._safe_dict_payload(
            lambda: self.provider.get_taoguba_market_sentiment(page_size),
            {
                "forum": "taoguba",
                "provider": self.provider.source_name,
                "hot_topics": [],
                "vip_focus": [],
                "articles": [],
            },
        )

    def taoguba_stock_sentiment(self, stock_code: str, page_size: int = 30) -> dict:
        resolved = self._resolve_stock_input(stock_code)
        stock_code = resolved["code"]
        payload = self._safe_dict_payload(
            lambda: self.provider.get_taoguba_stock_sentiment(stock_code, page_size),
            {
                "forum": "taoguba",
                "provider": self.provider.source_name,
                **self._resolved_stock_meta(resolved),
                "vip_views": [],
                "comments": [],
                "key_phrases": [],
            },
        )
        payload.update(self._resolved_stock_meta(resolved))
        return payload

    def taoguba_vip_views(self, stock_code: str | None = None, page_size: int = 10) -> dict:
        resolved_meta: dict[str, str] = {}
        if stock_code:
            resolved = self._resolve_stock_input(stock_code)
            stock_code = resolved["code"]
            resolved_meta = self._resolved_stock_meta(resolved)
        return self._safe_list_payload(
            lambda: self.provider.get_taoguba_vip_views(stock_code, page_size),
            {"forum": "taoguba", "provider": self.provider.source_name, **resolved_meta},
        )

    def stock_news(self, stock_code: str, page_size: int = 10) -> dict:
        resolved = self._resolve_stock_input(stock_code)
        stock_code = resolved["code"]
        return self._safe_list_payload(
            lambda: self.provider.get_stock_news(stock_code, page_size),
            {"provider": self.provider.source_name, **self._resolved_stock_meta(resolved)},
        )

    def market_telegraph(self, page_size: int = 20) -> dict:
        return self._safe_list_payload(
            lambda: self.provider.get_market_telegraph(page_size),
            {"provider": self.provider.source_name},
        )

    def global_news(self, page_size: int = 20) -> dict:
        return self._safe_list_payload(
            lambda: self.provider.get_global_news(page_size),
            {"provider": self.provider.source_name},
        )

    def announcements(self, stock_code: str, page_size: int = 10) -> dict:
        resolved = self._resolve_stock_input(stock_code)
        stock_code = resolved["code"]
        return self._safe_list_payload(
            lambda: self.provider.get_announcements(stock_code, page_size),
            {"provider": self.provider.source_name, **self._resolved_stock_meta(resolved)},
        )

    def fund_flow(self, stock_code: str, period: str = "minute", limit: int = 120) -> dict:
        resolved = self._resolve_stock_input(stock_code)
        stock_code = resolved["code"]
        try:
            if period == "minute":
                items = self.provider.get_fund_flow_minute(stock_code)
            else:
                items = self.provider.get_fund_flow_120d(stock_code, limit=limit)
        except Exception as exc:
            return {
                "stock_code": stock_code,
                "period": period,
                "provider": self.provider.source_name,
                "available": False,
                "error": str(exc),
                **self._resolved_stock_meta(resolved),
                "count": 0,
                "total_main_net": 0.0,
                "latest": None,
                "items": [],
            }
        total_main = round(sum(float(item.get("main_net", 0) or 0) for item in items), 2)
        return {
            "stock_code": stock_code,
            "period": period,
            "provider": self.provider.source_name,
            "available": True,
            **self._resolved_stock_meta(resolved),
            "count": len(items),
            "total_main_net": total_main,
            "latest": items[-1] if items else None,
            "items": items,
        }

    def sector_rankings(self, top_n: int = 10) -> dict:
        return self._safe_dict_payload(
            lambda: self.provider.get_sector_rankings(top_n),
            {"provider": self.provider.source_name, "top": [], "bottom": [], "total": 0},
        )

    def hot_stocks(self, trade_date: str | None = None, page_size: int = 20) -> dict:
        return self._safe_list_payload(
            lambda: self.provider.get_hot_stocks(trade_date, page_size),
            {"date": trade_date, "provider": self.provider.source_name},
        )

    def concept_blocks(self, stock_code: str) -> dict:
        resolved = self._resolve_stock_input(stock_code)
        stock_code = resolved["code"]
        return self._safe_dict_payload(
            lambda: self.provider.get_concept_blocks(stock_code),
            {
                "provider": self.provider.source_name,
                **self._resolved_stock_meta(resolved),
                "industry": [],
                "concept": [],
                "region": [],
                "concept_tags": [],
            },
        )

    def research_reports(self, stock_code: str, page_size: int = 10) -> dict:
        resolved = self._resolve_stock_input(stock_code)
        stock_code = resolved["code"]
        return self._safe_list_payload(
            lambda: self.provider.get_research_reports(stock_code, page_size),
            {"provider": self.provider.source_name, **self._resolved_stock_meta(resolved)},
        )

    def dragon_tiger(self, stock_code: str, trade_date: str, look_back: int = 30) -> dict:
        resolved = self._resolve_stock_input(stock_code)
        stock_code = resolved["code"]
        return self._safe_dict_payload(
            lambda: self.provider.get_dragon_tiger_board(stock_code, trade_date, look_back),
            {
                "date": trade_date,
                "look_back": look_back,
                "provider": self.provider.source_name,
                **self._resolved_stock_meta(resolved),
                "records": [],
                "buy_top5": [],
                "sell_top5": [],
                "institution": {},
            },
        )

    def daily_dragon_tiger(self, trade_date: str, min_net_buy: float | None = None) -> dict:
        return self._safe_dict_payload(
            lambda: self.provider.get_daily_dragon_tiger(trade_date, min_net_buy),
            {"date": trade_date, "provider": self.provider.source_name, "stocks": [], "total_records": 0},
        )

    def margin_trading(self, stock_code: str, page_size: int = 10) -> dict:
        resolved = self._resolve_stock_input(stock_code)
        stock_code = resolved["code"]
        return self._safe_list_payload(
            lambda: self.provider.get_margin_trading(stock_code, page_size),
            {"provider": self.provider.source_name, **self._resolved_stock_meta(resolved)},
        )

    def block_trades(self, stock_code: str, page_size: int = 10) -> dict:
        resolved = self._resolve_stock_input(stock_code)
        stock_code = resolved["code"]
        return self._safe_list_payload(
            lambda: self.provider.get_block_trades(stock_code, page_size),
            {"provider": self.provider.source_name, **self._resolved_stock_meta(resolved)},
        )

    def holder_numbers(self, stock_code: str, page_size: int = 10) -> dict:
        resolved = self._resolve_stock_input(stock_code)
        stock_code = resolved["code"]
        return self._safe_list_payload(
            lambda: self.provider.get_holder_numbers(stock_code, page_size),
            {"provider": self.provider.source_name, **self._resolved_stock_meta(resolved)},
        )

    def dividend_history(self, stock_code: str, page_size: int = 10) -> dict:
        resolved = self._resolve_stock_input(stock_code)
        stock_code = resolved["code"]
        return self._safe_list_payload(
            lambda: self.provider.get_dividend_history(stock_code, page_size),
            {"provider": self.provider.source_name, **self._resolved_stock_meta(resolved)},
        )

    def lockup_expiry(self, stock_code: str, trade_date: str, forward_days: int = 90) -> dict:
        resolved = self._resolve_stock_input(stock_code)
        stock_code = resolved["code"]
        return self._safe_dict_payload(
            lambda: self.provider.get_lockup_expiry(stock_code, trade_date, forward_days),
            {
                "date": trade_date,
                "provider": self.provider.source_name,
                **self._resolved_stock_meta(resolved),
                "history": [],
                "upcoming": [],
            },
        )

    def northbound_flow(self, history_days: int = 20) -> dict:
        return self._safe_dict_payload(
            lambda: self.provider.get_northbound_flow(history_days),
            {"provider": self.provider.source_name, "history": [], "latest": {}},
        )

    def stock_info(self, stock_code: str) -> dict:
        resolved = self._resolve_stock_input(stock_code)
        stock_code = resolved["code"]
        return self._safe_dict_payload(
            lambda: self.provider.get_stock_info(stock_code),
            {"code": stock_code, "provider": self.provider.source_name, **self._resolved_stock_meta(resolved)},
        )

    def realtime_quotes(self, codes: list[str], kind: str = "auto") -> dict:
        resolved_inputs: list[str] = []
        for item in codes:
            raw = str(item).strip()
            if raw and kind in {"auto", "stock"}:
                try:
                    resolved_inputs.append(self._resolve_stock_input(raw)["code"])
                    continue
                except Exception:
                    pass
            resolved_inputs.append(raw)
        try:
            items = self.provider.get_realtime_quotes(resolved_inputs, kind)
        except Exception as exc:
            return {
                "provider": self.provider.source_name,
                "kind": kind,
                "available": False,
                "error": str(exc),
                "inputs": codes,
                "items": [],
            }
        return {
            "provider": self.provider.source_name,
            "kind": kind,
            "available": True,
            "inputs": codes,
            "items": items,
        }

    def valuation(self, stock_code: str) -> dict:
        resolved = self._resolve_stock_input(stock_code)
        stock_code = resolved["code"]
        quotes_payload = self.realtime_quotes([stock_code], kind="stock")
        quote = quotes_payload.get("items", [{}])[0] if quotes_payload.get("items") else {}
        consensus = self.consensus_eps(stock_code)
        forecast_rows = consensus.get("items", [])
        errors: list[str] = []
        degraded_reasons: list[str] = []
        if quotes_payload.get("available") is False:
            errors.append(quotes_payload.get("error", "quote lookup failed"))
            degraded_reasons.append("quote_unavailable")
        if not forecast_rows:
            degraded_reasons.append("consensus_missing")
        eps_cur = float(forecast_rows[0]["mean"]) if forecast_rows else 0.0
        eps_next = float(forecast_rows[1]["mean"]) if len(forecast_rows) > 1 else 0.0
        analyst_count = int(forecast_rows[0]["institution_count"]) if forecast_rows else 0
        price = float(quote.get("price") or 0)
        pe_ttm = float(quote.get("pe_ttm") or 0)
        pb = float(quote.get("pb") or 0)
        pe_fwd = price / eps_cur if eps_cur > 0 else math.inf
        cagr = (eps_next / eps_cur - 1) if eps_cur > 0 and eps_next > 0 else 0.0
        peg = pe_fwd / (cagr * 100) if cagr > 0 and math.isfinite(pe_fwd) else math.inf
        digest_years = (
            math.log(pe_fwd / 30) / math.log(1 + cagr)
            if pe_fwd > 30 and cagr > 0 and math.isfinite(pe_fwd)
            else 0.0
        )
        payload = self._workflow_meta(
            "valuation",
            {"stock_code": stock_code, "stock_query": resolved["query"]},
            available=bool(quote),
            degraded_reasons=degraded_reasons,
            errors=errors,
        )
        payload.update(
            {
            "stock_code": stock_code,
            "name": quote.get("name", ""),
            "price": price,
            "mcap_yi": quote.get("mcap_yi", 0),
            "pe_ttm": pe_ttm,
            "pb": pb,
            "eps_cur": eps_cur or None,
            "eps_next": eps_next or None,
            "pe_fwd": round(pe_fwd, 2) if math.isfinite(pe_fwd) else None,
            "cagr_pct": round(cagr * 100, 2) if cagr else None,
            "peg": round(peg, 2) if math.isfinite(peg) else None,
            "digest_years": round(digest_years, 2) if math.isfinite(digest_years) else None,
            "analyst_count": analyst_count,
            "coverage": {
                "quote_available": bool(quote),
                "consensus_available": bool(forecast_rows),
                "analyst_count": analyst_count,
            },
            "summary": {
                "stock_name": quote.get("name", ""),
                "price": price,
                "pe_fwd": round(pe_fwd, 2) if math.isfinite(pe_fwd) else None,
                "peg": round(peg, 2) if math.isfinite(peg) else None,
            },
            }
        )
        payload.update(self._resolved_stock_meta(resolved))
        return payload

    def compare_valuations(self, stock_codes: list[str]) -> dict:
        items = [self.valuation(code) for code in stock_codes]
        items.sort(key=lambda item: item.get("peg") if item.get("peg") is not None else float("inf"))
        return {
            "provider": self.provider.source_name,
            "inputs": stock_codes,
            "items": items,
        }

    def _extract_article_stock_codes(self, article: dict) -> list[str]:
        codes: list[str] = []
        stock_infos = article.get("stock_infos") or article.get("stocks") or []
        if isinstance(stock_infos, dict):
            stock_infos = [stock_infos]
        for item in stock_infos:
            if not isinstance(item, dict):
                continue
            code = str(item.get("code") or item.get("stock_code") or "").strip()
            if len(code) == 6 and code.isdigit() and code not in codes:
                codes.append(code)
        for key in ("code", "stock_code", "股票代码"):
            code = str(article.get(key) or "").strip()
            if len(code) == 6 and code.isdigit() and code not in codes:
                codes.append(code)
        return codes

    def thematic_research(
        self,
        queries: list[str],
        channel: str = "report",
        size: int = 20,
        supplement_per_stock: int = 2,
    ) -> dict:
        best_articles: dict[str, dict] = {}
        query_hits: list[dict] = []
        for query in queries:
            result = self.iwencai_search(query, channel, size)
            if result.get("available") is False:
                payload = self._workflow_meta(
                    "theme-research",
                    {
                        "queries": queries,
                        "channel": channel,
                        "size": size,
                        "supplement_per_stock": supplement_per_stock,
                    },
                    available=False,
                    degraded_reasons=["iwencai_unavailable"],
                    errors=[result.get("error", "")],
                )
                payload.update(
                    {
                    "channel": channel,
                    "queries": queries,
                    "error": result.get("error", ""),
                    "article_count": 0,
                    "stock_count": 0,
                    "articles": [],
                    "supplements": [],
                    "query_hits": [],
                    }
                )
                return payload
            query_hits.append({"query": query, "count": len(result.get("items", []))})
            for article in result.get("items", []):
                uid = article.get("uid") or f"{article.get('title', '')}|{article.get('publish_date', '')}"
                score = float(article.get("score", 0) or 0)
                current = best_articles.get(uid)
                if current is None or score > float(current.get("score", 0) or 0):
                    best_articles[uid] = article

        articles = sorted(best_articles.values(), key=lambda item: item.get("publish_date", ""), reverse=True)
        seen_codes: list[str] = []
        for article in articles:
            for code in self._extract_article_stock_codes(article):
                if code not in seen_codes:
                    seen_codes.append(code)

        supplements: list[dict] = []
        for code in seen_codes[:10]:
            report_items = self.research_reports(code, supplement_per_stock).get("items", [])
            if report_items:
                supplements.append({"stock_code": code, "reports": report_items})
        payload = self._workflow_meta(
            "theme-research",
            {
                "queries": queries,
                "channel": channel,
                "size": size,
                "supplement_per_stock": supplement_per_stock,
            },
            available=True,
            degraded_reasons=[] if articles else ["empty_theme_search"],
        )
        payload.update(
            {
            "channel": channel,
            "queries": queries,
            "article_count": len(articles),
            "stock_count": len(seen_codes),
            "articles": articles,
            "supplements": supplements,
            "query_hits": query_hits,
            "coverage": {
                "query_count": len(queries),
                "deduped_article_count": len(articles),
                "supplemented_stock_count": len(supplements),
            },
            "summary": {
                "top_article_title": articles[0].get("title", "") if articles else "",
                "top_article_date": articles[0].get("publish_date", "") if articles else "",
                "stock_count": len(seen_codes),
            },
            }
        )
        theme_tokens = []
        for query in queries:
            theme_tokens.extend(token for token in query.replace("，", ",").split(",") if token.strip())
        self._observe_themes(
            theme_tokens,
            source="theme-research",
            related_stocks=seen_codes[:10],
            reasons=[item.get("title", "") for item in articles[:5]],
            linked_tags=theme_tokens,
            summary=payload["summary"].get("top_article_title", ""),
        )
        self._remember("theme-research", summary=",".join(theme_tokens[:5]))
        return payload

    def quick_research(self, stock_code: str, trade_date: str | None = None) -> dict:
        time_context = self._build_time_context("quick-research", trade_date, horizon="短线")
        evidence_plan = time_context["evidence_plan"]
        observe_date = time_context["analysis_date"]
        resolved = self._resolve_stock_input(stock_code)
        stock_code = resolved["code"]
        valuation = self.valuation(stock_code)
        strategy_setup = self.analyzer.evaluate_trade_setup(stock_code, observe_date)
        market_cycle = self.analyzer.assess_market_cycle(observe_date)
        discipline = self.analyzer.build_trade_discipline(stock_code, observe_date)
        playbook = self.analyzer.build_stock_playbook(stock_code, observe_date)
        concepts = self.concept_blocks(stock_code)
        fund_flow = self.fund_flow(stock_code, "120d", evidence_plan["fund_flow"]["limit"])
        dragon_tiger = self.dragon_tiger(stock_code, evidence_plan["dragon_tiger"]["trade_date"], evidence_plan["dragon_tiger"]["look_back"])
        lockup = self.lockup_expiry(stock_code, evidence_plan["lockup"]["trade_date"], evidence_plan["lockup"]["forward_days"])
        margin = self.margin_trading(stock_code, evidence_plan["margin"]["page_size"])
        holders = self.holder_numbers(stock_code, evidence_plan["holders"]["page_size"])
        reports = self.research_reports(stock_code, evidence_plan["reports"]["page_size"])
        news = self.stock_news(stock_code, evidence_plan["news"]["page_size"])
        announcements = self.announcements(stock_code, evidence_plan["announcements"]["page_size"])
        community = self.taoguba_stock_sentiment(stock_code, evidence_plan["community"]["page_size"])
        degraded_reasons: list[str] = []
        if valuation.get("available") is False:
            degraded_reasons.append("valuation_unavailable")
        if valuation.get("degraded"):
            degraded_reasons.extend(item for item in valuation.get("degraded_reasons", []) if item not in degraded_reasons)
        if not reports.get("items"):
            degraded_reasons.append("reports_missing")
        if community.get("available") is False:
            degraded_reasons.append("community_unavailable")
        payload = self._workflow_meta(
            "quick-research",
            {"stock_code": stock_code, "stock_query": resolved["query"], "date": observe_date},
            available=valuation.get("available", True),
            degraded_reasons=degraded_reasons,
            errors=list(valuation.get("errors", [])),
        )
        payload.update(
            {
            "stock_code": stock_code,
            "date": observe_date,
            "time_context": time_context,
            "evidence_plan": evidence_plan,
            "user_context": self._user_context_payload(stock_code),
            "coverage": {
                "analyst_count": valuation.get("analyst_count", 0),
                "has_consensus": valuation.get("eps_cur") is not None,
                "report_count": len(reports.get("items", [])),
                "news_count": len(news.get("items", [])),
                "announcement_count": len(announcements.get("items", [])),
                "concept_count": len(concepts.get("concept_tags", [])),
                "margin_rows": len(margin.get("items", [])),
                "holder_rows": len(holders.get("items", [])),
                "community_comments": community.get("comment_count", 0),
                "community_vip_views": len(community.get("vip_views", [])),
            },
            "summary": {
                "stock_name": valuation.get("name", ""),
                "pe_fwd": valuation.get("pe_fwd"),
                "peg": valuation.get("peg"),
                "report_count": len(reports.get("items", [])),
                "market_stage": market_cycle["stage"],
                "style": strategy_setup["style"],
                "community_mood": community.get("mood", "未知"),
            },
            "strategy_system": {
                "market_cycle": market_cycle,
                "trade_setup": strategy_setup,
                "discipline": discipline,
                "playbook": playbook,
                "community": community,
            },
            "valuation": valuation,
            "concepts": concepts,
            "fund_flow": {
                "total_main_net": fund_flow.get("total_main_net", 0),
                "latest": fund_flow.get("latest"),
            },
            "dragon_tiger": {
                "record_count": len(dragon_tiger.get("records", [])),
                "institution_net_amt": dragon_tiger.get("institution", {}).get("net_amt", 0),
            },
            "lockup": {
                "history_count": len(lockup.get("history", [])),
                "upcoming_count": len(lockup.get("upcoming", [])),
            },
            "margin": margin.get("items", []),
            "holders": holders.get("items", []),
            "reports": reports.get("items", []),
            "news": news.get("items", []),
            "announcements": announcements.get("items", []),
            "community": community,
            }
        )
        payload.update(self._resolved_stock_meta(resolved))
        stock_snapshot = self.provider.get_stock_snapshot(stock_code)
        self._observe_stock_memory(
            stock_code,
            stock_name=resolved.get("name", "") or stock_snapshot.name,
            sector=stock_snapshot.sector,
            style=strategy_setup.get("style", ""),
            setup=strategy_setup.get("setup", ""),
            market_stage=market_cycle.get("stage", ""),
            community_mood=community.get("mood", ""),
            methodology_score=strategy_setup.get("methodology_score"),
            watchlist_match=payload["user_context"]["memory"].get("is_watchlist_stock", False),
            tags=strategy_setup.get("tags", []),
            concept_tags=concepts.get("concept_tags", []),
            catalysts=[stock_snapshot.catalyst] if stock_snapshot.catalyst else [],
            notes=self.user_context.load_memory().stock_notes.get(stock_code, []),
            themes=[stock_snapshot.sector] + list(concepts.get("concept_tags", [])),
            summary=f"{strategy_setup.get('style', '')} / {community.get('mood', '未知')}",
        )
        self._observe_themes(
            [stock_snapshot.sector] + list(concepts.get("concept_tags", [])),
            source="quick-research",
            market_stage=market_cycle.get("stage", ""),
            community_mood=community.get("mood", ""),
            related_stocks=[stock_code],
            reasons=[strategy_setup.get("setup", ""), market_cycle.get("focus", "")],
            linked_tags=strategy_setup.get("tags", []),
            summary=f"{strategy_setup.get('style', '')} / {community.get('mood', '未知')}",
        )
        self._remember(
            "quick-research",
            stock_code=stock_code,
            stock_name=resolved.get("name", ""),
            summary=f"{strategy_setup['style']} / {community.get('mood', '未知')}",
        )
        return payload

    def price_bars(self, stock_code: str, frequency: int = 4, limit: int = 20) -> dict:
        resolved = self._resolve_stock_input(stock_code)
        stock_code = resolved["code"]
        try:
            items = self.provider.get_price_bars(stock_code, frequency, limit)
        except Exception as exc:
            return {
                "stock_code": stock_code,
                "frequency": frequency,
                "provider": self.provider.source_name,
                "available": False,
                "error": str(exc),
                **self._resolved_stock_meta(resolved),
                "items": [],
            }
        return {
            "stock_code": stock_code,
            "frequency": frequency,
            "provider": self.provider.source_name,
            "available": True,
            **self._resolved_stock_meta(resolved),
            "items": items,
        }

    def order_book(self, stock_code: str) -> dict:
        resolved = self._resolve_stock_input(stock_code)
        stock_code = resolved["code"]
        try:
            payload = self.provider.get_order_book(stock_code)
        except Exception as exc:
            return {
                "stock_code": stock_code,
                "provider": self.provider.source_name,
                "available": False,
                "error": str(exc),
                **self._resolved_stock_meta(resolved),
                "data": {},
            }
        payload["provider"] = self.provider.source_name
        payload["available"] = True
        payload.update(self._resolved_stock_meta(resolved))
        return payload

    def transactions(self, stock_code: str, start: int = 0, limit: int = 50) -> dict:
        resolved = self._resolve_stock_input(stock_code)
        stock_code = resolved["code"]
        try:
            items = self.provider.get_transactions(stock_code, start, limit)
        except Exception as exc:
            return {
                "stock_code": stock_code,
                "provider": self.provider.source_name,
                "available": False,
                "error": str(exc),
                **self._resolved_stock_meta(resolved),
                "items": [],
            }
        return {
            "stock_code": stock_code,
            "provider": self.provider.source_name,
            "available": True,
            **self._resolved_stock_meta(resolved),
            "items": items,
        }

    def financial_snapshot(self, stock_code: str) -> dict:
        resolved = self._resolve_stock_input(stock_code)
        stock_code = resolved["code"]
        try:
            payload = self.provider.get_financial_snapshot(stock_code)
        except Exception as exc:
            return {
                "stock_code": stock_code,
                "provider": self.provider.source_name,
                "available": False,
                "error": str(exc),
                **self._resolved_stock_meta(resolved),
                "data": {},
            }
        return {
            "stock_code": stock_code,
            "provider": self.provider.source_name,
            "available": True,
            **self._resolved_stock_meta(resolved),
            "data": payload,
        }

    def f10_profile(self, stock_code: str, category: str | None = None) -> dict:
        resolved = self._resolve_stock_input(stock_code)
        stock_code = resolved["code"]
        try:
            items = self.provider.get_f10_profile(stock_code, category)
        except Exception as exc:
            return {
                "stock_code": stock_code,
                "provider": self.provider.source_name,
                "available": False,
                "category": category,
                "error": str(exc),
                **self._resolved_stock_meta(resolved),
                "items": {},
            }
        return {
            "stock_code": stock_code,
            "provider": self.provider.source_name,
            "available": True,
            "category": category,
            **self._resolved_stock_meta(resolved),
            "items": items,
        }

    def financial_report(self, stock_code: str, report_type: str = "lrb", page_size: int = 20) -> dict:
        resolved = self._resolve_stock_input(stock_code)
        stock_code = resolved["code"]
        return {
            "stock_code": stock_code,
            "report_type": report_type,
            "provider": self.provider.source_name,
            **self._resolved_stock_meta(resolved),
            "items": self.provider.get_financial_report(stock_code, report_type, page_size),
        }

    def consensus_eps(self, stock_code: str) -> dict:
        resolved = self._resolve_stock_input(stock_code)
        stock_code = resolved["code"]
        try:
            items = self.provider.get_consensus_eps(stock_code)
        except Exception as exc:
            return {
                "stock_code": stock_code,
                "provider": self.provider.source_name,
                "available": False,
                "error": str(exc),
                **self._resolved_stock_meta(resolved),
                "items": [],
            }
        return {
            "stock_code": stock_code,
            "provider": self.provider.source_name,
            "available": True,
            **self._resolved_stock_meta(resolved),
            "items": items,
        }

    def iwencai_search(self, query: str, channel: str = "report", size: int = 50) -> dict:
        if not self.config.offline_mode and not self.config.iwencai_api_key:
            return {
                "query": query,
                "channel": channel,
                "provider": self.provider.source_name,
                "available": False,
                "error": "IWENCAI_API_KEY is required for live iwencai search.",
                "items": [],
            }
        try:
            items = self.provider.iwencai_search(query, channel, size)
        except Exception as exc:
            return {
                "query": query,
                "channel": channel,
                "provider": self.provider.source_name,
                "available": False,
                "error": str(exc),
                "items": [],
            }
        return {
            "query": query,
            "channel": channel,
            "provider": self.provider.source_name,
            "available": True,
            "items": items,
        }

    def iwencai_query(self, query: str, page: int = 1, limit: int = 50) -> dict:
        if not self.config.offline_mode and not self.config.iwencai_api_key:
            return {
                "query": query,
                "provider": self.provider.source_name,
                "available": False,
                "error": "IWENCAI_API_KEY is required for live iwencai query.",
                "items": [],
            }
        try:
            items = self.provider.iwencai_query(query, page, limit)
        except Exception as exc:
            return {
                "query": query,
                "provider": self.provider.source_name,
                "available": False,
                "error": str(exc),
                "items": [],
            }
        return {
            "query": query,
            "provider": self.provider.source_name,
            "available": True,
            "items": items,
        }

    def self_check(self) -> dict:
        config_valid = self.config.validate()
        checks: list[dict] = []
        recommendations: list[str] = []
        degraded_capabilities: list[str] = []
        candidate_codes: list[str] = []
        try:
            stocks = self.provider.list_stock_candidates()
            candidate_codes = [stock.code for stock in stocks[:4]]
            checks.append(self._build_check("provider-bootstrap", True, f"loaded {len(stocks)} stock candidates"))
            if not candidate_codes:
                candidate_codes = list(self.DEFAULT_SAMPLE_CODES)
        except Exception as exc:
            checks.append(self._build_check("provider-bootstrap", False, str(exc)))
            configured_codes = [code for code in self.config.live_watchlist if str(code).isdigit()]
            candidate_codes = configured_codes[:4] or list(self.DEFAULT_SAMPLE_CODES)

        sample_code = candidate_codes[0] if candidate_codes else "300750"
        quotes_payload = self.realtime_quotes([sample_code], kind="stock")
        checks.append(
            self._build_check(
                "quotes",
                quotes_payload.get("available", False),
                quotes_payload.get("error", f"returned {len(quotes_payload.get('items', []))} rows"),
            )
        )
        if quotes_payload.get("available") is False:
            degraded_capabilities.extend(["valuation", "quick-research"])

        consensus_payload = self.consensus_eps(sample_code)
        consensus_ok = bool(consensus_payload.get("items"))
        checks.append(
            self._build_check(
                "consensus-eps",
                consensus_ok,
                f"returned {len(consensus_payload.get('items', []))} rows" if consensus_ok else "no consensus rows returned",
                status="warning" if not consensus_ok else "ok",
            )
        )
        if not consensus_ok:
            degraded_capabilities.extend(["valuation", "quick-research"])

        mootdx_installed = importlib.util.find_spec("mootdx") is not None
        checks.append(
            self._build_check(
                "mootdx",
                mootdx_installed,
                "optional dependency installed" if mootdx_installed else "optional dependency missing",
                status="ok" if mootdx_installed else "warning",
            )
        )
        if not mootdx_installed:
            degraded_capabilities.extend(["quarterly-snapshot", "f10", "kline", "order-book", "transactions"])
            recommendations.append("Install optional dependency with `pip install .[mootdx]` to enable mootdx-backed endpoints.")

        if self.config.offline_mode or self.config.iwencai_api_key:
            iwencai_payload = self.iwencai_search("机器人", "report", 1)
            iwencai_ok = iwencai_payload.get("available", False)
            checks.append(
                self._build_check(
                    "iwencai-search",
                    iwencai_ok,
                    iwencai_payload.get("error", f"returned {len(iwencai_payload.get('items', []))} rows"),
                    status="ok" if iwencai_ok else "warning",
                )
            )
            if not iwencai_ok:
                degraded_capabilities.extend(["theme-research", "iwencai-search", "iwencai-query"])
        else:
            checks.append(
                self._build_check(
                    "iwencai-search",
                    True,
                    "skipped because IWENCAI_API_KEY is not configured",
                    status="skipped",
                )
            )
            degraded_capabilities.extend(["theme-research", "iwencai-search", "iwencai-query"])
            recommendations.append("Set `IWENCAI_API_KEY` to enable live theme research and iwencai search.")

        taoguba_payload = self.taoguba_market_sentiment(5)
        checks.append(
            self._build_check(
                "taoguba-community",
                taoguba_payload.get("available", False),
                taoguba_payload.get("error", f"returned {len(taoguba_payload.get('articles', []))} articles"),
                status="ok" if taoguba_payload.get("available", False) else "warning",
            )
        )
        if taoguba_payload.get("available") is False:
            degraded_capabilities.extend(["taoguba-hot", "taoguba-sentiment", "taoguba-stock", "taoguba-vip"])
        overall_ok = config_valid and all(check["ok"] for check in checks if check["status"] not in {"warning", "skipped"})
        payload = self._workflow_meta("self-check", {}, available=overall_ok, degraded_reasons=sorted(set(degraded_capabilities)))
        payload.update(
            {
            "config_valid": config_valid,
            "offline_mode": self.config.offline_mode,
            "live_source": self.config.live_source,
            "credential_status": {
                "iwencai_api_key_configured": bool(self.config.iwencai_api_key),
            },
            "dependency_status": {
                "mootdx_installed": mootdx_installed,
            },
            "health_checks": checks,
            "recommended_actions": recommendations,
            "supported_scenarios": [
                "profile-show",
                "profile-set",
                "memory-show",
                "memory-note",
                "memory-clear",
                "diagnose",
                "risk",
                "pick",
                "pre-market",
                "post-market",
                "market-cycle",
                "plan",
                "playbook",
                "news",
                "telegraph",
                "global-news",
                "announcements",
                "fund-flow",
                "sectors",
                "hot-stocks",
                "taoguba-hot",
                "taoguba-sentiment",
                "taoguba-stock",
                "taoguba-vip",
                "concept-blocks",
                "reports",
                "dragon-tiger",
                "daily-dragon-tiger",
                "margin",
                "block-trades",
                "holders",
                "dividends",
                "lockup",
                "northbound",
                "stock-info",
                "quotes",
                "valuation",
                "compare",
                "theme-research",
                "quick-research",
                "kline",
                "order-book",
                "transactions",
                "quarterly-snapshot",
                "f10",
                "finance",
                "consensus-eps",
                "iwencai-search",
                "iwencai-query",
            ],
            "sample_stock_codes": candidate_codes,
            }
        )
        return payload
