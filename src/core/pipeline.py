"""Analysis workflow orchestrator."""

from __future__ import annotations

from typing import Callable, Optional

from src.config import Config
from src.core.analyzer import IntegratedAnalyzer
from src.core.rating import RatingSystem
from src.core.risk_checker import RiskChecker
from src.providers import MarketDataProvider, build_provider


class AnalysisPipeline:
    """Run the standard workflow for diagnosis-style prompts."""

    def __init__(self, config: Optional[Config] = None, provider: Optional[MarketDataProvider] = None):
        self.config = config or Config.load()
        self.provider = provider or build_provider(self.config)
        self.analyzer = IntegratedAnalyzer(self.config, self.provider)
        self.rating_system = RatingSystem(self.config, self.provider)
        self.risk_checker = RiskChecker(self.config, self.provider)
        self._steps: list[tuple[str, Callable]] = []

    def add_step(self, name: str, func: Callable) -> "AnalysisPipeline":
        self._steps.append((name, func))
        return self

    def run(self, stock_code: str, scenario: str, **kwargs) -> dict:
        context = {"stock_code": stock_code, "scenario": scenario, **kwargs}
        for name, func in self._steps:
            context[name] = func(context)
        return context

    def run_standard_flow(
        self,
        stock_code: str,
        scenario: str,
        horizon: str = "短线",
        risk_preference: str = "平衡型",
        date: str | None = None,
    ) -> dict:
        context = {
            "stock_code": stock_code,
            "scenario": scenario,
            "horizon": horizon,
            "risk_preference": risk_preference,
            "date": date,
        }
        context["needs_clarified"] = self._clarify_needs(context)
        context["market_3d"] = self._analyze_market_3d(context)
        context["risk"] = self.risk_checker.check(stock_code, date).to_dict()
        context["rating_4d"] = self._rate_stock_4d(context)
        context["conclusion"] = self._generate_conclusion(context)
        return context

    def _clarify_needs(self, context: dict) -> dict:
        return {
            "scenario": context["scenario"],
            "horizon": context["horizon"],
            "risk_preference": context["risk_preference"],
        }

    def _analyze_market_3d(self, context: dict) -> dict:
        stock_code = context["stock_code"]
        date = context.get("date")
        analysis = self.analyzer.analyze_stock(stock_code, date)
        return {
            "news": analysis["news"],
            "sentiment": analysis["sentiment"],
            "community": analysis["community"],
            "technical": analysis["technical"],
            "methodology": analysis["methodology"],
            "discipline": analysis["discipline"],
        }

    def _rate_stock_4d(self, context: dict) -> dict:
        rating = self.rating_system.rate_stock(context["stock_code"], context.get("date"))
        return rating.to_dict()

    def _generate_conclusion(self, context: dict) -> dict:
        stock = self.provider.get_stock_snapshot(context["stock_code"])
        rating = context["rating_4d"]
        risk = context["risk"]
        methodology = context["market_3d"]["methodology"]
        discipline = context["market_3d"]["discipline"]
        community = context["market_3d"].get("community", {})
        entry_price = round(min(stock.price, stock.resistance * 0.99), 2)
        stop_loss = round(min(stock.support, entry_price * (1 - self.config.stop_loss_ratio)), 2)
        target_price = round(
            max(stock.resistance, entry_price + (entry_price - stop_loss) * self.config.profit_target_multiplier),
            2,
        )

        position_ratio = min(
            self.config.max_single_position,
            methodology["preferred_position"],
            discipline["preferred_position"],
        )
        if risk["risk_level"] == "R3":
            action = "不买"
            confidence = "低"
            position_ratio = 0.0
        elif methodology["market_stage"] == "退潮期/补跌期":
            action = "观望"
            confidence = "低"
            position_ratio = min(position_ratio, 0.1)
        elif rating["is_recommended"] and methodology["methodology_score"] >= 4:
            action = "可以买"
            confidence = "中高" if rating["total_score"] >= 4 else "中"
        elif rating["is_recommended"]:
            action = "小仓试错"
            confidence = "中"
        else:
            action = "观望"
            confidence = "中"

        community_score = community.get("sentiment_score")
        community_mood = community.get("mood", "未知")
        if isinstance(community_score, (int, float)):
            if community_score <= 2.4 and action == "可以买":
                action = "小仓试错"
                confidence = "中"
                position_ratio = min(position_ratio, 0.15)
            elif community_score >= 3.9 and action in {"观望", "小仓试错"} and rating["is_recommended"]:
                action = "小仓试错" if action == "观望" else action
                confidence = "中高" if confidence == "中" else confidence

        summary = (
            f"{stock.name} 处于{methodology['market_stage']}，更适合{methodology['setup']}，"
            f"定位为{methodology['style']}。四维评级 {rating['level']}，风险等级 {risk['risk_level']}。"
            f"社区情绪 {community_mood}。"
        )
        return {
            "action": action,
            "confidence": confidence,
            "entry_price": entry_price,
            "stop_loss": stop_loss,
            "target_price": target_price,
            "position_ratio": round(position_ratio, 2),
            "market_stage": methodology["market_stage"],
            "style": methodology["style"],
            "setup": methodology["setup"],
            "community_sentiment": {
                "score": community_score,
                "mood": community_mood,
                "vip_view_count": len(community.get("vip_views", [])),
            },
            "discipline": discipline,
            "summary": summary,
        }
