"""CLI helpers and renderers."""

from __future__ import annotations

import json
from typing import Iterable


def normalize_filters(values: Iterable[str]) -> list[str]:
    filters: list[str] = []
    for raw in values:
        for item in raw.split(","):
            token = item.strip()
            if token and token not in filters:
                filters.append(token)
    return filters or ["basic", "tech", "catalyst"]


def render_json(payload: object) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2)


def render_risk_report(payload: dict) -> str:
    red_flags = "、".join(payload["red_flags"]) if payload["red_flags"] else "无"
    warnings = "、".join(payload["warnings"]) if payload["warnings"] else "无"
    discipline = payload.get("strategy_discipline", {})
    user_context = payload.get("user_context", {}).get("preferences", {})
    return (
        f"# 风险扫描 {payload['stock_code']}\n\n"
        f"- 风险等级: {payload['risk_level']}\n"
        f"- 用户偏好风险级别: {user_context.get('risk_preference', '-')}\n"
        f"- 红线项目: {red_flags}\n"
        f"- 警告项目: {warnings}\n"
        f"- 方法论阶段: {discipline.get('market_stage', '-')}\n"
        f"- 建议仓位: {round(discipline.get('preferred_position', 0) * 100)}%\n"
        f"- 结论: {'可继续跟踪' if payload['is_clear'] else '禁止推荐'}"
    )


def render_stock_picker(candidates: list[dict], filters: list[str]) -> str:
    lines = [
        "# 智能选股报告",
        "",
        f"筛选条件: {', '.join(filters)}",
        "",
        "| 股票 | 代码 | 风格 | 介入方式 | 方法论分 | 风险收益比 | 催化因素 |",
        "|------|------|------|----------|----------|------------|----------|",
    ]
    for item in candidates:
        pref = item.get("user_preference", {})
        preference_badges = []
        if pref.get("watchlist_match"):
            preference_badges.append("自选")
        if pref.get("preferred_sector_match"):
            preference_badges.append("偏好板块")
        if pref.get("focus_style_match"):
            preference_badges.append("偏好风格")
        if pref.get("avoided_sector_match"):
            preference_badges.append("回避板块")
        lines.append(
            f"| {item['name']} | {item['code']} | {item.get('style', '')} | {item.get('setup', '')} | {item.get('methodology_score', '')} | "
            f"{item['risk_reward_ratio']} | {(item['catalyst'] or '无')} {'/'.join(preference_badges)} |"
        )
    if not candidates:
        lines.append("| - | - | - | - | - | 无符合条件标的 |")
    return "\n".join(lines)


def render_diagnosis(payload: dict) -> str:
    rating = payload["rating_4d"]
    conclusion = payload["conclusion"]
    setup = payload.get("strategy_system", {}).get("trade_setup", {})
    community = payload.get("strategy_system", {}).get("community", {})
    time_context = payload.get("time_context", {})
    preference_alignment = payload.get("preference_alignment", {})
    return (
        f"## {payload['stock_code']} 诊断报告\n\n"
        f"- 场景: {payload['needs_clarified']['scenario']}\n"
        f"- 时间环境: {time_context.get('session', '-')}\n"
        f"- 结论基准日: {time_context.get('analysis_date', '-')}\n"
        f"- 用户风险偏好 / 周期: {preference_alignment.get('risk_preference', '-')} / {preference_alignment.get('default_horizon', '-')}\n"
        f"- 四维评级: {rating['level']}\n"
        f"- 风险等级: {payload['risk']['risk_level']}\n"
        f"- 方法论阶段: {conclusion.get('market_stage', '')}\n"
        f"- 标的定位: {setup.get('style', conclusion.get('style', ''))}\n"
        f"- 介入方式: {setup.get('setup', conclusion.get('setup', ''))}\n"
        f"- 社区情绪: {community.get('mood', '未知')} / {community.get('sentiment_score', '-')}\n"
        f"- 建议动作: {conclusion['action']}\n"
        f"- 买入价: {conclusion['entry_price']}\n"
        f"- 止损价: {conclusion['stop_loss']}\n"
        f"- 目标价: {conclusion['target_price']}\n"
        f"- 建议仓位: {round(conclusion['position_ratio'] * 100)}%\n"
        f"- 结论: {conclusion['summary']}"
    )


def render_pre_market(payload: dict) -> str:
    return (
        f"# 盘前报告 {payload['date']}\n\n"
        f"- 隔夜情绪: {payload['overnight_sentiment']}\n"
        f"- 市场阶段: {payload.get('market_stage', '-')}\n"
        f"- 仓位计划: {payload.get('position_plan', '-')}\n"
        f"- 政策重点: {'；'.join(payload['policy_highlights'])}\n"
        f"- 昨日遗留: {payload['yesterday_leverage']}\n"
        f"- 乐观剧本: {payload['today_script_optimistic']}\n"
        f"- 悲观剧本: {payload['today_script_pessimistic']}\n"
        f"- 置信度: {payload['confidence']}"
    )


