"""Post-market review generation."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Optional

from src.config import Config
from src.core.analyzer import IntegratedAnalyzer
from src.providers import MarketDataProvider, build_provider


@dataclass(frozen=True)
class PostMarketReview:
    """Structured post-market review."""

    date: str
    index_summary: dict
    sentiment_monitor: str
    key_stocks: list[str]
    sector_rotation: str
    tomorrow_focus: list[str]
    market_stage: str

    def to_dict(self) -> dict:
        return asdict(self)


class PostMarketAnalyzer:
    """Generate a concise post-market review."""

    def __init__(self, config: Optional[Config] = None, provider: Optional[MarketDataProvider] = None):
        self.config = config or Config.load()
        self.provider = provider or build_provider(self.config)
        self.integrated_analyzer = IntegratedAnalyzer(self.config, self.provider)

    def generate_review(self, date: str) -> PostMarketReview:
        market = self.provider.get_market_snapshot(date)
        liquidity = self.integrated_analyzer.analyze_liquidity_pattern(date)
        market_cycle = self.integrated_analyzer.assess_market_cycle(date)
        return PostMarketReview(
            date=market.date,
            index_summary={
                "成交额(亿)": market.total_volume_billion,
                "涨跌比": f"{market.advancers}:{market.decliners}",
                "平盘数": market.unchanged,
                "流动性模式": liquidity["market_mode"]["mode"],
            },
            sentiment_monitor=f"情绪分 {market.sentiment_score}，海外信号 {market.overseas_signal}",
            key_stocks=list(market.leaders),
            sector_rotation=self.analyze_sector_rotation()["summary"],
            tomorrow_focus=[f"留意 {sector}" for sector in market.hot_sectors[:3]],
            market_stage=market_cycle["stage"],
        )

    def fetch_hard_metrics(self) -> dict:
        market = self.provider.get_market_snapshot()
        return {"成交额(亿)": market.total_volume_billion, "涨家": market.advancers, "跌家": market.decliners, "平家": market.unchanged}

    def fetch_soft_sentiment(self) -> dict:
        market = self.provider.get_market_snapshot()
        return {"sentiment_score": market.sentiment_score, "leaders": list(market.leaders)}

    def analyze_sector_rotation(self) -> dict:
        market = self.provider.get_market_snapshot()
        summary = f"资金更偏向 {', '.join(market.hot_sectors[:2])}，回避 {', '.join(market.cold_sectors[:2])}。"
        return {"summary": summary, "hot_sectors": list(market.hot_sectors), "cold_sectors": list(market.cold_sectors)}

    def detect_divergence(self, market_data: dict) -> dict:
        breadth = market_data.get("advancers", 0) - market_data.get("decliners", 0)
        if breadth < 0:
            return {"has_divergence": True, "summary": "指数可能偏强但个股体验一般。"}
        return {"has_divergence": False, "summary": "指数和个股表现大体同步。"}
