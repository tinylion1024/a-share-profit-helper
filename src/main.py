"""Installable CLI entrypoint for the A-share skill."""

from __future__ import annotations

import argparse
from typing import Any, Callable, Optional

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
    render_flagship,
    render_fund_flow,
    render_hot_stocks,
    render_iwencai,
    render_json,
    render_leaders,
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
    render_review_cycle,
    render_risk_report,
    render_rows,
    render_review_trade,
    render_sector_rankings,
    render_stock_info,
    render_stock_picker,
    render_taoguba_hot,
    render_taoguba_sentiment,
    render_taoguba_stock,
    render_taoguba_vip,
    render_theme_research,
    render_trading_plan,
    render_transactions,
    render_user_memory,
    render_user_profile,
    render_valuation,
)
from src.skill import ASharesSkill
from src.utils.time import shanghai_today_str


def _optional_list(values: list[str] | None) -> list[str] | None:
    if values is None:
        return None
    items: list[str] = []
    for raw in values:
        for item in str(raw).split(","):
            token = item.strip()
            if token and token not in items:
                items.append(token)
    return items


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="A-share skill runner")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("self-check", help="检查 Skill 是否可运行")
    subparsers.add_parser("flagship", help="查看当前对外主打能力和推荐使用路径")
    subparsers.add_parser("profile-show", help="查看用户偏好和记忆摘要")

    profile_set = subparsers.add_parser("profile-set", help="设置用户偏好")
    profile_set.add_argument("--risk-preference", help="风险偏好")
    profile_set.add_argument("--default-horizon", help="默认周期")
    profile_set.add_argument("--preferred-sectors", nargs="+", help="偏好板块，支持逗号分隔")
    profile_set.add_argument("--avoided-sectors", nargs="+", help="回避板块，支持逗号分隔")
    profile_set.add_argument("--watchlist", nargs="+", help="自选股票代码/简称，支持逗号分隔")
    profile_set.add_argument("--focus-styles", nargs="+", help="偏好风格，支持逗号分隔")
    profile_set.add_argument("--notes", nargs="+", help="用户备注，支持逗号分隔")

    memory_show = subparsers.add_parser("memory-show", help="查看用户记忆")
    memory_show.add_argument("--code", help="股票代码或简称")

    memory_note = subparsers.add_parser("memory-note", help="记录股票笔记")
    memory_note.add_argument("--code", required=True, help="股票代码或简称")
    memory_note.add_argument("--note", required=True, help="记忆内容")

    memory_clear = subparsers.add_parser("memory-clear", help="清理用户记忆")
    memory_clear.add_argument("--code", help="仅清理某只股票的记忆")

    review_trade = subparsers.add_parser("review-trade", help="记录交易复盘，沉淀经验学习")
    review_trade.add_argument("--code", required=True, help="股票代码或简称")
    review_trade.add_argument("--outcome", required=True, choices=["win", "loss", "flat"], help="复盘结果")
    review_trade.add_argument("--return-pct", required=True, type=float, help="收益率，单位百分比")
    review_trade.add_argument("--holding-days", type=int, default=1, help="持有天数")
    review_trade.add_argument("--theme", help="关联题材")
    review_trade.add_argument("--note", help="复盘备注")

    weekly_review = subparsers.add_parser("weekly-review", help="周期复盘，总结最近交易表现")
    weekly_review.add_argument("--limit", type=int, default=20, help="最近复盘条数")
    weekly_review.add_argument("--start-date", help="开始日期 YYYY-MM-DD")
    weekly_review.add_argument("--end-date", help="结束日期 YYYY-MM-DD")

    memory_feedback = subparsers.add_parser("memory-feedback", help="把复盘结果转成下一阶段的记忆反馈")
    memory_feedback.add_argument("--limit", type=int, default=20, help="回看复盘条数")

    risk = subparsers.add_parser("risk", help="风险扫描")
    risk.add_argument("--code", required=True, help="股票代码或简称")
    risk.add_argument("--date", help="日期 (YYYY-MM-DD)")

    diagnose = subparsers.add_parser("diagnose", help="诊股")
    diagnose.add_argument("--code", required=True, help="股票代码或简称")
    diagnose.add_argument("--scenario", default="诊股", help="场景名称")
    diagnose.add_argument("--horizon", help="持仓周期")
    diagnose.add_argument("--risk-preference", help="风险偏好")
    diagnose.add_argument("--date", help="日期 (YYYY-MM-DD)")

    pick = subparsers.add_parser("pick", help="选股")
    pick.add_argument("--filters", nargs="+", default=["basic", "tech", "catalyst"], help="过滤器")

    pre_market = subparsers.add_parser("pre-market", help="盘前分析")
    pre_market.add_argument("--date", help="日期 (YYYY-MM-DD)")

    post_market = subparsers.add_parser("post-market", help="盘后复盘")
    post_market.add_argument("--date", help="日期 (YYYY-MM-DD)")

    market_cycle = subparsers.add_parser("market-cycle", help="方法论市场周期判断")
    market_cycle.add_argument("--date", help="日期 (YYYY-MM-DD)")

    leaders = subparsers.add_parser("leaders", help="全市场主线/龙头扫描")
    leaders.add_argument("--date", help="日期 (YYYY-MM-DD)")

    plan = subparsers.add_parser("plan", help="交易计划")
    plan.add_argument("--code", required=True, help="股票代码或简称")
    plan.add_argument("--date", help="日期 (YYYY-MM-DD)")

    playbook = subparsers.add_parser("playbook", help="方法论单票执行手册")
    playbook.add_argument("--code", required=True, help="股票代码或简称")
    playbook.add_argument("--date", help="日期 (YYYY-MM-DD)")

    news = subparsers.add_parser("news", help="个股新闻")
    news.add_argument("--code", required=True, help="股票代码或简称")
    news.add_argument("--page-size", type=int, default=10, help="返回条数")

    telegraph = subparsers.add_parser("telegraph", help="市场快讯")
    telegraph.add_argument("--page-size", type=int, default=20, help="返回条数")

    global_news = subparsers.add_parser("global-news", help="全球财经快讯")
    global_news.add_argument("--page-size", type=int, default=20, help="返回条数")

    announcements = subparsers.add_parser("announcements", help="巨潮公告")
    announcements.add_argument("--code", required=True, help="股票代码或简称")
    announcements.add_argument("--page-size", type=int, default=10, help="返回条数")

    fund_flow = subparsers.add_parser("fund-flow", help="资金流")
    fund_flow.add_argument("--code", required=True, help="股票代码或简称")
    fund_flow.add_argument("--period", choices=["minute", "120d"], default="minute", help="资金流周期")
    fund_flow.add_argument("--limit", type=int, default=120, help="120日资金流条数")

    sectors = subparsers.add_parser("sectors", help="行业板块排名")
    sectors.add_argument("--top", type=int, default=10, help="Top/Bottom 返回条数")

    hot_stocks = subparsers.add_parser("hot-stocks", help="同花顺热点强势股")
    hot_stocks.add_argument("--date", help="观察日 (YYYY-MM-DD)")
    hot_stocks.add_argument("--page-size", type=int, default=20, help="返回条数")

    taoguba_hot = subparsers.add_parser("taoguba-hot", help="淘股吧点赞榜热点")
    taoguba_hot.add_argument("--page-size", type=int, default=10, help="返回条数")
    taoguba_hot.add_argument("--include-content", action="store_true", help="抓取正文摘要")

    taoguba_sentiment = subparsers.add_parser("taoguba-sentiment", help="淘股吧市场舆情")
    taoguba_sentiment.add_argument("--page-size", type=int, default=20, help="样本文章数")

    taoguba_stock = subparsers.add_parser("taoguba-stock", help="淘股吧个股情绪")
    taoguba_stock.add_argument("--code", required=True, help="股票代码或简称")
    taoguba_stock.add_argument("--page-size", type=int, default=30, help="评论条数")

    taoguba_vip = subparsers.add_parser("taoguba-vip", help="淘股吧大V观点")
    taoguba_vip.add_argument("--code", help="股票代码或简称")
    taoguba_vip.add_argument("--page-size", type=int, default=10, help="返回条数")

    concept_blocks = subparsers.add_parser("concept-blocks", help="概念板块归属")
    concept_blocks.add_argument("--code", required=True, help="股票代码或简称")

    reports = subparsers.add_parser("reports", help="个股研报")
    reports.add_argument("--code", required=True, help="股票代码或简称")
    reports.add_argument("--page-size", type=int, default=10, help="返回条数")

    dragon_tiger = subparsers.add_parser("dragon-tiger", help="个股龙虎榜")
    dragon_tiger.add_argument("--code", required=True, help="股票代码或简称")
    dragon_tiger.add_argument("--date", help="交易日 (YYYY-MM-DD)")
    dragon_tiger.add_argument("--look-back", type=int, default=30, help="回看天数")

    daily_dragon_tiger = subparsers.add_parser("daily-dragon-tiger", help="全市场龙虎榜")
    daily_dragon_tiger.add_argument("--date", help="交易日 (YYYY-MM-DD)")
    daily_dragon_tiger.add_argument("--min-net-buy", type=float, help="净买额下限，单位万元")

    margin = subparsers.add_parser("margin", help="融资融券")
    margin.add_argument("--code", required=True, help="股票代码或简称")
    margin.add_argument("--page-size", type=int, default=10, help="返回条数")

    block_trades = subparsers.add_parser("block-trades", help="大宗交易")
    block_trades.add_argument("--code", required=True, help="股票代码或简称")
    block_trades.add_argument("--page-size", type=int, default=10, help="返回条数")

    holders = subparsers.add_parser("holders", help="股东户数")
    holders.add_argument("--code", required=True, help="股票代码或简称")
    holders.add_argument("--page-size", type=int, default=10, help="返回条数")

    dividends = subparsers.add_parser("dividends", help="分红送转")
    dividends.add_argument("--code", required=True, help="股票代码或简称")
    dividends.add_argument("--page-size", type=int, default=10, help="返回条数")

    lockup = subparsers.add_parser("lockup", help="限售解禁")
    lockup.add_argument("--code", required=True, help="股票代码或简称")
    lockup.add_argument("--date", help="观察日 (YYYY-MM-DD)")
    lockup.add_argument("--forward-days", type=int, default=90, help="未来观察天数")

    northbound = subparsers.add_parser("northbound", help="北向资金")
    northbound.add_argument("--history-days", type=int, default=20, help="缓存历史天数")

    stock_info = subparsers.add_parser("stock-info", help="个股信息")
    stock_info.add_argument("--code", required=True, help="股票代码或简称")

    quotes = subparsers.add_parser("quotes", help="腾讯财经批量实时行情")
    quotes.add_argument("--codes", nargs="+", required=True, help="股票/指数/ETF 代码或简称，支持逗号分隔")
    quotes.add_argument("--kind", choices=["auto", "stock", "index", "etf"], default="auto", help="代码类型")

    valuation = subparsers.add_parser("valuation", help="单票完整估值")
    valuation.add_argument("--code", required=True, help="股票代码或简称")

    compare = subparsers.add_parser("compare", help="批量估值对比")
    compare.add_argument("--codes", nargs="+", required=True, help="股票代码或简称，支持逗号分隔")

    theme_research = subparsers.add_parser("theme-research", help="主题研报批量检索")
    theme_research.add_argument("--queries", nargs="+", required=True, help="检索语句，支持逗号分隔")
    theme_research.add_argument("--channel", choices=["report", "announcement", "news"], default="report", help="检索频道")
    theme_research.add_argument("--size", type=int, default=20, help="每个query的返回条数")
    theme_research.add_argument("--supplement-per-stock", type=int, default=2, help="每个标的补充的东财研报数")

    quick_research = subparsers.add_parser("quick-research", help="新标的快速调研")
    quick_research.add_argument("--code", required=True, help="股票代码或简称")
    quick_research.add_argument("--date", help="观察日 (YYYY-MM-DD)")

    kline = subparsers.add_parser("kline", help="mootdx K线")
    kline.add_argument("--code", required=True, help="股票代码或简称")
    kline.add_argument("--frequency", type=int, default=4, help="4日线 5周线 6月线 7/8/9/10/11分时")
    kline.add_argument("--limit", type=int, default=20, help="返回条数")

    order_book = subparsers.add_parser("order-book", help="mootdx 五档盘口")
    order_book.add_argument("--code", required=True, help="股票代码或简称")

    transactions = subparsers.add_parser("transactions", help="mootdx 逐笔成交")
    transactions.add_argument("--code", required=True, help="股票代码或简称")
    transactions.add_argument("--start", type=int, default=0, help="起始偏移")
    transactions.add_argument("--limit", type=int, default=50, help="返回条数")

    quarterly_snapshot = subparsers.add_parser("quarterly-snapshot", help="mootdx 季报快照")
    quarterly_snapshot.add_argument("--code", required=True, help="股票代码或简称")

    f10 = subparsers.add_parser("f10", help="mootdx F10 文本资料")
    f10.add_argument("--code", required=True, help="股票代码或简称")
    f10.add_argument("--category", help="F10 分类，如 最新提示 / 公司概况 / 财务分析")

    finance = subparsers.add_parser("finance", help="新浪财报三表")
    finance.add_argument("--code", required=True, help="股票代码或简称")
    finance.add_argument("--report-type", choices=["lrb", "fzb", "llb"], default="lrb", help="报表类型")
    finance.add_argument("--page-size", type=int, default=20, help="返回期数")

    consensus_eps = subparsers.add_parser("consensus-eps", help="同花顺一致预期EPS")
    consensus_eps.add_argument("--code", required=True, help="股票代码或简称")

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
    args.date_inferred = False
    if args.command in {"pre-market", "post-market", "market-cycle", "leaders", "plan", "playbook", "dragon-tiger", "daily-dragon-tiger", "lockup", "quick-research"} and not getattr(args, "date", None):
        args.date = today
        args.date_inferred = True
    return args