def render_post_market(payload: dict) -> str:
    summary = payload["index_summary"]
    return (
        f"# 盘后复盘 {payload['date']}\n\n"
        f"- 成交额(亿): {summary['成交额(亿)']}\n"
        f"- 涨跌比: {summary['涨跌比']}\n"
        f"- 平盘数: {summary.get('平盘数', 0)}\n"
        f"- 流动性模式: {summary['流动性模式']}\n"
        f"- 市场阶段: {payload.get('market_stage', '-')}\n"
        f"- 情绪监控: {payload['sentiment_monitor']}\n"
        f"- 核心个股: {'、'.join(payload['key_stocks'])}\n"
        f"- 板块轮动: {payload['sector_rotation']}\n"
        f"- 明日关注: {'；'.join(payload['tomorrow_focus'])}"
    )


def render_trading_plan(payload: dict) -> str:
    return (
        f"# 交易计划 {payload['stock_name']} ({payload['stock_code']})\n\n"
        f"- 日期: {payload['date']}\n"
        f"- 方法论阶段: {payload.get('methodology', {}).get('market_cycle', {}).get('stage', '-')}\n"
        f"- 标的定位: {payload.get('methodology', {}).get('trade_setup', {}).get('style', '-')}\n"
        f"- 乐观触发: {'；'.join(payload['optimistic_triggers'])}\n"
        f"- 乐观计划: {payload['optimistic_entry']} -> {payload['optimistic_target']} "
        f"(止损 {payload['optimistic_stop_loss']}, 仓位 {round(payload['optimistic_position'] * 100)}%)\n"
        f"- 悲观触发: {'；'.join(payload['pessimistic_triggers'])}\n"
        f"- 风控: 等级 {payload['risk_control']['risk_level']}，红线 {payload['risk_control']['red_flags'] or ['无']}"
    )


def render_market_cycle(payload: dict) -> str:
    playbook = payload.get("playbook", {})
    summary = payload.get("market_snapshot", {})
    community = payload.get("community", {})
    time_context = payload.get("time_context", {})
    lines = [
        f"# 市场周期 {payload.get('date', '')}",
        "",
        f"- 数据源: {payload.get('provider', '')}",
        f"- 时间环境: {time_context.get('session', '-')}",
        f"- 结论基准日: {time_context.get('analysis_date', '-')}",
        f"- 阶段 / 环境: {playbook.get('stage', '')} / {playbook.get('environment', '')}",
        f"- 仓位上限: {round(playbook.get('position_upper_bound', 0) * 100)}%",
        f"- 情绪 / 趋势: {summary.get('sentiment_score', '')} / {summary.get('trend_score', '')}",
        f"- 社区情绪: {community.get('mood', '未知')} / {community.get('sentiment_score', '-')}",
        f"- 涨跌家数: {summary.get('advancers', 0)} / {summary.get('decliners', 0)}",
        f"- 主线板块: {', '.join(summary.get('hot_sectors', [])) or '无'}",
        f"- 情绪锚点: {', '.join(summary.get('leaders', [])) or '无'}",
        "",
        "## 买入节奏",
    ]
    for item in playbook.get("buy_strategy", []):
        lines.append(f"- {item}")
    lines.append("")
    lines.append("## 卖出节奏")
    for item in playbook.get("sell_strategy", []):
        lines.append(f"- {item}")
    lines.append("")
    lines.append("## 避免动作")
    for item in playbook.get("avoid_actions", []):
        lines.append(f"- {item}")
    return "\n".join(lines)


def render_playbook(payload: dict) -> str:
    playbook = payload.get("playbook", {})
    setup = playbook.get("trade_setup", {})
    position_plan = playbook.get("position_plan", {})
    lines = [
        f"# 执行手册 {playbook.get('stock_name', '')} ({payload.get('stock_code', '')})",
        "",
        f"- 日期: {payload.get('date', '')}",
        f"- 市场阶段: {playbook.get('market_cycle', {}).get('stage', '')}",
        f"- 标的定位: {setup.get('style', '')}",
        f"- 介入方式: {setup.get('setup', '')}",
        f"- 方法论分: {setup.get('methodology_score', '')}",
        f"- 建议仓位 / 首仓: {round(position_plan.get('preferred_position', 0) * 100)}% / {round(position_plan.get('first_probe_position', 0) * 100)}%",
        "",
        "## 入场信号",
    ]
    for item in playbook.get("entry_signals", []):
        lines.append(f"- {item}")
    lines.append("")
    lines.append("## 加仓信号")
    for item in playbook.get("add_signals", []):
        lines.append(f"- {item}")
    lines.append("")
    lines.append("## 减仓信号")
    for item in playbook.get("reduce_signals", []):
        lines.append(f"- {item}")
    lines.append("")
    lines.append("## 离场信号")
    for item in playbook.get("exit_signals", []):
        lines.append(f"- {item}")
    if playbook.get("no_trade_conditions"):
        lines.append("")
        lines.append("## 不出手条件")
        for item in playbook.get("no_trade_conditions", []):
            lines.append(f"- {item}")
    return "\n".join(lines)


