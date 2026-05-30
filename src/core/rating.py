"""Rating system for A-share stock selection."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Optional

from src.config import Config
from src.core.analyzer import IntegratedAnalyzer
from src.core.risk_checker import RiskChecker
from src.providers import MarketDataProvider, build_provider


@dataclass(frozen=True)
class FourDimensionRating:
    """The four-dimensional rating used by the skill."""

    opportunity: int
    safety: int
    certainty: int
    comfort: int

    @property
    def total_score(self) -> float:
        return round(
            self.opportunity * 0.30
            + self.safety * 0.25
            + self.certainty * 0.25
            + self.comfort * 0.20,
            2,
        )

    @property
    def is_recommended(self) -> bool:
        return self.safety >= 3 and self.opportunity >= 3 and self.certainty >= 3

    @property
    def level(self) -> str:
        score = self.total_score
        if score >= 4.5:
            return "⭐⭐⭐⭐⭐ 立即买"
        if score >= 3.5:
            return "⭐⭐⭐⭐ 可以买"
        if score >= 2.5:
            return "⭐⭐⭐ 观望"
        return "⭐⭐ 回避"

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["total_score"] = self.total_score
        payload["is_recommended"] = self.is_recommended
        payload["level"] = self.level
        return payload


@dataclass(frozen=True)
class RiskLevel:
    """Compact rating labels."""

    risk: str
    opportunity: str
    certainty: str
    comfort_star: int


class RatingSystem:
    """Map market and stock signals to the four-dimensional rating."""

    def __init__(self, config: Optional[Config] = None, provider: Optional[MarketDataProvider] = None):
        self.config = config or Config.load()
        self.provider = provider or build_provider(self.config)
        self.analyzer = IntegratedAnalyzer(self.config, self.provider)
        self.risk_checker = RiskChecker(self.config, self.provider)

    def rate_stock(self, stock_code: str, date: str | None = None) -> FourDimensionRating:
        stock = self.provider.get_stock_snapshot(stock_code)
        market = self.provider.get_market_snapshot(date)
        risk = self.risk_checker.check(stock_code, date)
        strategy_profile = self.analyzer.methodology.evaluate_stock(stock, market)
        market_cycle = self.analyzer.methodology.assess_market_cycle(market)

        opportunity = 3
        if stock.momentum_score >= 4:
            opportunity += 1
        if stock.q1_growth >= 15:
            opportunity += 1
        if stock.catalyst == "":
            opportunity -= 1
        if stock.q1_growth < 0:
            opportunity -= 1
        if strategy_profile.style in {"主线龙头", "趋势中军"}:
            opportunity += 1
        elif strategy_profile.style == "观察股":
            opportunity -= 1

        if risk.risk_level == "R3":
            safety = 2
        elif risk.risk_level == "R2":
            safety = 3
        else:
            safety = 4 if stock.turnover_million >= 200 else 3
        if stock.turnover_million >= 1000 and safety < 5:
            safety += 1

        certainty = round((market.policy_score + market.trend_score) / 2)
        if stock.catalyst:
            certainty += 1
        if risk.warnings:
            certainty -= 1
        if market_cycle.stage == "退潮期/补跌期":
            certainty -= 1
        if strategy_profile.methodology_score >= 4:
            certainty += 1

        comfort = self.calculate_comfort(stock.price_position, stock.volume_pattern)
        if stock.risk_reward_ratio >= 2.5 and comfort < 5:
            comfort += 1
        if strategy_profile.setup == "分歧低吸" and comfort < 5:
            comfort += 1
        if strategy_profile.setup == "只宜确认后参与":
            comfort -= 1

        return FourDimensionRating(
            opportunity=max(1, min(5, opportunity)),
            safety=max(1, min(5, safety)),
            certainty=max(1, min(5, certainty)),
            comfort=max(1, min(5, comfort)),
        )

    def calculate_comfort(self, price_position: str, volume_pattern: str) -> int:
        score = 3
        if "缩量回踩" in price_position or "稳步放量" in volume_pattern:
            score = 5
        elif "追涨" in price_position:
            score = 2
        elif "缩量" in volume_pattern:
            score = 4
        return score

    def check_r3_redline(self, safety_star: int) -> bool:
        return safety_star < 3

    def check_r3红线(self, safety_star: int) -> bool:
        return self.check_r3_redline(safety_star)
