"""Time helpers with explicit Asia/Shanghai defaults."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo


SHANGHAI_TZ = ZoneInfo("Asia/Shanghai")


def shanghai_now() -> datetime:
    return datetime.now(SHANGHAI_TZ)


def shanghai_today_str() -> str:
    return shanghai_now().strftime("%Y-%m-%d")


def shanghai_timestamp_iso() -> str:
    return shanghai_now().isoformat(timespec="seconds")
