"""Pre-market report generation."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Optional

from src.config import Config
from src.core.analyzer import IntegratedAnalyzer
from src.providers import MarketDataProvider, build_provider


@dataclass(frozen=True)
class PreMarketReport:
    """Structured pre-market report."""

    date: str
    overnight_sentiment: str
    policy_highlights: list[str]
    yesterday_leverage: str
    today_script_optimistic: str
    today_script_pessimistic: str
    confidence: str
    market_stage: str
    position_plan: str

    def to_dict(self) -> dict:
        return asdict(self)


class PreMarketAnalyzer:
    """Generate an actionable pre-market report."""

    def __init__(self, config: Optional[Config] = None, provider: Optional[MarketDataProvider] = None):
        self.config = config or Config.load()
        self.provider = provider or build_provider(self.config)
        self.integrated_analyzer = IntegratedAnalyzer(self.config, self.provider)

    def generate_report(self, date: str) -> PreMarketReport:
        market = self.provider.get_market_snapshot(date)
        market_mode = self.integrated_analyzer.detect_market_mode(market.total_volume_billion)
        market_cycle = self.integrated_analyzer.assess_market_cycle(date)
        optimistic, pessimistic = self.generate_dual_script({"market_mode": market_mode.mode, "hot_sectors": market.hot_sectors})
        return PreMarketReport(
            date=market.date,
            overnight_sentiment=f"{market.overseas_signal}，情绪分 {market.sentiment_score}",
            policy_highlights=list(market.policy_highlights),
            yesterday_leverage="、".join(market.leaders),
            today_script_optimistic=optimistic,
            today_script_pessimistic=pessimistic,
            confidence="高" if market_cycle["stage"] == "亢奋期/加速期" else "中" if market_cycle["stage"] == "犹豫期/试探期" else "低",
            market_stage=market_cycle["stage"],
            position_plan=f"{market_cycle['action_bias']}，总仓位上限 {round(market_cycle['position_upper_bound'] * 100)}%",
        )

    def fetch_overnight_data(self) -> dict:
        market = self.provider.get_market_snapshot()
        return {"overseas_signal": market.overseas_signal, "policy_highlights": list(market.policy_highlights)}

    def fetch_sentiment(self) -> dict:
        market = self.provider.get_market_snapshot()
        return {"score": market.sentiment_score, "leaders": list(market.leaders)}

    def analyze_yesterday_leverage(self) -> dict:
        market = self.provider.get_market_snapshot()
        return {"leaders": list(market.leaders), "hot_sectors": list(market.hot_sectors)}

    def generate_dual_script(self, market_data: dict) -> tuple[str, str]:
        optimistic = f"若 {market_data['market_mode']} 延续，优先做 {', '.join(market_data['hot_sectors'][:2])} 的强趋势中军。"
        pessimistic = "若竞价转弱或高位股分歧扩大，降低仓位并等待回踩确认。"
        return optimistic, pessimistic