def render_news(payload: dict, title: str) -> str:
    lines = [f"# {title}", ""]
    if payload.get("stock_code"):
        lines.append(f"- 标的: {payload['stock_code']}")
    lines.append(f"- 数据源: {payload.get('provider', '')}")
    lines.append("")
    for item in payload.get("items", []):
        time = item.get("time") or item.get("date") or "-"
        source = item.get("source") or item.get("type") or "-"
        headline = item.get("title") or "-"
        extra = item.get("content") or item.get("summary") or item.get("url") or ""
        lines.append(f"- {time} | {source} | {headline}")
        if extra:
            lines.append(f"  {extra}")
    if not payload.get("items"):
        lines.append("- 无数据")
    return "\n".join(lines)


def render_fund_flow(payload: dict) -> str:
    latest = payload.get("latest") or {}
    label = "分钟级" if payload.get("period") == "minute" else "120日"
    return (
        f"# 资金流 {payload['stock_code']}\n\n"
        f"- 周期: {label}\n"
        f"- 数据源: {payload.get('provider', '')}\n"
        f"- 样本数: {payload.get('count', 0)}\n"
        f"- 主力累计净流入: {payload.get('total_main_net', 0)} 元\n"
        f"- 最新切片: {latest}"
    )


def render_sector_rankings(payload: dict) -> str:
    lines = [
        "# 行业板块排名",
        "",
        f"- 数据源: {payload.get('provider', '')}",
        f"- 行业数量: {payload.get('total', 0)}",
        "",
        "## Top",
    ]
    for item in payload.get("top", []):
        lines.append(
            f"- {item['rank']}. {item['name']} {item['change_pct']}% 涨{item['up_count']}跌{item['down_count']} 领涨 {item['leader']}"
        )
    lines.append("")
    lines.append("## Bottom")
    for item in payload.get("bottom", []):
        lines.append(
            f"- {item['rank']}. {item['name']} {item['change_pct']}% 涨{item['up_count']}跌{item['down_count']} 领涨 {item['leader']}"
        )
    return "\n".join(lines)


def render_hot_stocks(payload: dict) -> str:
    lines = ["# 同花顺热点强势股", "", f"- 数据源: {payload.get('provider', '')}", ""]
    for item in payload.get("items", []):
        lines.append(
            f"- {item['code']} {item['name']} | 涨幅 {item['change_pct']}% | "
            f"换手 {item['turnover_pct']}% | 归因 {item['reason']}"
        )
    if not payload.get("items"):
        lines.append("- 无数据")
    return "\n".join(lines)


def render_taoguba_hot(payload: dict) -> str:
    lines = ["# 淘股吧热点", "", f"- 数据源: {payload.get('provider', '')}", ""]
    for item in payload.get("items", []):
        lines.append(
            f"- {item.get('author_name', '')} | {item.get('title', '')} | "
            f"赞 {item.get('likes', 0)} | 回 {item.get('replies', 0)}"
        )
    if not payload.get("items"):
        lines.append("- 无数据")
    return "\n".join(lines)


def render_taoguba_sentiment(payload: dict) -> str:
    lines = [
        "# 淘股吧舆情",
        "",
        f"- 数据源: {payload.get('provider', '')}",
        f"- 情绪分: {payload.get('sentiment_score', '')}",
        f"- 情绪标签: {payload.get('mood', '')}",
        f"- 一致性: {payload.get('consensus_level', '')}",
        f"- 热度分: {payload.get('heat_score', '')}",
        "",
        "## 热点主题",
    ]
    for item in payload.get("hot_topics", []):
        lines.append(f"- {item.get('topic', '')} | 提及 {item.get('mentions', 0)} | 看多占比 {item.get('bullish_ratio', 0)}")
    if not payload.get("hot_topics"):
        lines.append("- 无数据")
    lines.append("")
    lines.append("## 大V聚焦")
    for item in payload.get("vip_focus", []):
        lines.append(f"- {item}")
    if not payload.get("vip_focus"):
        lines.append("- 无数据")
    return "\n".join(lines)


