"""Integrated market analysis."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Optional

from src.config import Config
from src.core.methodology import MethodologyEngine
from src.providers import MarketDataProvider, build_provider


@dataclass(frozen=True)
class MarketMode:
    """Market liquidity mode."""

    mode: str
    total_volume: float
    description: str
    key_focus: str

    def to_dict(self) -> dict:
        return asdict(self)


class IntegratedAnalyzer:
    """Combines market, sentiment, liquidity, and mandatory risk signals."""

    def __init__(self, config: Optional[Config] = None, provider: Optional[MarketDataProvider] = None):
        self.config = config or Config.load()
        self.provider = provider or build_provider(self.config)
        self.methodology = MethodologyEngine(self.config)

    def detect_market_mode(self, total_volume: float) -> MarketMode:
        if total_volume >= 20000:
            return MarketMode("超级天量", total_volume, "2万亿以上，追高风险迅速放大", "只做有承接的中军龙头")
        if total_volume >= 15000:
            return MarketMode("天量", total_volume, "1.5万亿以上，分歧和换手都很高", "重视筹码结构和次日承接")
        if total_volume <= 8000:
            return MarketMode("缩量", total_volume, "8000亿以下，题材扩散能力偏弱", "聚焦抱团核心和低位防守")
        return MarketMode("正常", total_volume, "流动性正常，可执行标准交易流程", "精选强于指数的个股")

    def analyze_news_policy(self, keywords: list[str] | None = None, date: str | None = None) -> dict:
        snapshot = self.provider.get_market_snapshot(date)
        highlights = [item for item in snapshot.policy_highlights if not keywords or any(key in item for key in keywords)]
        score = round(snapshot.policy_score, 2)
        bias = "偏多" if score >= 3.5 else "中性" if score >= 2.5 else "偏空"
        return {
            "score": score,
            "bias": bias,
            "highlights": highlights or list(snapshot.policy_highlights),
        }

    def analyze_sentiment(self, date: str | None = None) -> dict:
        snapshot = self.provider.get_market_snapshot(date)
        market_cycle = self.methodology.assess_market_cycle(snapshot)
        score = round(snapshot.sentiment_score, 2)
        return {
            "score": score,
            "tone": market_cycle.stage,
            "environment": market_cycle.environment,
            "action_bias": market_cycle.action_bias,
            "position_upper_bound": market_cycle.position_upper_bound,
            "leaders": list(snapshot.leaders),
            "overseas_signal": snapshot.overseas_signal,
        }

    def analyze_liquidity_pattern(self, date: str | None = None) -> dict:
        snapshot = self.provider.get_market_snapshot(date)
        mode = self.detect_market_mode(snapshot.total_volume_billion)
        market_cycle = self.methodology.assess_market_cycle(snapshot)
        breadth = round(snapshot.advancers / max(snapshot.decliners, 1), 2)
        return {
            "market_mode": mode.to_dict(),
            "breadth": breadth,
            "advancers": snapshot.advancers,
            "decliners": snapshot.decliners,
            "market_cycle": market_cycle.to_dict(),
            "hot_sectors": list(snapshot.hot_sectors),
            "cold_sectors": list(snapshot.cold_sectors),
        }

    def assess_market_cycle(self, date: str | None = None) -> dict:
        snapshot = self.provider.get_market_snapshot(date)
        return self.methodology.assess_market_cycle(snapshot).to_dict()

    def evaluate_trade_setup(self, stock_code: str, date: str | None = None) -> dict:
        stock = self.provider.get_stock_snapshot(stock_code)
        snapshot = self.provider.get_market_snapshot(date)
        return self.methodology.evaluate_stock(stock, snapshot).to_dict()

    def build_trade_discipline(self, stock_code: str, date: str | None = None) -> dict:
        stock = self.provider.get_stock_snapshot(stock_code)
        snapshot = self.provider.get_market_snapshot(date)
        return self.methodology.build_discipline(stock, snapshot)

    def build_market_playbook(self, date: str | None = None) -> dict:
        snapshot = self.provider.get_market_snapshot(date)
        return self.methodology.build_market_playbook(snapshot)

    def build_stock_playbook(self, stock_code: str, date: str | None = None) -> dict:
        stock = self.provider.get_stock_snapshot(stock_code)
        snapshot = self.provider.get_market_snapshot(date)
        return self.methodology.build_stock_playbook(stock, snapshot)

    def check_mandatory_risks(self, stock_code: str) -> dict:
        stock = self.provider.get_stock_snapshot(stock_code)
        risks = []
        if stock.under_investigation:
            risks.append("立案调查")
        if stock.delisting_risk:
            risks.append("退市预警")
        if stock.reduction_plan:
            risks.append("大比例减持")
        if stock.earnings_shock:
            risks.append("业绩巨亏")
        return {
            "stock_code": stock_code,
            "risks": risks,
            "has_red_flags": bool(risks),
        }

    def analyze_tianliang_adaptation(self, stock_code: str, date: str | None = None) -> dict:
        stock = self.provider.get_stock_snapshot(stock_code)
        snapshot = self.provider.get_market_snapshot(date)
        market_mode = self.detect_market_mode(snapshot.total_volume_billion)
        if market_mode.mode in {"超级天量", "天量"}:
            focus = "看5/10/20日均线承接，不追高位小票"
        else:
            focus = "标准均线和支撑阻力位即可"
        return {
            "market_mode": market_mode.mode,
            "focus": focus,
            "ma20": stock.ma20,
            "support": stock.support,
            "resistance": stock.resistance,
        }

    def analyze_stock(self, stock_code: str, date: str | None = None) -> dict:
        stock = self.provider.get_stock_snapshot(stock_code)
        market = self.provider.get_market_snapshot(date)
        news = self.analyze_news_policy(date=date)
        sentiment = self.analyze_sentiment(date=date)
        liquidity = self.analyze_liquidity_pattern(date=date)
        strategy_profile = self.methodology.evaluate_stock(stock, market)
        discipline = self.methodology.build_discipline(stock, market)
        return {
            "stock": stock.to_dict(),
            "market": market.to_dict(),
            "news": news,
            "sentiment": sentiment,
            "liquidity": liquidity,
            "methodology": strategy_profile.to_dict(),
            "discipline": discipline,
            "technical": {
                "above_ma20": stock.above_ma20,
                "price_position": stock.price_position,
                "volume_pattern": stock.volume_pattern,
                "risk_reward_ratio": stock.risk_reward_ratio,
            },
        }
