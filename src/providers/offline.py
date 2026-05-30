"""Offline-first provider with optional JSON overrides."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.config import Config
from src.models import MarketSnapshot, StockSnapshot
from src.providers.base import DataNotFoundError, MarketDataProvider
from src.providers.default_data import DEFAULT_MARKET, DEFAULT_STOCKS


class OfflineFirstProvider(MarketDataProvider):
    """Load local JSON fixture data first, then fall back to built-ins."""

    def __init__(self, config: Config | None = None):
        self.config = config or Config.load()
        payload = self._load_payload()
        self._market = MarketSnapshot(**payload["market"])
        self._stocks = {
            item["code"]: StockSnapshot(
                notes=tuple(item.get("notes", [])),
                **{key: value for key, value in item.items() if key != "notes"},
            )
            for item in payload["stocks"]
        }

    @property
    def source_name(self) -> str:
        if self.config.sample_data_path:
            return "json-fixture"
        return "built-in-fixture"

    def _load_payload(self) -> dict:
        if not self.config.sample_data_path:
            return {"market": DEFAULT_MARKET, "stocks": DEFAULT_STOCKS}

        path = Path(self.config.sample_data_path)
        if not path.exists():
            return {"market": DEFAULT_MARKET, "stocks": DEFAULT_STOCKS}

        payload = json.loads(path.read_text(encoding="utf-8"))
        if "market" not in payload or "stocks" not in payload:
            return {"market": DEFAULT_MARKET, "stocks": DEFAULT_STOCKS}
        return payload

    def get_market_snapshot(self, date: str | None = None) -> MarketSnapshot:
        if date and date != self._market.date:
            return MarketSnapshot(date=date, **{key: value for key, value in self._market.to_dict().items() if key != "date"})
        return self._market

    def get_stock_snapshot(self, stock_code: str) -> StockSnapshot:
        try:
            return self._stocks[stock_code]
        except KeyError as exc:
            raise DataNotFoundError(stock_code) from exc

    def list_stock_candidates(self) -> list[StockSnapshot]:
        return list(self._stocks.values())

    def get_stock_news(self, stock_code: str, page_size: int = 10) -> list[dict[str, Any]]:
        stock = self.get_stock_snapshot(stock_code)
        return [
            {
                "title": f"{stock.name} 离线样例新闻 {index}",
                "content": f"{stock.name} 当前处于离线样例模式，真实新闻需要在线 provider。",
                "time": self._market.date,
                "source": self.source_name,
                "url": "",
            }
            for index in range(1, min(page_size, 3) + 1)
        ]

    def get_market_telegraph(self, page_size: int = 20) -> list[dict[str, Any]]:
        items = [
            {
                "title": "离线模式市场快讯",
                "content": "当前使用内置样例数据，市场快讯未接入实时源。",
                "time": f"{self._market.date} 09:30:00",
                "source": self.source_name,
            },
            {
                "title": "离线模式提示",
                "content": "切换到在线模式后可获取财联社和东方财富快讯。",
                "time": f"{self._market.date} 10:00:00",
                "source": self.source_name,
            },
        ]
        return items[:page_size]

    def get_global_news(self, page_size: int = 20) -> list[dict[str, Any]]:
        return self.get_market_telegraph(page_size)

    def get_announcements(self, stock_code: str, page_size: int = 10) -> list[dict[str, Any]]:
        stock = self.get_stock_snapshot(stock_code)
        return [
            {
                "title": f"{stock.name} 关于经营情况的离线样例公告",
                "type": "样例公告",
                "date": self._market.date,
                "url": "",
            }
        ][:page_size]

    def get_fund_flow_minute(self, stock_code: str) -> list[dict[str, Any]]:
        stock = self.get_stock_snapshot(stock_code)
        return [
            {
                "time": f"{self._market.date} 09:35",
                "main_net": round(stock.turnover_million * 20_000, 2),
                "small_net": -500_000.0,
                "mid_net": 200_000.0,
                "large_net": 150_000.0,
                "super_net": 150_000.0,
            },
            {
                "time": f"{self._market.date} 10:30",
                "main_net": round(stock.turnover_million * 25_000, 2),
                "small_net": -650_000.0,
                "mid_net": 220_000.0,
                "large_net": 180_000.0,
                "super_net": 210_000.0,
            },
        ]

    def get_fund_flow_120d(self, stock_code: str, limit: int = 120) -> list[dict[str, Any]]:
        stock = self.get_stock_snapshot(stock_code)
        rows = []
        for index in range(1, min(limit, 5) + 1):
            rows.append(
                {
                    "date": f"2026-05-0{index}",
                    "main_net": round(stock.turnover_million * 10_000 * index, 2),
                    "small_net": round(-150_000.0 * index, 2),
                    "mid_net": round(60_000.0 * index, 2),
                    "large_net": round(40_000.0 * index, 2),
                    "super_net": round(25_000.0 * index, 2),
                }
            )
        return rows

    def get_sector_rankings(self, top_n: int = 10) -> dict[str, Any]:
        sectors = [
            {"rank": 1, "name": "AI 算力", "change_pct": 2.8, "code": "BK1001", "up_count": 23, "down_count": 5, "leader": "工业富联", "leader_change": 5.2},
            {"rank": 2, "name": "储能", "change_pct": 2.1, "code": "BK1002", "up_count": 18, "down_count": 7, "leader": "宁德时代", "leader_change": 3.1},
            {"rank": 3, "name": "有色", "change_pct": 1.5, "code": "BK1003", "up_count": 15, "down_count": 9, "leader": "紫金矿业", "leader_change": 2.7},
            {"rank": 4, "name": "白酒", "change_pct": -1.2, "code": "BK1004", "up_count": 4, "down_count": 20, "leader": "贵州茅台", "leader_change": -0.5},
        ]
        size = min(top_n, len(sectors))
        return {"top": sectors[:size], "bottom": sectors[-size:], "total": len(sectors)}

    def get_hot_stocks(self, trade_date: str | None = None, page_size: int = 20) -> list[dict[str, Any]]:
        date = trade_date or self._market.date
        rows = [
            {
                "date": date,
                "code": "300750",
                "name": "宁德时代",
                "reason": "储能 + 固态电池 + 出海订单",
                "close": 412.5,
                "change_amount": 12.3,
                "change_pct": 3.07,
                "turnover_pct": 5.8,
                "amount": 22_373_358_897.0,
                "volume": 53_372_900.0,
                "big_order_net": 1.26,
                "market": "创业板",
            },
            {
                "date": date,
                "code": "300308",
                "name": "中际旭创",
                "reason": "算力 + 光模块 + 北美订单",
                "close": 168.2,
                "change_amount": 8.6,
                "change_pct": 5.39,
                "turnover_pct": 7.2,
                "amount": 8_620_000_000.0,
                "volume": 18_900_000.0,
                "big_order_net": 0.84,
                "market": "创业板",
            },
        ]
        return rows[:page_size]

    def get_concept_blocks(self, stock_code: str) -> dict[str, Any]:
        stock = self.get_stock_snapshot(stock_code)
        return {
            "stock_code": stock_code,
            "stock_name": stock.name,
            "industry": [
                {"name": stock.sector, "change_pct": 2.1, "desc": "离线样例行业"},
            ],
            "concept": [
                {"name": "储能", "change_pct": 2.8, "desc": "离线样例概念"},
                {"name": "动力电池", "change_pct": 1.9, "desc": "离线样例概念"},
            ],
            "region": [
                {"name": "福建", "change_pct": 0.6, "desc": "离线样例地域"},
            ],
            "concept_tags": ["储能", "动力电池"],
        }

    def get_research_reports(self, stock_code: str, page_size: int = 10) -> list[dict[str, Any]]:
        stock = self.get_stock_snapshot(stock_code)
        return [
            {
                "title": f"{stock.name} 离线样例研报",
                "publishDate": f"{self._market.date} 08:00:00",
                "orgSName": "样例研究所",
                "emRatingName": "增持",
                "predictThisYearEps": 1.23,
                "predictNextYearEps": 1.45,
                "predictNextTwoYearEps": 1.66,
                "indvInduName": stock.sector,
                "pdfUrl": "",
            }
        ][:page_size]

    def get_dragon_tiger_board(
        self,
        stock_code: str,
        trade_date: str,
        look_back: int = 30,
    ) -> dict[str, Any]:
        stock = self.get_stock_snapshot(stock_code)
        return {
            "stock_code": stock_code,
            "trade_date": trade_date,
            "look_back": look_back,
            "records": [
                {"date": trade_date, "reason": "日涨幅偏离值达7%", "net_buy": 3250.5, "turnover": 18.4}
            ],
            "seats": {
                "buy": [
                    {"name": "机构专用", "buy_amt": 5200.0, "sell_amt": 800.0, "net": 4400.0},
                    {"name": "中信证券上海分公司", "buy_amt": 1800.0, "sell_amt": 200.0, "net": 1600.0},
                ],
                "sell": [
                    {"name": "某量化席位", "buy_amt": 300.0, "sell_amt": 2400.0, "net": -2100.0}
                ],
            },
            "institution": {"buy_amt": 5200.0, "sell_amt": 800.0, "net_amt": 4400.0},
            "stock_name": stock.name,
        }

    def get_daily_dragon_tiger(
        self,
        trade_date: str,
        min_net_buy: float | None = None,
    ) -> dict[str, Any]:
        rows = [
            {
                "code": "300750",
                "name": "宁德时代",
                "reason": "日涨幅偏离值达7%",
                "close": 412.5,
                "change_pct": 4.1,
                "net_buy_wan": 6800.0,
                "buy_wan": 12000.0,
                "sell_wan": 5200.0,
                "turnover_pct": 9.2,
            },
            {
                "code": "002594",
                "name": "比亚迪",
                "reason": "连续三日涨幅偏离值累计达20%",
                "close": 298.0,
                "change_pct": 2.5,
                "net_buy_wan": 3200.0,
                "buy_wan": 7900.0,
                "sell_wan": 4700.0,
                "turnover_pct": 6.3,
            },
        ]
        if min_net_buy is not None:
            rows = [item for item in rows if item["net_buy_wan"] >= min_net_buy]
        return {"date": trade_date, "total_records": len(rows), "stocks": rows}

    def get_margin_trading(self, stock_code: str, page_size: int = 10) -> list[dict[str, Any]]:
        return [
            {
                "date": "2026-05-28",
                "rzye": 18_200_000_000.0,
                "rzmre": 1_120_000_000.0,
                "rzche": 1_050_000_000.0,
                "rqye": 620_000_000.0,
                "rqmcl": 120_000.0,
                "rqchl": 98_000.0,
                "rzrqye": 18_820_000_000.0,
            }
        ][:page_size]

    def get_block_trades(self, stock_code: str, page_size: int = 10) -> list[dict[str, Any]]:
        return [
            {
                "date": "2026-05-27",
                "price": 405.6,
                "vol": 32.5,
                "amount": 13_182_000.0,
                "buyer": "机构专用",
                "seller": "某营业部",
                "premium_pct": -1.8,
            }
        ][:page_size]

    def get_holder_numbers(self, stock_code: str, page_size: int = 10) -> list[dict[str, Any]]:
        return [
            {
                "date": "2026-03-31",
                "holder_num": 520_000,
                "change_num": -18_000,
                "change_ratio": -3.35,
                "avg_shares": 11_200.0,
            }
        ][:page_size]

    def get_dividend_history(self, stock_code: str, page_size: int = 10) -> list[dict[str, Any]]:
        return [
            {
                "date": "2026-05-20",
                "bonus_rmb": 1.2,
                "transfer_ratio": 0.0,
                "bonus_ratio": 0.0,
                "plan": "实施完成",
            }
        ][:page_size]

    def get_lockup_expiry(
        self,
        stock_code: str,
        trade_date: str,
        forward_days: int = 90,
    ) -> dict[str, Any]:
        return {
            "stock_code": stock_code,
            "trade_date": trade_date,
            "forward_days": forward_days,
            "history": [
                {"date": "2026-04-15", "type": "股权激励限售股份", "shares": 12_000_000, "ratio": 0.45}
            ],
            "upcoming": [
                {"date": "2026-07-20", "type": "首发机构配售股份", "shares": 25_000_000, "ratio": 0.92}
            ],
        }

    def get_northbound_flow(self, history_days: int = 20) -> dict[str, Any]:
        realtime = [
            {"time": "09:30", "hgt_yi": 5.2, "sgt_yi": 3.8},
            {"time": "10:30", "hgt_yi": 12.6, "sgt_yi": 8.1},
            {"time": "15:00", "hgt_yi": 18.4, "sgt_yi": 11.7},
        ]
        history = [
            {"date": "2026-05-26", "hgt": 15.2, "sgt": 10.4},
            {"date": "2026-05-27", "hgt": 11.8, "sgt": 7.9},
            {"date": "2026-05-28", "hgt": 18.4, "sgt": 11.7},
        ]
        return {
            "date": self._market.date,
            "realtime": realtime,
            "latest": realtime[-1],
            "history": history[-history_days:],
        }

    def get_stock_info(self, stock_code: str) -> dict[str, Any]:
        stock = self.get_stock_snapshot(stock_code)
        return {
            "code": stock.code,
            "name": stock.name,
            "industry": stock.sector,
            "total_shares": 2_500_000_000,
            "float_shares": 2_100_000_000,
            "mcap": round(stock.price * 2_500_000_000, 2),
            "float_mcap": round(stock.price * 2_100_000_000, 2),
            "list_date": "2018-06-11",
            "price": stock.price,
        }

    def get_realtime_quotes(self, codes: list[str], kind: str = "auto") -> list[dict[str, Any]]:
        items = []
        for code in codes:
            normalized = code.strip()
            if normalized in {"sh000300", "000300"}:
                items.append(
                    {
                        "input": code,
                        "symbol": "sh000300",
                        "code": "000300",
                        "name": "沪深300",
                        "kind": "index",
                        "price": 3812.45,
                        "last_close": 3798.12,
                        "open": 3805.0,
                        "change_amt": 14.33,
                        "change_pct": 0.38,
                        "high": 3821.2,
                        "low": 3792.8,
                        "amount_wan": 0.0,
                        "turnover_pct": 0.0,
                        "pe_ttm": 0.0,
                        "pb": 0.0,
                        "mcap_yi": 0.0,
                        "float_mcap_yi": 0.0,
                        "limit_up": 0.0,
                        "limit_down": 0.0,
                    }
                )
                continue
            if normalized in {"510300", "sh510300"}:
                items.append(
                    {
                        "input": code,
                        "symbol": "sh510300",
                        "code": "510300",
                        "name": "沪深300ETF",
                        "kind": "etf",
                        "price": 3.912,
                        "last_close": 3.876,
                        "open": 3.884,
                        "change_amt": 0.036,
                        "change_pct": 0.93,
                        "high": 3.926,
                        "low": 3.871,
                        "amount_wan": 186523.0,
                        "turnover_pct": 2.14,
                        "pe_ttm": 0.0,
                        "pb": 0.0,
                        "mcap_yi": 0.0,
                        "float_mcap_yi": 0.0,
                        "limit_up": 0.0,
                        "limit_down": 0.0,
                    }
                )
                continue
            stock = self.get_stock_snapshot(normalized.replace("sh", "").replace("sz", "").replace("bj", ""))
            items.append(
                {
                    "input": code,
                    "symbol": f"sz{stock.code}" if stock.code.startswith(("0", "1", "2", "3")) else f"sh{stock.code}",
                    "code": stock.code,
                    "name": stock.name,
                    "kind": "stock",
                    "price": stock.price,
                    "last_close": round(stock.price - 3.2, 2),
                    "open": round(stock.price - 1.6, 2),
                    "change_amt": 3.2,
                    "change_pct": 1.61,
                    "high": round(stock.price + 2.3, 2),
                    "low": round(stock.price - 2.7, 2),
                    "amount_wan": stock.turnover_million * 100,
                    "turnover_pct": 1.25,
                    "pe_ttm": stock.pe,
                    "pb": 4.82,
                    "mcap_yi": round(stock.price * 25, 2),
                    "float_mcap_yi": round(stock.price * 21, 2),
                    "limit_up": round(stock.price * 1.1, 2),
                    "limit_down": round(stock.price * 0.9, 2),
                }
            )
        return items

    def get_price_bars(self, stock_code: str, frequency: int = 4, limit: int = 20) -> list[dict[str, Any]]:
        stock = self.get_stock_snapshot(stock_code)
        rows = []
        for index in range(min(limit, 5)):
            rows.append(
                {
                    "datetime": f"2026-05-{24 + index:02d} 15:00",
                    "open": round(stock.price - 8 + index, 2),
                    "close": round(stock.price - 6 + index, 2),
                    "high": round(stock.price - 4 + index, 2),
                    "low": round(stock.price - 10 + index, 2),
                    "vol": 320000 + index * 12000,
                    "amount": 13_500_000_000 + index * 520_000_000,
                }
            )
        return rows

    def get_order_book(self, stock_code: str) -> dict[str, Any]:
        stock = self.get_stock_snapshot(stock_code)
        return {
            "code": stock.code,
            "price": stock.price,
            "last_close": round(stock.price - 9.11, 2),
            "open": round(stock.price - 1.79, 2),
            "high": round(stock.price + 6.07, 2),
            "low": round(stock.price - 8.24, 2),
            "servertime": "13:52:12.132",
            "vol": 368205,
            "amount": 15_639_648_256.0,
            "bids": [
                {"level": 1, "price": round(stock.price - 0.01, 2), "volume": 2},
                {"level": 2, "price": round(stock.price - 0.02, 2), "volume": 14},
                {"level": 3, "price": round(stock.price - 0.03, 2), "volume": 4},
                {"level": 4, "price": round(stock.price - 0.04, 2), "volume": 17},
                {"level": 5, "price": round(stock.price - 0.05, 2), "volume": 3},
            ],
            "asks": [
                {"level": 1, "price": round(stock.price, 2), "volume": 3},
                {"level": 2, "price": round(stock.price + 0.01, 2), "volume": 22},
                {"level": 3, "price": round(stock.price + 0.02, 2), "volume": 2},
                {"level": 4, "price": round(stock.price + 0.06, 2), "volume": 1},
                {"level": 5, "price": round(stock.price + 0.07, 2), "volume": 8},
            ],
        }

    def get_transactions(self, stock_code: str, start: int = 0, limit: int = 50) -> list[dict[str, Any]]:
        return [
            {"time": "13:16", "price": 427.4, "vol": 29, "num": 18, "buyorsell": 1},
            {"time": "13:16", "price": 427.4, "vol": 16, "num": 13, "buyorsell": 1},
            {"time": "13:16", "price": 427.3, "vol": 23, "num": 12, "buyorsell": 1},
        ][start : start + limit]

    def get_financial_snapshot(self, stock_code: str) -> dict[str, Any]:
        stock = self.get_stock_snapshot(stock_code)
        return {
            "code": stock.code,
            "name": stock.name,
            "market": 0 if stock.code.startswith(("0", "1", "2", "3")) else 1,
            "updated_at": self._market.date,
            "liutongguben": 2_100_000_000,
            "zongguben": 2_500_000_000,
            "eps": 5.58,
            "bvps": 45.21,
            "roe": 24.8,
            "profit": 13_963_200_000,
            "income": 84_705_000_000,
            "meigujingzichan": 45.21,
            "meigugongjijin": 12.34,
            "meiguweifeipeili": 18.76,
        }

    def get_f10_profile(self, stock_code: str, category: str | None = None) -> dict[str, str]:
        stock = self.get_stock_snapshot(stock_code)
        categories = {
            "最新提示": f"{stock.name} 离线样例最新提示：包含近期公告、分红和股东大会摘要。",
            "公司概况": f"{stock.name} 离线样例公司概况：主营业务覆盖动力电池、储能与材料。",
            "财务分析": f"{stock.name} 离线样例财务分析：收入保持增长，ROE 维持高位。",
            "股东研究": f"{stock.name} 离线样例股东研究：机构持仓稳定，户均持股上升。",
            "股本结构": f"{stock.name} 离线样例股本结构：总股本与流通股本较稳定。",
            "资本运作": f"{stock.name} 离线样例资本运作：近期无重大并购重组。",
            "业内点评": f"{stock.name} 离线样例业内点评：行业景气延续，龙头优势明显。",
            "行业分析": f"{stock.name} 离线样例行业分析：新能源链条维持高景气。",
            "公司大事": f"{stock.name} 离线样例公司大事：近期发布季度报告并披露回购计划。",
        }
        if category:
            return {category: categories.get(category, "")}
        return categories

    def get_financial_report(
        self,
        stock_code: str,
        report_type: str = "lrb",
        page_size: int = 20,
    ) -> list[dict[str, Any]]:
        rows = {
            "lrb": [
                {"报告日": "2026-03-31", "净利润": "13963200000", "营业总收入": "84705000000"},
                {"报告日": "2025-12-31", "净利润": "50745000000", "营业总收入": "362013000000"},
            ],
            "fzb": [
                {"报告日": "2026-03-31", "资产总计": "825331000000", "负债合计": "492003000000"},
            ],
            "llb": [
                {"报告日": "2026-03-31", "经营活动产生的现金流量净额": "27581000000"},
            ],
        }
        return rows.get(report_type, [])[:page_size]

    def get_consensus_eps(self, stock_code: str) -> list[dict[str, Any]]:
        return [
            {"year": "2026", "institution_count": 31, "min": 19.13, "mean": 20.77, "max": 22.57, "industry_avg": 2.58},
            {"year": "2027", "institution_count": 30, "min": 22.90, "mean": 25.72, "max": 29.52, "industry_avg": 3.29},
        ]

    def iwencai_search(
        self,
        query: str,
        channel: str = "report",
        size: int = 50,
    ) -> list[dict[str, Any]]:
        return [
            {
                "title": f"离线样例 {channel} 检索: {query}",
                "uid": f"offline-{query}",
                "publish_date": "2026-05-28",
                "score": 98.2,
                "channel": channel,
                "organization": "样例研究所",
                "summary": "离线模式下返回的样例语义检索结果。",
                "stock_infos": [{"code": "300750", "name": "宁德时代"}],
            }
        ][:size]

    def iwencai_query(
        self,
        query: str,
        page: int = 1,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        return [
            {"query": query, "股票代码": "300750", "股票简称": "宁德时代", "ROE": 24.8, "page": page}
        ][:limit]