def render_taoguba_stock(payload: dict) -> str:
    lines = [
        f"# 淘股吧个股情绪 {payload.get('stock_name', '')} ({payload.get('stock_code', '')})",
        "",
        f"- 数据源: {payload.get('provider', '')}",
        f"- 情绪分: {payload.get('sentiment_score', '')}",
        f"- 情绪标签: {payload.get('mood', '')}",
        f"- 评论数 / 大V评论数: {payload.get('comment_count', 0)} / {payload.get('vip_comment_count', 0)}",
        f"- 关键词: {', '.join(payload.get('key_phrases', [])) or '无'}",
        "",
        "## 大V观点",
    ]
    for item in payload.get("vip_views", []):
        lines.append(f"- {item.get('author_name', '')}({item.get('tier', '')}) | {item.get('stance', '')} | {item.get('summary', '')}")
    if not payload.get("vip_views"):
        lines.append("- 无数据")
    return "\n".join(lines)


def render_taoguba_vip(payload: dict) -> str:
    lines = ["# 淘股吧大V观点", "", f"- 数据源: {payload.get('provider', '')}", ""]
    for item in payload.get("items", []):
        lines.append(
            f"- {item.get('author_name', '')}({item.get('tier', '')}) | {item.get('stance', '')} | "
            f"{item.get('title', '')}"
        )
    if not payload.get("items"):
        lines.append("- 无数据")
    return "\n".join(lines)


def render_user_profile(payload: dict) -> str:
    preferences = payload.get("preferences", {})
    memory = payload.get("memory", {})
    return (
        "# 用户档案\n\n"
        f"- 风险偏好: {preferences.get('risk_preference', '-')}\n"
        f"- 默认周期: {preferences.get('default_horizon', '-')}\n"
        f"- 偏好板块: {', '.join(preferences.get('preferred_sectors', [])) or '无'}\n"
        f"- 回避板块: {', '.join(preferences.get('avoided_sectors', [])) or '无'}\n"
        f"- 自选池: {', '.join(preferences.get('watchlist', [])) or '无'}\n"
        f"- 关注风格: {', '.join(preferences.get('focus_styles', [])) or '无'}\n"
        f"- 备注: {'；'.join(preferences.get('notes', [])) or '无'}\n"
        f"- 最近关注股票: {', '.join(memory.get('recent_stocks', [])) or '无'}\n"
        f"- 股票画像数 / 题材画像数: {len(memory.get('stock_profiles', {}))} / {len(memory.get('theme_profiles', {}))}"
    )


def render_user_memory(payload: dict) -> str:
    memory = payload.get("memory", {})
    lines = [
        "# 用户记忆",
        "",
        f"- 最近关注股票: {', '.join(memory.get('recent_stocks', [])) or '无'}",
        "",
        "## 最近工作流",
    ]
    for item in memory.get("recent_workflows", [])[:10]:
        lines.append(f"- {item.get('timestamp', '')} | {item.get('workflow', '')} | {item.get('stock_code', '')} | {item.get('summary', '')}")
    if not memory.get("recent_workflows"):
        lines.append("- 无数据")
    lines.append("")
    lines.append("## 标的笔记")
    stock_notes = memory.get("stock_notes", {})
    if stock_notes:
        for code, notes in stock_notes.items():
            lines.append(f"- {code}: {'；'.join(notes)}")
    else:
        lines.append("- 无数据")
    lines.append("")
    lines.append("## 股票画像")
    stock_profiles = memory.get("stock_profiles", {})
    if stock_profiles:
        for code, profile in list(stock_profiles.items())[:10]:
            lines.append(
                f"- {code} | {profile.get('stock_name', '')} | "
                f"风格 {profile.get('last_style', '')} | 题材 {', '.join(profile.get('concept_tags', [])[:4]) or profile.get('sector', '')} | "
                f"情绪 {profile.get('last_sentiment', '')} | 观察 {profile.get('observation_count', 0)} 次"
            )
    else:
        lines.append("- 无数据")
    lines.append("")
    lines.append("## 题材画像")
    theme_profiles = memory.get("theme_profiles", {})
    if theme_profiles:
        for theme, profile in list(theme_profiles.items())[:10]:
            lines.append(
                f"- {theme} | 相关股票 {', '.join(profile.get('related_stocks', [])[:4]) or '无'} | "
                f"平均热度 {profile.get('avg_heat_score', '-') } | 观察 {profile.get('observation_count', 0)} 次"
            )
    else:
        lines.append("- 无数据")
    return "\n".join(lines)


