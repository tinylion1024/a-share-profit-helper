---
name: a-shares-master
description: "Analyze A-share trades with latest trusted online data."
version: 2.1.0
author: tinylion1024
license: MIT
platforms: [linux, macos]
homepage: https://github.com/tinylion1024/a-share-profit-helper
user-invocable: true
tags: [finance, stocks, a-share, trading]
category: research
metadata: {"openclaw":{"emoji":"📈","homepage":"https://github.com/tinylion1024/a-share-profit-helper","skillKey":"a-shares-master","os":["linux","macos"],"requires":{"bins":["python3"]},"envVars":[{"name":"A_SHARE_SKILL_OFFLINE_MODE","required":false,"description":"Force fixture mode only for tests or incident fallback."},{"name":"A_SHARE_SKILL_DATA_PATH","required":false,"description":"Path to fixture JSON with market and stock data."},{"name":"A_SHARE_SKILL_LIVE_SOURCE","required":false,"description":"Current trusted upstream, default is tencent."},{"name":"A_SHARE_SKILL_WATCHLIST","required":false,"description":"Comma-separated online watchlist for live stock picking."},{"name":"A_SHARE_SKILL_TIMEOUT_SECONDS","required":false,"description":"HTTP timeout for live upstream requests."},{"name":"IWENCAI_BASE_URL","required":false,"description":"Override iwencai API base URL for semantic search."},{"name":"IWENCAI_API_KEY","required":false,"description":"Enable live iwencai semantic and structured queries."}]},"hermes":{"category":"research","tags":["finance","stocks","a-share","trading"],"related_skills":["browser","spreadsheets"],"config":{"offline_mode":"A_SHARE_SKILL_OFFLINE_MODE","sample_data_path":"A_SHARE_SKILL_DATA_PATH","live_source":"A_SHARE_SKILL_LIVE_SOURCE","watchlist":"A_SHARE_SKILL_WATCHLIST","iwencai_api_key":"IWENCAI_API_KEY"}}}
---

# A-Shares Master Skill

This skill uses the latest trusted online A-share data by default, then converts it into `诊股` / `选股` / `风控` / `盘前盘后复盘` / `市场周期判断` / `方法论执行手册` / `新闻` / `公告` / `资金流` / `行业轮动` / `热点强势股` / `概念板块` / `研报` / `龙虎榜` / `融资融券` / `大宗交易` / `股东户数` / `分红` / `解禁` / `北向资金` / `个股信息` / `批量实时行情` / `K线` / `五档盘口` / `逐笔成交` / `季报快照` / `F10 公司资料` / `财报三表` / `一致预期` / `估值` / `批量对比` / `主题研报批量检索` / `快速调研` / `iwencai 检索` output. Local fixtures remain available only for tests or controlled fallback.

The three flagship workflows, `valuation`, `quick-research`, and `theme-research`, now share a common machine-friendly envelope with `workflow`, `generated_at`, `input`, `degraded`, `errors`, `coverage`, and `summary`. `self-check` also reports dependency state, credential state, capability checks, and recommended actions.

## When To Use

- The user asks whether a stock can be bought, held, reduced, or avoided.
- The user wants a pre-market view, post-market review, or a two-scenario trading plan.
- The agent needs current A-share quotes, turnover, MA20, support, and resistance from live upstreams.
- The user wants stock news, CNInfo announcements, intraday fund flow, sector rotation, THS hot stocks, concept tags, Eastmoney research reports, dragon-tiger seats, margin data, block trades, holder changes, dividend history, northbound flow, stock basics, batch quotes, K-line bars, five-level order book, tick transactions, quarterly snapshots, F10 company text, financial statements, THS consensus EPS, valuation comparison, thematic report research, or iwencai semantic search.
- The agent must use `terminal` with a single, stable entrypoint that works in both OpenClaw and Hermes-style environments.

## Prerequisites

- Run inside `{baseDir}` or the repository root.
- Python 3.9+ is enough.
- Network access is required for default execution because the skill fetches online quotes and K-lines.
- `quarterly-snapshot` and `f10` use optional `mootdx`; install it with `pip install .[mootdx]`.
- To force fixture mode for tests or incident fallback, set `A_SHARE_SKILL_OFFLINE_MODE=true`.

## How To Run

Prefer the unified entrypoint:

