"""Installable CLI entrypoint for the A-share skill."""

from __future__ import annotations

import argparse

from src.cli import (
    normalize_filters,
    render_compare,
    render_concept_blocks,
    render_consensus_eps,
    render_daily_dragon_tiger,
    render_diagnosis,
    render_dragon_tiger,
    render_f10_profile,
    render_financial_snapshot,
    render_fund_flow,
    render_hot_stocks,
    render_iwencai,
    render_json,
    render_lockup,
    render_market_cycle,
    render_news,
    render_northbound,
    render_order_book,
    render_post_market,
    render_pre_market,
    render_price_bars,
    render_playbook,
    render_quick_research,
    render_quotes,
    render_reports,
    render_risk_report,
    render_rows,
    render_sector_rankings,
    render_stock_info,
    render_stock_picker,
    render_theme_research,
    render_trading_plan,
    render_transactions,
    render_valuation,
)
from src.skill import ASharesSkill
from src.utils.time import shanghai_today_str


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="A-share skill runner")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("self-check", help="检查 Skill 是否可运行")

    risk = subparsers.add_parser("risk", help="风险扫描")
    risk.add_argument("--code", required=True, help="股票代码")
    risk.add_argument("--date", help="日期 (YYYY-MM-DD)")

    diagnose = subparsers.add_parser("diagnose", help="诊股")
    diagnose.add_argument("--code", required=True, help="股票代码")
    diagnose.add_argument("--scenario", default="诊股", help="场景名称")
    diagnose.add_argument("--horizon", default="短线", help="持仓周期")
    diagnose.add_argument("--risk-preference", default="平衡型", help="风险偏好")
    diagnose.add_argument("--date", help="日期 (YYYY-MM-DD)")

    pick = subparsers.add_parser("pick", help="选股")
    pick.add_argument("--filters", nargs="+", default=["basic", "tech", "catalyst"], help="过滤器")

    pre_market = subparsers.add_parser("pre-market", help="盘前分析")
    pre_market.add_argument("--date", help="日期 (YYYY-MM-DD)")

    post_market = subparsers.add_parser("post-market", help="盘后复盘")
    post_market.add_argument("--date", help="日期 (YYYY-MM-DD)")

    market_cycle = subparsers.add_parser("market-cycle", help="方法论市场周期判断")
    market_cycle.add_argument("--date", help="日期 (YYYY-MM-DD)")

    plan = subparsers.add_parser("plan", help="交易计划")
    plan.add_argument("--code", required=True, help="股票代码")
    plan.add_argument("--date", help="日期 (YYYY-MM-DD)")

    playbook = subparsers.add_parser("playbook", help="方法论单票执行手册")
    playbook.add_argument("--code", required=True, help="股票代码")
    playbook.add_argument("--date", help="日期 (YYYY-MM-DD)")

    news = subparsers.add_parser("news", help="个股新闻")
    news.add_argument("--code", required=True, help="股票代码")
    news.add_argument("--page-size", type=int, default=10, help="返回条数")

    telegraph = subparsers.add_parser("telegraph", help="市场快讯")
    telegraph.add_argument("--page-size", type=int, default=20, help="返回条数")

    global_news = subparsers.add_parser("global-news", help="全球财经快讯")
    global_news.add_argument("--page-size", type=int, default=20, help="返回条数")

    announcements = subparsers.add_parser("announcements", help="巨潮公告")
    announcements.add_argument("--code", required=True, help="股票代码")
    announcements.add_argument("--page-size", type=int, default=10, help="返回条数")

    fund_flow = subparsers.add_parser("fund-flow", help="资金流")
    fund_flow.add_argument("--code", required=True, help="股票代码")
    fund_flow.add_argument("--period", choices=["minute", "120d"], default="minute", help="资金流周期")
    fund_flow.add_argument("--limit", type=int, default=120, help="120日资金流条数")

    sectors = subparsers.add_parser("sectors", help="行业板块排名")
    sectors.add_argument("--top", type=int, default=10, help="Top/Bottom 返回条数")

    hot_stocks = subparsers.add_parser("hot-stocks", help="同花顺热点强势股")
    hot_stocks.add_argument("--date", help="观察日 (YYYY-MM-DD)")
    hot_stocks.add_argument("--page-size", type=int, default=20, help="返回条数")

    concept_blocks = subparsers.add_parser("concept-blocks", help="概念板块归属")
    concept_blocks.add_argument("--code", required=True, help="股票代码")

    reports = subparsers.add_parser("reports", help="个股研报")
    reports.add_argument("--code", required=True, help="股票代码")
    reports.add_argument("--page-size", type=int, default=10, help="返回条数")

    dragon_tiger = subparsers.add_parser("dragon-tiger", help="个股龙虎榜")
    dragon_tiger.add_argument("--code", required=True, help="股票代码")
    dragon_tiger.add_argument("--date", help="交易日 (YYYY-MM-DD)")
    dragon_tiger.add_argument("--look-back", type=int, default=30, help="回看天数")

    daily_dragon_tiger = subparsers.add_parser("daily-dragon-tiger", help="全市场龙虎榜")
    daily_dragon_tiger.add_argument("--date", help="交易日 (YYYY-MM-DD)")
    daily_dragon_tiger.add_argument("--min-net-buy", type=float, help="净买额下限，单位万元")

    margin = subparsers.add_parser("margin", help="融资融券")
    margin.add_argument("--code", required=True, help="股票代码")
    margin.add_argument("--page-size", type=int, default=10, help="返回条数")

    block_trades = subparsers.add_parser("block-trades", help="大宗交易")
    block_trades.add_argument("--code", required=True, help="股票代码")
    block_trades.add_argument("--page-size", type=int, default=10, help="返回条数")

    holders = subparsers.add_parser("holders", help="股东户数")
    holders.add_argument("--code", required=True, help="股票代码")
    holders.add_argument("--page-size", type=int, default=10, help="返回条数")

    dividends = subparsers.add_parser("dividends", help="分红送转")
    dividends.add_argument("--code", required=True, help="股票代码")
    dividends.add_argument("--page-size", type=int, default=10, help="返回条数")

    lockup = subparsers.add_parser("lockup", help="限售解禁")
    lockup.add_argument("--code", required=True, help="股票代码")
    lockup.add_argument("--date", help="观察日 (YYYY-MM-DD)")
    lockup.add_argument("--forward-days", type=int, default=90, help="未来观察天数")

    northbound = subparsers.add_parser("northbound", help="北向资金")
    northbound.add_argument("--history-days", type=int, default=20, help="缓存历史天数")

    stock_info = subparsers.add_parser("stock-info", help="个股信息")
    stock_info.add_argument("--code", required=True, help="股票代码")

    quotes = subparsers.add_parser("quotes", help="腾讯财经批量实时行情")
    quotes.add_argument("--codes", nargs="+", required=True, help="股票/指数/ETF 代码，支持逗号分隔")
    quotes.add_argument("--kind", choices=["auto", "stock", "index", "etf"], default="auto", help="代码类型")

    valuation = subparsers.add_parser("valuation", help="单票完整估值")
    valuation.add_argument("--code", required=True, help="股票代码")

    compare = subparsers.add_parser("compare", help="批量估值对比")
    compare.add_argument("--codes", nargs="+", required=True, help="股票代码，支持逗号分隔")

    theme_research = subparsers.add_parser("theme-research", help="主题研报批量检索")
    theme_research.add_argument("--queries", nargs="+", required=True, help="检索语句，支持逗号分隔")
    theme_research.add_argument("--channel", choices=["report", "announcement", "news"], default="report", help="检索频道")
    theme_research.add_argument("--size", type=int, default=20, help="每个query的返回条数")
    theme_research.add_argument("--supplement-per-stock", type=int, default=2, help="每个标的补充的东财研报数")

    quick_research = subparsers.add_parser("quick-research", help="新标的快速调研")
    quick_research.add_argument("--code", required=True, help="股票代码")
    quick_research.add_argument("--date", help="观察日 (YYYY-MM-DD)")

    kline = subparsers.add_parser("kline", help="mootdx K线")
    kline.add_argument("--code", required=True, help="股票代码")
    kline.add_argument("--frequency", type=int, default=4, help="4日线 5周线 6月线 7/8/9/10/11分时")
    kline.add_argument("--limit", type=int, default=20, help="返回条数")

    order_book = subparsers.add_parser("order-book", help="mootdx 五档盘口")
    order_book.add_argument("--code", required=True, help="股票代码")

    transactions = subparsers.add_parser("transactions", help="mootdx 逐笔成交")
    transactions.add_argument("--code", required=True, help="股票代码")
    transactions.add_argument("--start", type=int, default=0, help="起始偏移")
    transactions.add_argument("--limit", type=int, default=50, help="返回条数")

    quarterly_snapshot = subparsers.add_parser("quarterly-snapshot", help="mootdx 季报快照")
    quarterly_snapshot.add_argument("--code", required=True, help="股票代码")

    f10 = subparsers.add_parser("f10", help="mootdx F10 文本资料")
    f10.add_argument("--code", required=True, help="股票代码")
    f10.add_argument("--category", help="F10 分类，如 最新提示 / 公司概况 / 财务分析")

    finance = subparsers.add_parser("finance", help="新浪财报三表")
    finance.add_argument("--code", required=True, help="股票代码")
    finance.add_argument("--report-type", choices=["lrb", "fzb", "llb"], default="lrb", help="报表类型")
    finance.add_argument("--page-size", type=int, default=20, help="返回期数")

    consensus_eps = subparsers.add_parser("consensus-eps", help="同花顺一致预期EPS")
    consensus_eps.add_argument("--code", required=True, help="股票代码")

    iwencai_search = subparsers.add_parser("iwencai-search", help="iwencai 语义检索")
    iwencai_search.add_argument("--query", required=True, help="查询语句")
    iwencai_search.add_argument("--channel", choices=["report", "announcement", "news"], default="report", help="检索频道")
    iwencai_search.add_argument("--size", type=int, default=10, help="返回条数")

    iwencai_query = subparsers.add_parser("iwencai-query", help="iwencai 结构化查询")
    iwencai_query.add_argument("--query", required=True, help="查询语句")
    iwencai_query.add_argument("--page", type=int, default=1, help="页码")
    iwencai_query.add_argument("--limit", type=int, default=10, help="返回条数")

    parser.add_argument("--format", choices=["markdown", "json"], default="markdown", help="输出格式")
    return parser