def render_concept_blocks(payload: dict) -> str:
    lines = [
        f"# 概念板块 {payload.get('stock_name', '')} ({payload.get('stock_code', '')})",
        "",
        f"- 数据源: {payload.get('provider', '')}",
        f"- 概念标签: {', '.join(payload.get('concept_tags', [])) or '无'}",
        "",
        "## 行业",
    ]
    for item in payload.get("industry", []):
        lines.append(f"- {item['name']} | {item.get('change_pct', 0)}% | {item.get('desc', '')}")
    if not payload.get("industry"):
        lines.append("- 无数据")
    lines.append("")
    lines.append("## 概念")
    for item in payload.get("concept", []):
        lines.append(f"- {item['name']} | {item.get('change_pct', 0)}% | {item.get('desc', '')}")
    if not payload.get("concept"):
        lines.append("- 无数据")
    lines.append("")
    lines.append("## 地域")
    for item in payload.get("region", []):
        lines.append(f"- {item['name']} | {item.get('change_pct', 0)}% | {item.get('desc', '')}")
    if not payload.get("region"):
        lines.append("- 无数据")
    return "\n".join(lines)


def render_reports(payload: dict) -> str:
    lines = [f"# 研报 {payload['stock_code']}", "", f"- 数据源: {payload.get('provider', '')}", ""]
    for item in payload.get("items", []):
        lines.append(
            f"- {str(item.get('publishDate', ''))[:10]} | {item.get('orgSName', '')} | "
            f"{item.get('emRatingName', '')} | {item.get('title', '')}"
        )
    if not payload.get("items"):
        lines.append("- 无数据")
    return "\n".join(lines)


def render_dragon_tiger(payload: dict) -> str:
    lines = [
        f"# 龙虎榜 {payload['stock_code']}",
        "",
        f"- 数据源: {payload.get('provider', '')}",
        f"- 回看天数: {payload.get('look_back', 0)}",
        f"- 上榜次数: {len(payload.get('records', []))}",
        f"- 机构净额(万): {payload.get('institution', {}).get('net_amt', 0)}",
        "",
        "## Records",
    ]
    for item in payload.get("records", []):
        lines.append(f"- {item['date']} | {item['reason']} | 净买 {item['net_buy']} 万 | 换手 {item['turnover']}%")
    if not payload.get("records"):
        lines.append("- 无数据")
    lines.append("")
    lines.append("## Buy Seats")
    for item in payload.get("seats", {}).get("buy", []):
        lines.append(f"- {item['name']} | 买 {item['buy_amt']} 万 | 卖 {item['sell_amt']} 万 | 净 {item['net']} 万")
    lines.append("")
    lines.append("## Sell Seats")
    for item in payload.get("seats", {}).get("sell", []):
        lines.append(f"- {item['name']} | 买 {item['buy_amt']} 万 | 卖 {item['sell_amt']} 万 | 净 {item['net']} 万")
    return "\n".join(lines)


def render_daily_dragon_tiger(payload: dict) -> str:
    lines = [
        f"# 全市场龙虎榜 {payload.get('date', '')}",
        "",
        f"- 数据源: {payload.get('provider', '')}",
        f"- 记录数: {payload.get('total_records', 0)}",
        "",
    ]
    for item in payload.get("stocks", [])[:20]:
        lines.append(
            f"- {item['code']} {item['name']} | 净买 {item['net_buy_wan']} 万 | "
            f"涨跌 {item['change_pct']}% | {item['reason']}"
        )
    if not payload.get("stocks"):
        lines.append("- 无数据")
    return "\n".join(lines)


def render_rows(payload: dict, title: str, columns: list[str]) -> str:
    lines = [f"# {title} {payload['stock_code']}", "", f"- 数据源: {payload.get('provider', '')}", ""]
    for item in payload.get("items", []):
        lines.append("- " + " | ".join(f"{column}={item.get(column, '')}" for column in columns))
    if not payload.get("items"):
        lines.append("- 无数据")
    return "\n".join(lines)


def render_lockup(payload: dict) -> str:
    lines = [
        f"# 限售解禁 {payload['stock_code']}",
        "",
        f"- 数据源: {payload.get('provider', '')}",
        f"- 观察日期: {payload.get('trade_date', '')}",
        f"- 未来窗口: {payload.get('forward_days', 0)} 天",
        "",
        "## History",
    ]
    for item in payload.get("history", []):
        lines.append(f"- {item['date']} | {item['type']} | shares={item['shares']} | ratio={item['ratio']}")
    if not payload.get("history"):
        lines.append("- 无历史数据")
    lines.append("")
    lines.append("## Upcoming")
    for item in payload.get("upcoming", []):
        lines.append(f"- {item['date']} | {item['type']} | shares={item['shares']} | ratio={item['ratio']}")
    if not payload.get("upcoming"):
        lines.append("- 未来窗口内无待解禁")
    return "\n".join(lines)


