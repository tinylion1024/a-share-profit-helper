"""Intent-aware time context and evidence window selection."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date as date_cls, datetime, timedelta
from typing import Any

from src.utils.time import shanghai_now


def _parse_date(value: str) -> date_cls:
    return datetime.strptime(value, "%Y-%m-%d").date()


def _previous_trading_day(value: date_cls) -> date_cls:
    cursor = value - timedelta(days=1)
    while cursor.weekday() >= 5:
        cursor -= timedelta(days=1)
    return cursor


def _is_trading_day(value: date_cls) -> bool:
    return value.weekday() < 5


def _detect_market_session(now: datetime, requested_date: str | None) -> str:
    if requested_date and requested_date != now.strftime("%Y-%m-%d"):
        return "historical"
    if not _is_trading_day(now.date()):
        return "weekend"

    minutes = now.hour * 60 + now.minute
    if minutes < 9 * 60 + 15:
        return "pre-market"
    if minutes < 11 * 60 + 30:
        return "intraday-am"
    if minutes < 13 * 60:
        return "midday-break"
    if minutes < 15 * 60:
        return "intraday-pm"
    return "post-market"


@dataclass(frozen=True)
class IntentTimeContext:
    """Current environment plus selected evidence windows."""

    intent: str
    session: str
    current_date: str
    requested_date: str | None
    analysis_date: str
    anchor_trade_date: str
    is_trading_day: bool
    uses_intraday_data: bool
    evidence_plan: dict[str, dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_intent_time_context(
    intent: str,
    requested_date: str | None = None,
    *,
    horizon: str | None = None,
    now: datetime | None = None,
) -> IntentTimeContext:
    current = now or shanghai_now()
    current_date = current.strftime("%Y-%m-%d")
    session = _detect_market_session(current, requested_date)
    if requested_date:
        anchor_trade_date = requested_date
    elif session in {"pre-market", "weekend"}:
        anchor_trade_date = _previous_trading_day(current.date()).strftime("%Y-%m-%d")
    else:
        anchor_trade_date = current_date

    short_horizon = horizon in {None, "", "短线", "超短"}
    uses_intraday_data = requested_date is None and session in {"intraday-am", "intraday-pm", "midday-break", "post-market"}

    if intent in {"market-cycle", "pre-market", "post-market"}:
        evidence_plan = {
            "market_snapshot": {
                "mode": "realtime" if uses_intraday_data else "last_close",
                "date": anchor_trade_date,
                "reason": "市场环境判断优先使用最近完整交易日，盘中/盘后追加实时行情。",
            },
            "telegraph": {
                "window": "overnight_to_now" if session == "pre-market" else "today",
                "page_size": 8 if session == "pre-market" else 12,
                "reason": "盘前看隔夜消息，盘中盘后看当日消息流。",
            },
            "community": {
                "window": "recent_1d" if session != "weekend" else "recent_3d",
                "page_size": 10 if session == "pre-market" else 14,
                "reason": "情绪周期判断更依赖最近 1 个交易日的社区热度。",
            },
            "hot_stocks": {
                "trade_date": current_date if uses_intraday_data else anchor_trade_date,
                "page_size": 6,
                "reason": "主线辨识度优先使用当日或最近交易日强势股。",
            },
            "northbound": {
                "history_days": 5,
                "reason": "市场环境更看近 5 个交易日北向节奏。",
            },
        }
    elif intent in {"diagnose", "playbook", "risk"}:
        evidence_plan = {
            "market_snapshot": {
                "mode": "realtime" if uses_intraday_data else "last_close",
                "date": anchor_trade_date,
                "reason": "单票结论先看当前环境，再看个股结构。",
            },
            "community": {
                "window": "recent_1d" if short_horizon else "recent_3d",
                "page_size": 18 if short_horizon else 10,
                "reason": "短线诊断更看最近 1 个交易日的股民情绪和大V观点。",
            },
            "news": {
                "window": "recent_3d" if short_horizon else "recent_7d",
                "page_size": 3 if short_horizon else 5,
                "reason": "短线更看近 3 日催化，偏波段可放宽到 7 日。",
            },
            "announcements": {
                "window": "recent_7d",
                "page_size": 3,
                "reason": "公告以最近 7 日为主，避免旧信息干扰当前判断。",
            },
        }
    else:
        evidence_plan = {
            "valuation": {
                "mode": "realtime_quote+consensus",
                "reason": "估值需要当前价格和最新一致预期。",
            },
            "community": {
                "window": "recent_1d" if session in {"pre-market", "intraday-am", "midday-break", "intraday-pm", "post-market"} else "recent_3d",
                "page_size": 20 if short_horizon else 12,
                "reason": "快速调研默认优先最近情绪和观点变化。",
            },
            "reports": {
                "window": "recent_30d",
                "page_size": 3 if uses_intraday_data else 5,
                "reason": "近 30 日研报足够覆盖主流卖方观点。",
            },
            "news": {
                "window": "recent_3d",
                "page_size": 4,
                "reason": "快速调研需要近 3 日催化与扰动。",
            },
            "announcements": {
                "window": "recent_7d",
                "page_size": 4,
                "reason": "公告窗口用最近 7 日识别新增事件。",
            },
            "fund_flow": {
                "window": "recent_120d",
                "limit": 5,
                "reason": "保留近 120 日主力资金趋势，摘要只看最近 5 条。",
            },
            "dragon_tiger": {
                "trade_date": anchor_trade_date,
                "look_back": 30,
                "reason": "龙虎榜回看 30 天足够识别是否反复上榜。",
            },
            "lockup": {
                "trade_date": anchor_trade_date,
                "forward_days": 90,
                "reason": "未来 90 日解禁对中短线影响最大。",
            },
            "margin": {
                "window": "recent_3_sessions",
                "page_size": 3,
                "reason": "两融默认只看最近 3 个交易日变化。",
            },
            "holders": {
                "window": "recent_3_reports",
                "page_size": 3,
                "reason": "股东户数按最近 3 次披露对比即可。",
            },
        }

    return IntentTimeContext(
        intent=intent,
        session=session,
        current_date=current_date,
        requested_date=requested_date,
        analysis_date=anchor_trade_date,
        anchor_trade_date=anchor_trade_date,
        is_trading_day=_is_trading_day(current.date()),
        uses_intraday_data=uses_intraday_data,
        evidence_plan=evidence_plan,
    )