def _apply_runtime_defaults(args: argparse.Namespace) -> argparse.Namespace:
    today = shanghai_today_str()
    if args.command in {"pre-market", "post-market", "market-cycle", "plan", "playbook", "dragon-tiger", "daily-dragon-tiger", "lockup", "quick-research"} and not getattr(args, "date", None):
        args.date = today
    return args


def main() -> None:
    parser = build_parser()
    args = _apply_runtime_defaults(parser.parse_args())
    skill = ASharesSkill()

    if args.command == "self-check":
        payload = skill.self_check()
        print(render_json(payload) if args.format == "json" else render_json(payload))
        return

    if args.command == "risk":
        payload = skill.risk(args.code, args.date)
        print(render_json(payload) if args.format == "json" else render_risk_report(payload))
        return

    if args.command == "diagnose":
        payload = skill.diagnose(args.code, args.scenario, args.horizon, args.risk_preference, args.date)
        print(render_json(payload) if args.format == "json" else render_diagnosis(payload))
        return

    if args.command == "pick":
        filters = normalize_filters(args.filters)
        payload = skill.pick(filters)
        print(render_json(payload) if args.format == "json" else render_stock_picker(payload, filters))
        return

    if args.command == "pre-market":
        payload = skill.pre_market_report(args.date)
        print(render_json(payload) if args.format == "json" else render_pre_market(payload))
        return

    if args.command == "post-market":
        payload = skill.post_market_review(args.date)
        print(render_json(payload) if args.format == "json" else render_post_market(payload))
        return

    if args.command == "market-cycle":
        payload = skill.market_cycle_report(args.date)
        print(render_json(payload) if args.format == "json" else render_market_cycle(payload))
        return

    if args.command == "plan":
        payload = skill.trading_plan_report(args.code, args.date)
        print(render_json(payload) if args.format == "json" else render_trading_plan(payload))
        return

    if args.command == "playbook":
        payload = skill.strategy_playbook(args.code, args.date)
        print(render_json(payload) if args.format == "json" else render_playbook(payload))
        return

    if args.command == "news":
        payload = skill.stock_news(args.code, args.page_size)
        print(render_json(payload) if args.format == "json" else render_news(payload, "个股新闻"))
        return

    if args.command == "telegraph":
        payload = skill.market_telegraph(args.page_size)
        print(render_json(payload) if args.format == "json" else render_news(payload, "市场快讯"))
        return

    if args.command == "global-news":
        payload = skill.global_news(args.page_size)
        print(render_json(payload) if args.format == "json" else render_news(payload, "全球财经快讯"))
        return

    if args.command == "announcements":
        payload = skill.announcements(args.code, args.page_size)
        print(render_json(payload) if args.format == "json" else render_news(payload, "巨潮公告"))
        return

    if args.command == "fund-flow":
        payload = skill.fund_flow(args.code, args.period, args.limit)
        print(render_json(payload) if args.format == "json" else render_fund_flow(payload))
        return

    if args.command == "sectors":
        payload = skill.sector_rankings(args.top)
        print(render_json(payload) if args.format == "json" else render_sector_rankings(payload))
        return

    if args.command == "hot-stocks":
        payload = skill.hot_stocks(args.date, args.page_size)
        print(render_json(payload) if args.format == "json" else render_hot_stocks(payload))
        return

    if args.command == "concept-blocks":
        payload = skill.concept_blocks(args.code)
        print(render_json(payload) if args.format == "json" else render_concept_blocks(payload))
        return

    if args.command == "reports":
        payload = skill.research_reports(args.code, args.page_size)
        print(render_json(payload) if args.format == "json" else render_reports(payload))
        return

    if args.command == "dragon-tiger":
        payload = skill.dragon_tiger(args.code, args.date, args.look_back)
        print(render_json(payload) if args.format == "json" else render_dragon_tiger(payload))
        return

    if args.command == "daily-dragon-tiger":
        payload = skill.daily_dragon_tiger(args.date, args.min_net_buy)
        print(render_json(payload) if args.format == "json" else render_daily_dragon_tiger(payload))
        return

    if args.command == "margin":
        payload = skill.margin_trading(args.code, args.page_size)
        print(render_json(payload) if args.format == "json" else render_rows(payload, "融资融券", ["date", "rzye", "rqye", "rzrqye"]))
        return

    if args.command == "block-trades":
        payload = skill.block_trades(args.code, args.page_size)
        print(render_json(payload) if args.format == "json" else render_rows(payload, "大宗交易", ["date", "price", "vol", "amount", "buyer", "premium_pct"]))
        return

    if args.command == "holders":
        payload = skill.holder_numbers(args.code, args.page_size)
        print(render_json(payload) if args.format == "json" else render_rows(payload, "股东户数", ["date", "holder_num", "change_ratio", "avg_shares"]))
        return

    if args.command == "dividends":
        payload = skill.dividend_history(args.code, args.page_size)
        print(render_json(payload) if args.format == "json" else render_rows(payload, "分红送转", ["date", "bonus_rmb", "transfer_ratio", "bonus_ratio", "plan"]))
        return

    if args.command == "lockup":
        payload = skill.lockup_expiry(args.code, args.date, args.forward_days)
        print(render_json(payload) if args.format == "json" else render_lockup(payload))
        return

    if args.command == "northbound":
        payload = skill.northbound_flow(args.history_days)
        print(render_json(payload) if args.format == "json" else render_northbound(payload))
        return

    if args.command == "stock-info":
        payload = skill.stock_info(args.code)
        print(render_json(payload) if args.format == "json" else render_stock_info(payload))
        return

    if args.command == "quotes":
        payload = skill.realtime_quotes(normalize_filters(args.codes), args.kind)
        print(render_json(payload) if args.format == "json" else render_quotes(payload))
        return

    if args.command == "valuation":
        payload = skill.valuation(args.code)
        print(render_json(payload) if args.format == "json" else render_valuation(payload))
        return

    if args.command == "compare":
        payload = skill.compare_valuations(normalize_filters(args.codes))
        print(render_json(payload) if args.format == "json" else render_compare(payload))
        return

    if args.command == "theme-research":
        payload = skill.thematic_research(normalize_filters(args.queries), args.channel, args.size, args.supplement_per_stock)
        print(render_json(payload) if args.format == "json" else render_theme_research(payload))
        return

    if args.command == "quick-research":
        payload = skill.quick_research(args.code, args.date)
        print(render_json(payload) if args.format == "json" else render_quick_research(payload))
        return

    if args.command == "kline":
        payload = skill.price_bars(args.code, args.frequency, args.limit)
        print(render_json(payload) if args.format == "json" else render_price_bars(payload))
        return

    if args.command == "order-book":
        payload = skill.order_book(args.code)
        print(render_json(payload) if args.format == "json" else render_order_book(payload))
        return

    if args.command == "transactions":
        payload = skill.transactions(args.code, args.start, args.limit)
        print(render_json(payload) if args.format == "json" else render_transactions(payload))
        return

    if args.command == "quarterly-snapshot":
        payload = skill.financial_snapshot(args.code)
        print(render_json(payload) if args.format == "json" else render_financial_snapshot(payload))
        return

    if args.command == "f10":
        payload = skill.f10_profile(args.code, args.category)
        print(render_json(payload) if args.format == "json" else render_f10_profile(payload))
        return

    if args.command == "finance":
        payload = skill.financial_report(args.code, args.report_type, args.page_size)
        print(render_json(payload) if args.format == "json" else render_rows(payload, "财报三表", ["报告日", "净利润", "营业总收入", "资产总计", "负债合计", "经营活动产生的现金流量净额"]))
        return

    if args.command == "consensus-eps":
        payload = skill.consensus_eps(args.code)
        print(render_json(payload) if args.format == "json" else render_consensus_eps(payload))
        return

    if args.command == "iwencai-search":
        payload = skill.iwencai_search(args.query, args.channel, args.size)
        print(render_json(payload) if args.format == "json" else render_iwencai(payload, "iwencai 语义检索"))
        return

    if args.command == "iwencai-query":
        payload = skill.iwencai_query(args.query, args.page, args.limit)
        print(render_json(payload) if args.format == "json" else render_iwencai(payload, "iwencai 结构化查询"))
        return

    parser.error(f"unknown command: {args.command}")


if __name__ == "__main__":
    main()
