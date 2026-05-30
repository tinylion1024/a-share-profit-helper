"""Trading plan generation."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Optional

from src.config import Config
from src.core.analyzer import IntegratedAnalyzer
from src.core.rating import RatingSystem
from src.core.risk_checker import RiskChecker
from src.providers import MarketDataProvider, build_provider


@dataclass(frozen=True)
class TradingPlan:
    """Structured optimistic/pessimistic trading plan."""

    stock_code: str
    stock_name: str
    date: str
    optimistic_triggers: list[str]
    optimistic_entry: float
    optimistic_target: float
    optimistic_stop_loss: float
    optimistic_position: float
    pessimistic_triggers: list[str]
    pessimistic_entry: float
    pessimistic_target: float
    pessimistic_stop_loss: float
    pessimistic_position: float
    risk_control: dict
    break_points: dict
    methodology: dict

    def to_dict(self) -> dict:
        return asdict(self)


class TradingPlanGenerator:
    """Generate executable trading plans with two scenarios."""

    def __init__(self, config: Optional[Config] = None, provider: Optional[MarketDataProvider] = None):
        self.config = config or Config.load()
        self.provider = provider or build_provider(self.config)
        self.analyzer = IntegratedAnalyzer(self.config, self.provider)
        self.rating_system = RatingSystem(self.config, self.provider)
        self.risk_checker = RiskChecker(self.config, self.provider)

    def generate_plan(self, stock_code: str, date: str) -> TradingPlan:
        stock = self.provider.get_stock_snapshot(stock_code)
        market = self.provider.get_market_snapshot(date)
        market_mode = self.analyzer.detect_market_mode(market.total_volume_billion)
        market_cycle = self.analyzer.assess_market_cycle(date)
        trade_setup = self.analyzer.evaluate_trade_setup(stock_code, date)
        discipline = self.analyzer.build_trade_discipline(stock_code, date)
        rating = self.rating_system.rate_stock(stock_code, date)
        risk = self.risk_checker.check(stock_code, date)
        optimistic_triggers, pessimistic_triggers = self.define_triggers(market_mode.mode)
        optimistic_entry = round(min(stock.price, stock.resistance * 0.99), 2)
        optimistic_stop = round(stock.support, 2)
        optimistic_target = round(
            max(stock.resistance, optimistic_entry + (optimistic_entry - optimistic_stop) * self.config.profit_target_multiplier),
            2,
        )
        pessimistic_stop = round(min(stock.support, stock.price * (1 - self.config.stop_loss_ratio)), 2)
        return TradingPlan(
            stock_code=stock.code,
            stock_name=stock.name,
            date=market.date,
            optimistic_triggers=optimistic_triggers + [f"市场阶段 {market_cycle['stage']}", f"参与方式 {trade_setup['setup']}"],
            optimistic_entry=optimistic_entry,
            optimistic_target=optimistic_target,
            optimistic_stop_loss=optimistic_stop,
            optimistic_position=min(
                self.calculate_position(risk.risk_level, "高" if rating.total_score >= 4 else "中"),
                trade_setup["preferred_position"],
            ),
            pessimistic_triggers=pessimistic_triggers + [market_cycle["focus"]],
            pessimistic_entry=round(stock.support, 2),
            pessimistic_target=round(stock.ma20, 2),
            pessimistic_stop_loss=pessimistic_stop,
            pessimistic_position=0.0 if risk.risk_level == "R3" else round(self.config.max_single_position * 0.3, 2),
            risk_control={
                "risk_level": risk.risk_level,
                "red_flags": risk.red_flags,
                "warnings": risk.warnings,
                "discipline": discipline,
            },
            break_points={"support": stock.support, "resistance": stock.resistance},
            methodology={
                "market_cycle": market_cycle,
                "trade_setup": trade_setup,
            },
        )

    def fetch_market_metrics(self, date: str) -> dict:
        market = self.provider.get_market_snapshot(date)
        return {"成交额(亿)": market.total_volume_billion, "涨家": market.advancers, "跌家": market.decliners}

    def fetch_sentiment_after_close(self, date: str) -> dict:
        market = self.provider.get_market_snapshot(date)
        return {"leaders": list(market.leaders), "sentiment_score": market.sentiment_score}

    def define_triggers(self, market_mode: str) -> tuple[list[str], list[str]]:
        optimistic = [f"{market_mode} 延续", "股价站稳关键支撑", "热点板块继续扩散"]
        pessimistic = ["竞价不及预期", "跌破关键支撑", "板块龙头出现放量分歧"]
        return optimistic, pessimistic

    def calculate_position(self, risk_level: str, confidence: str) -> float:
        base_position = self.config.max_single_position
        if risk_level == "R2":
            base_position *= 0.7
        elif risk_level == "R3":
            base_position = 0.0
        if confidence == "高":
            base_position *= 1.0
        elif confidence == "低":
            base_position *= 0.5
        return round(min(base_position, self.config.max_position_ratio), 2)