def render_northbound(payload: dict) -> str:
    latest = payload.get("latest") or {}
    lines = [
        "# 北向资金",
        "",
        f"- 数据源: {payload.get('provider', '')}",
        f"- 日期: {payload.get('date', '')}",
        f"- 最新: {latest}",
        "",
        "## History",
    ]
    for item in payload.get("history", []):
        lines.append(f"- {item['date']} | 沪股通 {item['hgt']} 亿 | 深股通 {item['sgt']} 亿")
    if not payload.get("history"):
        lines.append("- 无缓存历史")
    return "\n".join(lines)


def render_stock_info(payload: dict) -> str:
    return (
        f"# 个股信息 {payload.get('name', '')} ({payload.get('code', '')})\n\n"
        f"- 数据源: {payload.get('provider', '')}\n"
        f"- 行业: {payload.get('industry', '')}\n"
        f"- 价格: {payload.get('price', 0)}\n"
        f"- 总股本: {payload.get('total_shares', 0)}\n"
        f"- 流通股: {payload.get('float_shares', 0)}\n"
        f"- 总市值: {payload.get('mcap', 0)}\n"
        f"- 流通市值: {payload.get('float_mcap', 0)}\n"
        f"- 上市日期: {payload.get('list_date', '')}"
    )


def render_quotes(payload: dict) -> str:
    lines = ["# 实时行情", "", f"- 数据源: {payload.get('provider', '')}", f"- 类型: {payload.get('kind', '')}"]
    if payload.get("available") is False:
        lines.append(f"- 错误: {payload.get('error', '')}")
        return "\n".join(lines)
    lines.append("")
    for item in payload.get("items", []):
        lines.append(
            f"- {item.get('symbol', '')} {item.get('name', '')} | 现价 {item.get('price', '')} | "
            f"涨跌 {item.get('change_amt', '')} / {item.get('change_pct', '')}% | "
            f"PE {item.get('pe_ttm', '')} | PB {item.get('pb', '')}"
        )
    if not payload.get("items"):
        lines.append("- 无数据")
    return "\n".join(lines)


def render_valuation(payload: dict) -> str:
    lines = [
        f"# 估值 {payload.get('name', '')} ({payload.get('stock_code', '')})",
        "",
        f"- 数据源: {payload.get('provider', '')}",
        f"- 可用: {'是' if payload.get('available') else '否'}",
        f"- 时间: {payload.get('generated_at', '')}",
    ]
    if payload.get("degraded"):
        lines.append(f"- 降级原因: {', '.join(payload.get('degraded_reasons', []))}")
    for item in payload.get("errors", []):
        lines.append(f"- 错误: {item}")
    lines.extend(
        [
            f"- 现价: {payload.get('price', '')}",
            f"- 市值(亿): {payload.get('mcap_yi', '')}",
            f"- PE(TTM): {payload.get('pe_ttm', '')}",
            f"- PB: {payload.get('pb', '')}",
            f"- 一致预期EPS(当年/次年): {payload.get('eps_cur', '')} / {payload.get('eps_next', '')}",
            f"- 前向PE: {payload.get('pe_fwd', '')}",
            f"- CAGR: {payload.get('cagr_pct', '')}%",
            f"- PEG: {payload.get('peg', '')}",
            f"- PE消化年数: {payload.get('digest_years', '')}",
            f"- 覆盖机构数: {payload.get('analyst_count', 0)}",
        ]
    )
    return "\n".join(lines)


def render_compare(payload: dict) -> str:
    lines = ["# 批量估值对比", "", f"- 数据源: {payload.get('provider', '')}", ""]
    for item in payload.get("items", []):
        lines.append(
            f"- {item.get('name', '')}({item.get('stock_code', '')}) | "
            f"PE_fwd {item.get('pe_fwd', '')}x | PEG {item.get('peg', '')} | "
            f"消化 {item.get('digest_years', '')} 年 | 覆盖 {item.get('analyst_count', 0)} 家"
        )
    if not payload.get("items"):
        lines.append("- 无数据")
    return "\n".join(lines)


