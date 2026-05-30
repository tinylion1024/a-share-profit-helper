"""Methodology-driven trading strategy rules."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from src.config import Config
from src.models import MarketSnapshot, StockSnapshot


@dataclass(frozen=True)
class MarketCycleAssessment:
    """Structured market regime derived from the methodology."""

    stage: str
    environment: str
    breadth_ratio: float
    position_upper_bound: float
    action_bias: str
    focus: str
    warnings: list[str]
    signal_stack: list[str]

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class StockStrategyProfile:
    """Methodology view for a single stock."""

    stock_code: str
    stock_name: str
    market_stage: str
    style: str
    setup: str
    methodology_score: float
    preferred_position: float
    action_bias: str
    tags: list[str]
    reasons: list[str]

    def to_dict(self) -> dict:
        return asdict(self)


class MethodologyEngine:
    """Turn market methodology into reusable trading rules."""

    def __init__(self, config: Config):
        self.config = config

    def assess_market_cycle(self, snapshot: MarketSnapshot) -> MarketCycleAssessment:
        breadth_ratio = round(snapshot.advancers / max(snapshot.decliners, 1), 2)
        warnings: list[str] = []
        signal_stack: list[str] = []

        if snapshot.total_volume_billion >= 15000:
            warnings.append("天量环境下次日承接比追高更重要")
        if snapshot.total_volume_billion <= 8000:
            warnings.append("缩量环境下主线扩散能力偏弱")
        if breadth_ratio < 0.9:
            warnings.append("跌多涨少，亏钱效应仍未明显修复")
        if not snapshot.hot_sectors:
            warnings.append("主线题材不够清晰，避免无差别出手")

        if snapshot.sentiment_score >= 4.2 and breadth_ratio >= 1.1 and snapshot.trend_score >= 3.2:
            stage = "亢奋期/加速期"
            environment = "强势市场"
            position_upper_bound = round(min(self.config.max_position_ratio, 0.7), 2)
            action_bias = "主攻"
            focus = "围绕主线龙头和趋势中军，优先做分歧后的确认与加仓。"
        elif snapshot.sentiment_score <= 2.6 or breadth_ratio <= 0.85 or snapshot.trend_score < 2.6:
            stage = "退潮期/补跌期"
            environment = "弱势市场"
            position_upper_bound = round(min(self.config.max_position_ratio, 0.2), 2)
            action_bias = "防守"
            focus = "收缩战线，只做高确定性反抽，更多时间用于等待。"
        else:
            stage = "犹豫期/试探期"
            environment = "震荡市场" if snapshot.trend_score < 3.2 else "震荡偏强"
            position_upper_bound = round(min(self.config.max_position_ratio, 0.35 if snapshot.trend_score < 3.2 else 0.4), 2)
            action_bias = "试仓"
            focus = "小仓位验证主线强度，确认后再逐步加仓。"

        if snapshot.hot_sectors:
            signal_stack.append(f"主线关注 {' / '.join(snapshot.hot_sectors[:2])}")
        if snapshot.leaders:
            signal_stack.append(f"情绪锚点 {' / '.join(snapshot.leaders[:3])}")
        signal_stack.append(f"涨跌家数比 {snapshot.advancers}:{snapshot.decliners}")

        return MarketCycleAssessment(
            stage=stage,
            environment=environment,
            breadth_ratio=breadth_ratio,
            position_upper_bound=position_upper_bound,
            action_bias=action_bias,
            focus=focus,
            warnings=warnings,
            signal_stack=signal_stack,
        )

    def evaluate_stock(self, stock: StockSnapshot, snapshot: MarketSnapshot) -> StockStrategyProfile:
        market_cycle = self.assess_market_cycle(snapshot)
        leader_score = self._leader_score(stock, snapshot)
        theme_score = self._theme_score(stock, snapshot)
        volume_price_score = self._volume_price_score(stock)
        timing_score = self._timing_score(stock, market_cycle)
        risk_reward_score = self._risk_reward_score(stock)
        methodology_score = round(
            leader_score * 0.28
            + theme_score * 0.22
            + volume_price_score * 0.2
            + timing_score * 0.15
            + risk_reward_score * 0.15,
            2,
        )

        if leader_score >= 4.2 and theme_score >= 4.0:
            style = "主线龙头"
        elif leader_score >= 3.6 and volume_price_score >= 3.6:
            style = "趋势中军"
        elif theme_score >= 3.4 and risk_reward_score >= 3.5:
            style = "补涨候选"
        else:
            style = "观察股"

        if market_cycle.stage == "退潮期/补跌期":
            setup = "等待二次确认"
        elif stock.price_position == "缩量回踩":
            setup = "分歧低吸"
        elif stock.above_ma20 and "放量" in stock.volume_pattern:
            setup = "趋势跟随"
        elif stock.price_position == "追涨":
            setup = "只宜确认后参与"
        else:
            setup = "继续观察"

        preferred_position = self._preferred_position(style, methodology_score, market_cycle)
        if market_cycle.stage == "退潮期/补跌期":
            action_bias = "轻仓或空仓等待"
        elif methodology_score >= 4.1 and style in {"主线龙头", "趋势中军"}:
            action_bias = "可试仓，确认后再加仓"
        elif methodology_score >= 3.4:
            action_bias = "小仓位跟踪"
        else:
            action_bias = "继续观察，不急于出手"

        tags: list[str] = []
        reasons: list[str] = []
        if stock.sector in snapshot.hot_sectors:
            tags.append("主线题材")
            reasons.append("所属板块处于市场热点前排。")
        if stock.catalyst:
            tags.append("题材催化")
            reasons.append(f"存在明确催化: {stock.catalyst}。")
        if stock.momentum_score >= 4:
            tags.append("强势动量")
            reasons.append("动量评分较高，具备情绪承接基础。")
        if stock.price_position == "缩量回踩":
            tags.append("分歧窗口")
            reasons.append("价格处于缩量回踩区，更符合分歧低吸节奏。")
        if stock.risk_reward_ratio >= 2.5:
            tags.append("盈亏比占优")
            reasons.append("风险收益比高于策略底线。")
        if stock.price_position == "追涨":
            tags.append("追高风险")
            reasons.append("当前价格贴近压力位，不适合无脑追高。")
        if market_cycle.stage == "退潮期/补跌期":
            tags.append("退潮防守")
            reasons.append("市场处于退潮期，仓位和节奏必须更保守。")
        if not reasons:
            reasons.append("当前标的缺少足够多的主线与量价共振信号。")

        return StockStrategyProfile(
            stock_code=stock.code,
            stock_name=stock.name,
            market_stage=market_cycle.stage,
            style=style,
            setup=setup,
            methodology_score=methodology_score,
            preferred_position=preferred_position,
            action_bias=action_bias,
            tags=tags,
            reasons=reasons,
        )

    def build_discipline(self, stock: StockSnapshot, snapshot: MarketSnapshot) -> dict:
        market_cycle = self.assess_market_cycle(snapshot)
        profile = self.evaluate_stock(stock, snapshot)
        must_do = [
            f"总仓位不高于 {round(market_cycle.position_upper_bound * 100)}%",
            f"单笔最大亏损控制在总资金 2% 以内，默认止损参考 {round(self.config.stop_loss_ratio * 100)}%",
            "只在计划内的买点、加仓点和止损点执行操作",
        ]
        must_avoid = [
            "没有主线和确认信号时强行出手",
            "亏损后立刻加大仓位扳本",
            "在杂毛股和高位追涨之间频繁切换",
        ]
        if market_cycle.stage == "退潮期/补跌期":
            must_do.append("优先空仓或极轻仓，等待主线重新聚焦")
            must_avoid.append("在退潮期重仓抄底高位股")
        elif market_cycle.stage == "亢奋期/加速期":
            must_do.append("围绕龙头和中军做确认后的加仓，不做后排杂毛")
            must_avoid.append("高潮次日无条件满仓追高")
        else:
            must_do.append("先试仓验证，再根据承接强度决定是否加仓")
            must_avoid.append("把试仓阶段当成主升阶段来做")

        return {
            "market_stage": market_cycle.stage,
            "environment": market_cycle.environment,
            "stock_style": profile.style,
            "preferred_position": profile.preferred_position,
            "must_do": must_do,
            "must_avoid": must_avoid,
            "focus": market_cycle.focus,
        }

    def build_market_playbook(self, snapshot: MarketSnapshot) -> dict:
        market_cycle = self.assess_market_cycle(snapshot)
        buy_strategy: list[str] = []
        sell_strategy: list[str] = []
        avoid_actions: list[str] = []

        if market_cycle.stage == "亢奋期/加速期":
            buy_strategy.extend(
                [
                    "主做主线龙头和趋势中军的分歧回封、回踩确认。",
                    "允许在确认承接后逐步加仓，但不做后排杂毛补涨。",
                ]
            )
            sell_strategy.extend(
                [
                    "高潮次日若高位股炸板率抬升，优先锁定部分利润。",
                    "若最高标断板或主线梯队塌陷，主动收缩仓位。",
                ]
            )
            avoid_actions.append("高潮一致时无条件满仓追高。")
        elif market_cycle.stage == "退潮期/补跌期":
            buy_strategy.extend(
                [
                    "只做极少数高辨识度核心股的超预期反抽。",
                    "大部分时间保持空仓或极轻仓，等待新主线确认。",
                ]
            )
            sell_strategy.extend(
                [
                    "一旦出现不及预期，第一时间离场，不恋战。",
                    "高位股出现批量跌停或一字跌停时，优先考虑全面防守。",
                ]
            )
            avoid_actions.append("在退潮期重仓抄底高位股或做无逻辑反弹。")
        else:
            buy_strategy.extend(
                [
                    "先用小仓位验证主线，再根据承接与扩散情况加仓。",
                    "优先参与分歧低吸和缩量回踩，而不是追涨一致高潮。",
                ]
            )
            sell_strategy.extend(
                [
                    "若试仓后承接不足或题材无法扩散，及时回到轻仓等待。",
                    "主线由试探转向退潮时，先减仓再判断。",
                ]
            )
            avoid_actions.append("把试错阶段当成主升阶段去重仓。")

        if snapshot.hot_sectors:
            avoid_actions.append(f"非主线方向暂时让位于 {', '.join(snapshot.hot_sectors[:2])}。")

        return {
            "stage": market_cycle.stage,
            "environment": market_cycle.environment,
            "position_upper_bound": market_cycle.position_upper_bound,
            "action_bias": market_cycle.action_bias,
            "focus": market_cycle.focus,
            "signal_stack": market_cycle.signal_stack,
            "warnings": market_cycle.warnings,
            "buy_strategy": buy_strategy,
            "sell_strategy": sell_strategy,
            "avoid_actions": avoid_actions,
            "mindset_rules": [
                "主力不出牌的时候，不要强行出牌。",
                "只在高胜率窗口重拳出击，其他时间保持耐心。",
                "情绪归情绪，操作归操作，不因上一笔盈亏改写计划。",
            ],
        }

    def build_stock_playbook(self, stock: StockSnapshot, snapshot: MarketSnapshot) -> dict:
        market_cycle = self.assess_market_cycle(snapshot)
        profile = self.evaluate_stock(stock, snapshot)
        discipline = self.build_discipline(stock, snapshot)

        entry_signals: list[str] = []
        add_signals: list[str] = []
        reduce_signals: list[str] = []
        exit_signals: list[str] = []
        no_trade_conditions: list[str] = []

        if profile.setup == "分歧低吸":
            entry_signals.append("缩量回踩后站稳关键支撑，次日承接不弱。")
        elif profile.setup == "趋势跟随":
            entry_signals.append("放量维持趋势，回踩不破 5/10 日关键均线。")
        elif profile.setup == "只宜确认后参与":
            entry_signals.append("必须等待分歧转一致后的再确认，避免直接追高。")
        else:
            entry_signals.append("当前更适合观察，等待更清晰的主线确认。")

        add_signals.extend(
            [
                "首仓验证有效后，再按金字塔节奏加仓。",
                "只有当主线扩散、龙头承接和个股量价继续共振时才允许加仓。",
            ]
        )
        reduce_signals.extend(
            [
                "题材扩散转弱、炸板率抬升或个股连续三次冲高无新高时减仓。",
                "若个股明显弱于同板块龙头，先降仓位再判断。",
            ]
        )
        exit_signals.extend(
            [
                f"跌破支撑位 {stock.support} 或趋势止损位，执行离场。",
                "最高标断板、主线退潮、高位股批量补跌时优先退出。",
                "出现明显情绪顶点并伴随放量滞涨时，分批止盈。",
            ]
        )

        if market_cycle.stage == "退潮期/补跌期":
            no_trade_conditions.extend(
                [
                    "市场处于退潮期且该股不是最核心的逆势抱团标的。",
                    "个股位置偏高但缺少新的题材催化或承接证据。",
                ]
            )
        if profile.style == "观察股":
            no_trade_conditions.append("仅有零散信号，没有形成主线、龙头、量价三重共振。")
        if stock.price_position == "追涨":
            no_trade_conditions.append("价格贴近压力位，不满足低吸或确认后的盈亏比要求。")

        return {
            "stock_code": stock.code,
            "stock_name": stock.name,
            "market_cycle": market_cycle.to_dict(),
            "trade_setup": profile.to_dict(),
            "discipline": discipline,
            "entry_signals": entry_signals,
            "add_signals": add_signals,
            "reduce_signals": reduce_signals,
            "exit_signals": exit_signals,
            "no_trade_conditions": no_trade_conditions,
            "position_plan": {
                "preferred_position": profile.preferred_position,
                "max_total_position": market_cycle.position_upper_bound,
                "first_probe_position": round(min(profile.preferred_position, max(profile.preferred_position * 0.5, 0.05)), 2)
                if profile.preferred_position > 0
                else 0.0,
            },
            "mindset_rules": [
                "先判断这是不是主线机会，再决定是否出手。",
                "不要因为错过而追价，不要因为亏损而扳本。",
                "按照计划行动，而不是按照盘中情绪行动。",
            ],
        }

    def _leader_score(self, stock: StockSnapshot, snapshot: MarketSnapshot) -> float:
        score = 2.2
        if stock.sector in snapshot.hot_sectors:
            score += 1.2
        if stock.catalyst:
            score += 0.8
        if stock.turnover_million >= 500:
            score += 0.5
        if stock.turnover_million >= 1000:
            score += 0.3
        if stock.momentum_score >= 4:
            score += 0.7
        if stock.above_ma20:
            score += 0.3
        return round(min(score, 5.0), 2)

    def _theme_score(self, stock: StockSnapshot, snapshot: MarketSnapshot) -> float:
        score = 2.0
        if stock.sector in snapshot.hot_sectors:
            score += 1.5
        if stock.catalyst:
            score += 1.0
        if stock.sector in snapshot.cold_sectors:
            score -= 0.8
        return round(max(1.0, min(score, 5.0)), 2)

    def _volume_price_score(self, stock: StockSnapshot) -> float:
        score = 2.2
        if stock.price_position == "缩量回踩":
            score += 1.2
        elif stock.price_position == "趋势中段":
            score += 0.8
        elif stock.price_position == "追涨":
            score -= 0.7
        if "稳步放量" in stock.volume_pattern:
            score += 1.0
        elif stock.volume_pattern == "缩量":
            score -= 0.3
        return round(max(1.0, min(score, 5.0)), 2)

    def _timing_score(self, stock: StockSnapshot, market_cycle: MarketCycleAssessment) -> float:
        score = 3.0
        if market_cycle.stage == "亢奋期/加速期" and stock.above_ma20:
            score += 1.0
        if market_cycle.stage == "犹豫期/试探期" and stock.price_position == "缩量回踩":
            score += 0.8
        if market_cycle.stage == "退潮期/补跌期":
            score -= 1.2
            if stock.price_position == "追涨":
                score -= 0.8
        return round(max(1.0, min(score, 5.0)), 2)

    def _risk_reward_score(self, stock: StockSnapshot) -> float:
        if stock.risk_reward_ratio >= 3:
            return 5.0
        if stock.risk_reward_ratio >= 2.2:
            return 4.0
        if stock.risk_reward_ratio >= 1.5:
            return 3.0
        if stock.risk_reward_ratio >= 1.0:
            return 2.0
        return 1.0

    def _preferred_position(
        self,
        style: str,
        methodology_score: float,
        market_cycle: MarketCycleAssessment,
    ) -> float:
        base = min(self.config.max_single_position, market_cycle.position_upper_bound)
        if methodology_score >= 4.3:
            multiplier = 1.0
        elif methodology_score >= 3.6:
            multiplier = 0.7
        else:
            multiplier = 0.4
        if style == "观察股":
            multiplier *= 0.5
        if market_cycle.stage == "退潮期/补跌期" and methodology_score < 4.2:
            return 0.0
        return round(min(base * multiplier, self.config.max_single_position), 2)