CommandHandler = Callable[[ASharesSkill, argparse.Namespace], tuple[Any, Callable[..., str], tuple[Any, ...], Optional[Any]]]


def _resolved_date(args: argparse.Namespace) -> str | None:
    return None if getattr(args, "date_inferred", False) else getattr(args, "date", None)


def _emit_output(
    args: argparse.Namespace,
    payload: Any,
    renderer: Callable[..., str],
    renderer_args: tuple[Any, ...] = (),
    markdown_payload: Optional[Any] = None,
) -> None:
    if args.format == "json":
        print(render_json(payload))
        return
    print(renderer(payload if markdown_payload is None else markdown_payload, *renderer_args))


def _build_command_handlers() -> dict[str, CommandHandler]:
    return {
        "self-check": lambda skill, args: (skill.self_check(), render_json, (), None),
        "flagship": lambda skill, args: (skill.flagship_overview(), render_flagship, (), None),
        "profile-show": lambda skill, args: (skill.user_profile(), render_user_profile, (), None),
        "profile-set": lambda skill, args: (
            skill.update_user_profile(
                risk_preference=args.risk_preference,
                default_horizon=args.default_horizon,
                preferred_sectors=_optional_list(args.preferred_sectors),
                avoided_sectors=_optional_list(args.avoided_sectors),
                watchlist=_optional_list(args.watchlist),
                focus_styles=_optional_list(args.focus_styles),
                notes=_optional_list(args.notes),
            ),
            render_user_profile,
            (),
            None,
        ),
        "memory-show": lambda skill, args: (skill.user_memory(args.code), render_user_memory, (), None),
        "memory-note": lambda skill, args: (skill.add_memory_note(args.code, args.note), render_user_memory, (), None),
        "memory-clear": lambda skill, args: (skill.clear_memory(args.code), render_user_memory, (), None),
        "review-trade": lambda skill, args: (
            skill.review_trade(
                args.code,
                outcome=args.outcome,
                return_pct=args.return_pct,
                holding_days=args.holding_days,
                theme=args.theme,
                note=args.note,
            ),
            render_review_trade,
            (),
            None,
        ),
        "weekly-review": lambda skill, args: (
            skill.weekly_review(limit=args.limit, start_date=args.start_date, end_date=args.end_date),
            render_review_cycle,
            (),
            None,
        ),
        "memory-feedback": lambda skill, args: (skill.memory_feedback(limit=args.limit), render_review_cycle, (), None),
        "risk": lambda skill, args: (skill.risk(args.code, args.date), render_risk_report, (), None),
        "diagnose": lambda skill, args: (
            skill.diagnose(args.code, args.scenario, args.horizon, args.risk_preference, args.date),
            render_diagnosis,
            (),
            None,
        ),
        "pick": lambda skill, args: (
            skill.pick(normalize_filters(args.filters)),
            render_stock_picker,
            (normalize_filters(args.filters),),
            None,
        ),
        "pre-market": lambda skill, args: (skill.pre_market_report(_resolved_date(args)), render_pre_market, (), None),
        "post-market": lambda skill, args: (skill.post_market_review(_resolved_date(args)), render_post_market, (), None),
        "market-cycle": lambda skill, args: (skill.market_cycle_report(_resolved_date(args)), render_market_cycle, (), None),
        "leaders": lambda skill, args: (skill.leaders_scan(_resolved_date(args)), render_leaders, (), None),
        "plan": lambda skill, args: (skill.trading_plan_report(args.code, args.date), render_trading_plan, (), None),
        "playbook": lambda skill, args: (skill.strategy_playbook(args.code, _resolved_date(args)), render_playbook, (), None),
        "news": lambda skill, args: (skill.stock_news(args.code, args.page_size), render_news, ("个股新闻",), None),
        "telegraph": lambda skill, args: (skill.market_telegraph(args.page_size), render_news, ("市场快讯",), None),
        "global-news": lambda skill, args: (skill.global_news(args.page_size), render_news, ("全球财经快讯",), None),
        "announcements": lambda skill, args: (skill.announcements(args.code, args.page_size), render_news, ("巨潮公告",), None),
        "fund-flow": lambda skill, args: (skill.fund_flow(args.code, args.period, args.limit), render_fund_flow, (), None),
        "sectors": lambda skill, args: (skill.sector_rankings(args.top), render_sector_rankings, (), None),
        "hot-stocks": lambda skill, args: (skill.hot_stocks(args.date, args.page_size), render_hot_stocks, (), None),
        "taoguba-hot": lambda skill, args: (skill.taoguba_hot(args.page_size, args.include_content), render_taoguba_hot, (), None),
        "taoguba-sentiment": lambda skill, args: (skill.taoguba_market_sentiment(args.page_size), render_taoguba_sentiment, (), None),
        "taoguba-stock": lambda skill, args: (skill.taoguba_stock_sentiment(args.code, args.page_size), render_taoguba_stock, (), None),
        "taoguba-vip": lambda skill, args: (skill.taoguba_vip_views(args.code, args.page_size), render_taoguba_vip, (), None),
        "concept-blocks": lambda skill, args: (skill.concept_blocks(args.code), render_concept_blocks, (), None),
        "reports": lambda skill, args: (skill.research_reports(args.code, args.page_size), render_reports, (), None),
        "dragon-tiger": lambda skill, args: (skill.dragon_tiger(args.code, args.date, args.look_back), render_dragon_tiger, (), None),
        "daily-dragon-tiger": lambda skill, args: (skill.daily_dragon_tiger(args.date, args.min_net_buy), render_daily_dragon_tiger, (), None),
        "margin": lambda skill, args: (
            skill.margin_trading(args.code, args.page_size),
            render_rows,
            ("融资融券", ["date", "rzye", "rqye", "rzrqye"]),
            None,
        ),
        "block-trades": lambda skill, args: (
            skill.block_trades(args.code, args.page_size),
            render_rows,
            ("大宗交易", ["date", "price", "vol", "amount", "buyer", "premium_pct"]),
            None,
        ),
        "holders": lambda skill, args: (
            skill.holder_numbers(args.code, args.page_size),
            render_rows,
            ("股东户数", ["date", "holder_num", "change_ratio", "avg_shares"]),
            None,
        ),
        "dividends": lambda skill, args: (
            skill.dividend_history(args.code, args.page_size),
            render_rows,
            ("分红送转", ["date", "bonus_rmb", "transfer_ratio", "bonus_ratio", "plan"]),
            None,
        ),
        "lockup": lambda skill, args: (skill.lockup_expiry(args.code, args.date, args.forward_days), render_lockup, (), None),
        "northbound": lambda skill, args: (skill.northbound_flow(args.history_days), render_northbound, (), None),
        "stock-info": lambda skill, args: (skill.stock_info(args.code), render_stock_info, (), None),
        "quotes": lambda skill, args: (skill.realtime_quotes(normalize_filters(args.codes), args.kind), render_quotes, (), None),
        "valuation": lambda skill, args: (skill.valuation(args.code), render_valuation, (), None),
        "compare": lambda skill, args: (skill.compare_valuations(normalize_filters(args.codes)), render_compare, (), None),
        "theme-research": lambda skill, args: (
            skill.thematic_research(normalize_filters(args.queries), args.channel, args.size, args.supplement_per_stock),
            render_theme_research,
            (),
            None,
        ),
        "quick-research": lambda skill, args: (skill.quick_research(args.code, _resolved_date(args)), render_quick_research, (), None),
        "kline": lambda skill, args: (skill.price_bars(args.code, args.frequency, args.limit), render_price_bars, (), None),
        "order-book": lambda skill, args: (skill.order_book(args.code), render_order_book, (), None),
        "transactions": lambda skill, args: (skill.transactions(args.code, args.start, args.limit), render_transactions, (), None),
        "quarterly-snapshot": lambda skill, args: (skill.financial_snapshot(args.code), render_financial_snapshot, (), None),
        "f10": lambda skill, args: (skill.f10_profile(args.code, args.category), render_f10_profile, (), None),
        "finance": lambda skill, args: (
            skill.financial_report(args.code, args.report_type, args.page_size),
            render_rows,
            ("财报三表", ["报告日", "净利润", "营业总收入", "资产总计", "负债合计", "经营活动产生的现金流量净额"]),
            None,
        ),
        "consensus-eps": lambda skill, args: (skill.consensus_eps(args.code), render_consensus_eps, (), None),
        "iwencai-search": lambda skill, args: (skill.iwencai_search(args.query, args.channel, args.size), render_iwencai, ("iwencai 语义检索",), None),
        "iwencai-query": lambda skill, args: (skill.iwencai_query(args.query, args.page, args.limit), render_iwencai, ("iwencai 结构化查询",), None),
    }


def main() -> None:
    parser = build_parser()
    args = _apply_runtime_defaults(parser.parse_args())
    skill = ASharesSkill()
    handlers = _build_command_handlers()
    handler = handlers.get(args.command)
    if handler is None:
        parser.error(f"unknown command: {args.command}")
    payload, renderer, renderer_args, markdown_payload = handler(skill, args)
    if args.command == "profile-set":
        markdown_payload = {**payload, "memory": skill.user_profile().get("memory", {})}
    _emit_output(args, payload, renderer, renderer_args, markdown_payload)


if __name__ == "__main__":
    main()