def render_quick_research(payload: dict) -> str:
    coverage = payload.get("coverage", {})
    valuation = payload.get("valuation", {})
    strategy = payload.get("strategy_system", {})
    market_cycle = strategy.get("market_cycle", {})
    trade_setup = strategy.get("trade_setup", {})
    concepts = payload.get("concepts", {})
    fund_flow = payload.get("fund_flow", {})
    dragon_tiger = payload.get("dragon_tiger", {})
    lockup = payload.get("lockup", {})
    community = payload.get("community", {})
    time_context = payload.get("time_context", {})
    lines = [
        f"# 新标的快速调研 {payload.get('stock_code', '')}",
        "",
        f"- 日期: {payload.get('date', '')}",
        f"- 数据源: {payload.get('provider', '')}",
        f"- 时间环境: {time_context.get('session', '-')}",
        f"- 结论基准日: {time_context.get('analysis_date', '-')}",
        f"- 可用: {'是' if payload.get('available') else '否'}",
        f"- 时间: {payload.get('generated_at', '')}",
    ]
    if payload.get("degraded"):
        lines.append(f"- 降级原因: {', '.join(payload.get('degraded_reasons', []))}")
    for item in payload.get("errors", []):
        lines.append(f"- 错误: {item}")
    lines.extend(
        [
            f"- 机构覆盖: {'有' if coverage.get('has_consensus') else '无'} / {coverage.get('analyst_count', 0)} 家",
            f"- 前向PE / PEG: {valuation.get('pe_fwd', '')} / {valuation.get('peg', '')}",
            f"- 方法论阶段 / 风格: {market_cycle.get('stage', '')} / {trade_setup.get('style', '')}",
            f"- 介入方式 / 建议仓位: {trade_setup.get('setup', '')} / {round(trade_setup.get('preferred_position', 0) * 100)}%",
            f"- 社区情绪 / 大V观点数: {community.get('mood', '未知')} / {len(community.get('vip_views', []))}",
            f"- 概念标签: {', '.join(concepts.get('concept_tags', [])[:8]) or '无'}",
            f"- 资金流主力累计: {fund_flow.get('total_main_net', 0)}",
            f"- 龙虎榜次数 / 机构净额: {dragon_tiger.get('record_count', 0)} / {dragon_tiger.get('institution_net_amt', 0)}",
            f"- 解禁历史 / 未来: {lockup.get('history_count', 0)} / {lockup.get('upcoming_count', 0)}",
            f"- 近端研报数: {coverage.get('report_count', 0)}",
        ]
    )
    return "\n".join(lines)


def render_theme_research(payload: dict) -> str:
    lines = [
        "# 主题研报检索",
        "",
        f"- 数据源: {payload.get('provider', '')}",
        f"- 频道: {payload.get('channel', '')}",
        f"- 可用: {'是' if payload.get('available') else '否'}",
        f"- 时间: {payload.get('generated_at', '')}",
    ]
    if payload.get("degraded"):
        lines.append(f"- 降级原因: {', '.join(payload.get('degraded_reasons', []))}")
    if payload.get("available") is False:
        for item in payload.get("errors", []) or [payload.get("error", "")]:
            lines.append(f"- 错误: {item}")
        return "\n".join(lines)
    lines.append(f"- Query数: {len(payload.get('queries', []))}")
    lines.append(f"- 去重研报数: {payload.get('article_count', 0)}")
    lines.append(f"- 涉及标的数: {payload.get('stock_count', 0)}")
    lines.append("")
    lines.append("## Query Hits")
    for item in payload.get("query_hits", []):
        lines.append(f"- {item.get('query', '')}: {item.get('count', 0)} 篇")
    if not payload.get("query_hits"):
        lines.append("- 无数据")
    lines.append("")
    lines.append("## Articles")
    for item in payload.get("articles", [])[:10]:
        extra = item.get("extra") or {}
        organization = extra.get("organization", "") if isinstance(extra, dict) else ""
        lines.append(f"- {str(item.get('publish_date', ''))[:10]} | {organization} | {item.get('title', '')}")
    if not payload.get("articles"):
        lines.append("- 无数据")
    lines.append("")
    lines.append("## Supplements")
    for item in payload.get("supplements", []):
        lines.append(f"- {item.get('stock_code', '')}: {len(item.get('reports', []))} 篇东财研报")
    if not payload.get("supplements"):
        lines.append("- 无补充研报")
    return "\n".join(lines)


def render_price_bars(payload: dict) -> str:
    lines = [f"# K线 {payload.get('stock_code', '')}", "", f"- 数据源: {payload.get('provider', '')}", f"- 周期: {payload.get('frequency', '')}"]
    if payload.get("available") is False:
        lines.append(f"- 错误: {payload.get('error', '')}")
        return "\n".join(lines)
    lines.append("")
    for item in payload.get("items", [])[:20]:
        lines.append(
            f"- {item.get('datetime', '')} | O {item.get('open', '')} H {item.get('high', '')} "
            f"L {item.get('low', '')} C {item.get('close', '')} | V {item.get('vol', '')}"
        )
    if not payload.get("items"):
        lines.append("- 无数据")
    return "\n".join(lines)


