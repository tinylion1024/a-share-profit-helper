"""Domain models for the A-share skill."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class MarketSnapshot:
    """Deterministic market snapshot used by the skill."""

    date: str
    total_volume_billion: float
    policy_score: float
    sentiment_score: float
    trend_score: float
    advancers: int
    decliners: int
    unchanged: int = 0
    hot_sectors: tuple[str, ...] = field(default_factory=tuple)
    cold_sectors: tuple[str, ...] = field(default_factory=tuple)
    policy_highlights: tuple[str, ...] = field(default_factory=tuple)
    leaders: tuple[str, ...] = field(default_factory=tuple)
    overseas_signal: str = "中性"
    data_source: str = ""
    refreshed_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class StockSnapshot:
    """Deterministic stock snapshot used across modules."""

    code: str
    name: str
    sector: str
    price: float
    ma20: float
    boll_position: float
    pe: float
    q1_growth: float
    turnover_million: float
    momentum_score: float
    support: float
    resistance: float
    catalyst: str
    under_investigation: bool = False
    delisting_risk: bool = False
    reduction_plan: bool = False
    earnings_shock: bool = False
    earnings_disclosed: bool = True
    notes: tuple[str, ...] = field(default_factory=tuple)
    data_source: str = ""
    refreshed_at: str = ""

    @property
    def above_ma20(self) -> bool:
        return self.price >= self.ma20

    @property
    def price_position(self) -> str:
        if self.price <= self.ma20 * 1.02:
            return "缩量回踩"
        if self.price >= self.resistance * 0.98:
            return "追涨"
        return "趋势中段"

    @property
    def volume_pattern(self) -> str:
        if self.turnover_million >= 10_000:
            return "行业中军稳步放量"
        if self.turnover_million < 80:
            return "缩量"
        return "正常放量"

    @property
    def risk_reward_ratio(self) -> float:
        reward = max(self.resistance - self.price, 0.1)
        risk = max(self.price - self.support, 0.1)
        return round(reward / risk, 2)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