```bash
cd {baseDir}
pip install .
a-shares-skill self-check
a-shares-skill valuation --code 300750

# Repository mode
python3 scripts/run_skill.py self-check
python3 scripts/run_skill.py risk --code 300750
python3 scripts/run_skill.py diagnose --code 300750 --date 2026-05-28
python3 scripts/run_skill.py pick --filters basic,tech,catalyst
python3 scripts/run_skill.py market-cycle --date 2026-05-28
python3 scripts/run_skill.py pre-market --date 2026-05-28
python3 scripts/run_skill.py post-market --date 2026-05-28
python3 scripts/run_skill.py plan --code 300750 --date 2026-05-28
python3 scripts/run_skill.py playbook --code 300750 --date 2026-05-28
python3 scripts/run_skill.py news --code 300750 --page-size 3
python3 scripts/run_skill.py telegraph --page-size 5
python3 scripts/run_skill.py global-news --page-size 5
python3 scripts/run_skill.py announcements --code 300750 --page-size 3
python3 scripts/run_skill.py fund-flow --code 300750 --period minute
python3 scripts/run_skill.py sectors --top 5
python3 scripts/run_skill.py hot-stocks --page-size 5
python3 scripts/run_skill.py concept-blocks --code 300750
python3 scripts/run_skill.py reports --code 300750 --page-size 3
python3 scripts/run_skill.py dragon-tiger --code 002428 --date 2026-05-28
python3 scripts/run_skill.py daily-dragon-tiger --date 2026-05-28 --min-net-buy 5000
python3 scripts/run_skill.py margin --code 300750 --page-size 3
python3 scripts/run_skill.py block-trades --code 300750 --page-size 3
python3 scripts/run_skill.py holders --code 300750 --page-size 3
python3 scripts/run_skill.py dividends --code 300750 --page-size 3
python3 scripts/run_skill.py lockup --code 002428 --date 2026-05-28 --forward-days 90
python3 scripts/run_skill.py northbound --history-days 5
python3 scripts/run_skill.py stock-info --code 300750
python3 scripts/run_skill.py quotes --codes 300750,sh000300,510300 --kind auto
python3 scripts/run_skill.py valuation --code 300750
python3 scripts/run_skill.py compare --codes 300750,002594
python3 scripts/run_skill.py theme-research --queries "人形机器人产业链深度 2026,人形机器人减速器 丝杠" --channel report --size 5 --supplement-per-stock 2
python3 scripts/run_skill.py quick-research --code 300750 --date 2026-05-29
python3 scripts/run_skill.py kline --code 300750 --frequency 4 --limit 5
python3 scripts/run_skill.py order-book --code 300750
python3 scripts/run_skill.py transactions --code 300750 --start 0 --limit 5
python3 scripts/run_skill.py quarterly-snapshot --code 300750
python3 scripts/run_skill.py f10 --code 300750 --category 最新提示
python3 scripts/run_skill.py finance --code 300750 --report-type lrb --page-size 1
python3 scripts/run_skill.py consensus-eps --code 300750
python3 scripts/run_skill.py iwencai-search --query "人形机器人 行星滚柱丝杠 2026" --channel report --size 3
```

For machine-readable output:

```bash
python3 scripts/run_skill.py --format json risk --code 300750
```

## Quick Reference

- `terminal`
  Run all commands in this skill through the terminal tool or a shell-capable agent step.
- `scripts/run_skill.py`
  Single agent-friendly entrypoint.
- `a-shares-skill`
  Installed console script for non-repo usage.
- `python3 -m src.main`
  Module entrypoint that mirrors the installed console script.
- `src/skill.py`
  Unified facade used by all scripts.
- `src/providers/offline.py`
  Fixture provider kept for tests and incident fallback only.
- `src/providers/live.py`
  Trusted live provider using Tencent finance plus Eastmoney, THS, mootdx, CNInfo, and CLS endpoints.
- `src/core/`
  Analysis, rating, risk, and workflow logic.
- `scripts/run_tests.sh`
  Runs `pytest` when available, otherwise falls back to `unittest`.

## Procedure

1. Run `python3 scripts/run_skill.py self-check` before using live scenarios.
2. If the user asks for 风控 only, call `risk`.
3. If the user asks for 买/卖/持建议, call `diagnose`.
4. If the user asks for what to buy, call `pick`.
5. If the user asks for市场情绪阶段、仓位节奏 or 主攻/防守判断, call `market-cycle`.
6. If the user needs single-stock entry/add/reduce/exit rules, call `playbook`.
7. If the user needs actionable prices and position sizing, call `plan`.
8. If the user asks for event flow, call `news`, `telegraph`, `global-news`, or `announcements`.
9. If the user asks for资金面 or 行业轮动, call `fund-flow` or `sectors`.
10. If the user asks for强势股归因 or 题材热点, call `hot-stocks`.
11. If the user asks for个股所属概念、概念标签 or 题材归属, call `concept-blocks`.
12. If the user asks for卖方观点 or 机构覆盖, call `reports`.
13. If the user asks for席位资金、连板观察 or 全市场龙虎榜, call `dragon-tiger` or `daily-dragon-tiger`.
14. If the user asks for两融、筹码集中、大宗成交、分红回报 or 解禁预警, call `margin`, `holders`, `block-trades`, `dividends`, or `lockup`.
15. If the user asks for指数、ETF or 批量实时行情, call `quotes`.
16. If the user asks for个股估值、PEG、PE消化 or 批量估值对比, call `valuation` or `compare`.
17. If the user asks for主题研报聚合、跨主题研报批量检索 or 主题补充研报, call `theme-research`.
18. If the user asks for新标的快速调研, call `quick-research`.
19. If the user asks for个股K线、五档盘口 or 逐笔成交, call `kline`, `order-book`, or `transactions`.
20. If the user asks for北向资金、个股基本面、季报快照、F10资料、财务报表 or 一致预期, call `northbound`, `stock-info`, `quarterly-snapshot`, `f10`, `finance`, or `consensus-eps`.
21. If the user asks for跨主题语义检索 or 结构化问财查询, call `iwencai-search` or `iwencai-query`.
22. Use `--format json` when another agent or tool will parse the output.
23. If live data is unavailable, fail clearly unless the caller explicitly enabled offline fallback.

## Pitfalls

- Do not assume fixture output is acceptable in production; latest online data is the default contract.
- Do not call the legacy scripts first; they are thin wrappers around `run_skill.py`.
- Do not hide upstream failures by silently switching to fixture data.
- Do not edit `references/` to change behavior. The executable behavior lives in `src/` and `scripts/`.

## Verification

- Run `python3 scripts/run_skill.py self-check`.
- Run `python3 -m src.main --format json self-check`.
- Run `sh scripts/run_tests.sh`.
- If `pytest` is installed, the same tests should also pass via `python3 -m pytest -q tests`.