def render_order_book(payload: dict) -> str:
    lines = [f"# 五档盘口 {payload.get('code', '')}", "", f"- 数据源: {payload.get('provider', '')}"]
    if payload.get("available") is False:
        lines.append(f"- 错误: {payload.get('error', '')}")
        return "\n".join(lines)
    lines.extend(
        [
            f"- 现价: {payload.get('price', '')}",
            f"- 昨收: {payload.get('last_close', '')}",
            f"- 开盘: {payload.get('open', '')}",
            f"- 最高/最低: {payload.get('high', '')} / {payload.get('low', '')}",
            f"- 时间: {payload.get('servertime', '')}",
            "",
            "## 买盘",
        ]
    )
    for item in payload.get("bids", []):
        lines.append(f"- 买{item['level']} {item['price']} / {item['volume']}")
    lines.append("")
    lines.append("## 卖盘")
    for item in payload.get("asks", []):
        lines.append(f"- 卖{item['level']} {item['price']} / {item['volume']}")
    return "\n".join(lines)


def render_transactions(payload: dict) -> str:
    lines = [f"# 逐笔成交 {payload.get('stock_code', '')}", "", f"- 数据源: {payload.get('provider', '')}"]
    if payload.get("available") is False:
        lines.append(f"- 错误: {payload.get('error', '')}")
        return "\n".join(lines)
    lines.append("")
    for item in payload.get("items", [])[:50]:
        lines.append(
            f"- {item.get('time', '')} | 价 {item.get('price', '')} | 量 {item.get('vol', '')} | "
            f"笔数 {item.get('num', '')} | 方向 {item.get('buyorsell', '')}"
        )
    if not payload.get("items"):
        lines.append("- 无数据")
    return "\n".join(lines)


def render_financial_snapshot(payload: dict) -> str:
    lines = [f"# 季报快照 {payload.get('stock_code', '')}", "", f"- 数据源: {payload.get('provider', '')}"]
    if payload.get("available") is False:
        lines.append(f"- 错误: {payload.get('error', '')}")
        return "\n".join(lines)
    data = payload.get("data", {})
    lines.extend(
        [
            f"- 标的: {data.get('name', '')} ({data.get('code', '')})",
            f"- EPS: {data.get('eps', '')}",
            f"- ROE: {data.get('roe', '')}",
            f"- 每股净资产: {data.get('bvps', data.get('meigujingzichan', ''))}",
            f"- 净利润: {data.get('profit', '')}",
            f"- 主营收入: {data.get('income', '')}",
            f"- 总股本: {data.get('zongguben', '')}",
            f"- 流通股本: {data.get('liutongguben', '')}",
        ]
    )
    return "\n".join(lines)


def render_f10_profile(payload: dict) -> str:
    lines = [f"# F10 {payload.get('stock_code', '')}", "", f"- 数据源: {payload.get('provider', '')}"]
    if payload.get("category"):
        lines.append(f"- 分类: {payload.get('category', '')}")
    if payload.get("available") is False:
        lines.append(f"- 错误: {payload.get('error', '')}")
        return "\n".join(lines)
    lines.append("")
    for category, content in payload.get("items", {}).items():
        lines.append(f"## {category}")
        lines.append(content or "(空)")
        lines.append("")
    if not payload.get("items"):
        lines.append("- 无数据")
    return "\n".join(lines).rstrip()


def render_consensus_eps(payload: dict) -> str:
    lines = [f"# 一致预期EPS {payload['stock_code']}", "", f"- 数据源: {payload.get('provider', '')}", ""]
    for item in payload.get("items", []):
        lines.append(
            f"- {item['year']} | 机构数 {item['institution_count']} | "
            f"最小 {item['min']} | 均值 {item['mean']} | 最大 {item['max']} | 行业均值 {item['industry_avg']}"
        )
    if not payload.get("items"):
        lines.append("- 无数据")
    return "\n".join(lines)


def render_iwencai(payload: dict, title: str) -> str:
    lines = [f"# {title}", "", f"- 数据源: {payload.get('provider', '')}"]
    if payload.get("query"):
        lines.append(f"- 查询: {payload['query']}")
    if payload.get("channel"):
        lines.append(f"- 频道: {payload['channel']}")
    if payload.get("available") is False:
        lines.append(f"- 错误: {payload.get('error', '')}")
        return "\n".join(lines)
    lines.append("")
    for item in payload.get("items", []):
        lines.append("- " + json.dumps(item, ensure_ascii=False))
    if not payload.get("items"):
        lines.append("- 无数据")
    return "\n".join(lines)
