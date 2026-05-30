"""Provider interfaces."""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from typing import Any

from src.models import MarketSnapshot, StockSnapshot


class DataNotFoundError(KeyError):
    """Raised when requested market data is unavailable."""


class OnlineDataError(RuntimeError):
    """Raised when a live upstream cannot provide valid market data."""


class MarketDataProvider(ABC):
    """Common interface for market data providers."""

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Human-readable provider name."""

    @abstractmethod
    def get_market_snapshot(self, date: str | None = None) -> MarketSnapshot:
        """Return the market snapshot for a date."""

    @abstractmethod
    def get_stock_snapshot(self, stock_code: str) -> StockSnapshot:
        """Return the stock snapshot for a given code."""

    @abstractmethod
    def list_stock_candidates(self) -> list[StockSnapshot]:
        """Return all candidate stocks known by the provider."""

    def resolve_stock_identifier(self, identifier: str) -> dict[str, str]:
        """Resolve a stock code or Chinese short name to a canonical stock code."""
        raw = str(identifier or "").strip()
        if not raw:
            raise DataNotFoundError("empty stock identifier")

        normalized = raw.lower()
        if re.fullmatch(r"(sh|sz|bj)\d{6}", normalized):
            return {
                "query": raw,
                "code": normalized[2:],
                "name": "",
                "matched_by": "symbol",
            }
        if re.fullmatch(r"\d{6}", raw):
            stock_name = ""
            for stock in self.list_stock_candidates():
                if stock.code == raw:
                    stock_name = stock.name
                    break
            return {
                "query": raw,
                "code": raw,
                "name": stock_name,
                "matched_by": "code",
            }

        prefix_matches: list[StockSnapshot] = []
        fuzzy_matches: list[StockSnapshot] = []
        for stock in self.list_stock_candidates():
            if raw == stock.name:
                return {
                    "query": raw,
                    "code": stock.code,
                    "name": stock.name,
                    "matched_by": "name_exact",
                }
            if stock.name.startswith(raw):
                prefix_matches.append(stock)
            elif raw in stock.name:
                fuzzy_matches.append(stock)

        if len(prefix_matches) == 1:
            stock = prefix_matches[0]
            return {
                "query": raw,
                "code": stock.code,
                "name": stock.name,
                "matched_by": "name_prefix",
            }
        if len(fuzzy_matches) == 1:
            stock = fuzzy_matches[0]
            return {
                "query": raw,
                "code": stock.code,
                "name": stock.name,
                "matched_by": "name_fuzzy",
            }

        raise DataNotFoundError(raw)

    def get_stock_news(self, stock_code: str, page_size: int = 10) -> list[dict[str, Any]]:
        """Return the latest stock-specific news items."""
        raise NotImplementedError("stock news is not implemented by this provider")

    def get_market_telegraph(self, page_size: int = 20) -> list[dict[str, Any]]:
        """Return market-wide telegraph items."""
        raise NotImplementedError("market telegraph is not implemented by this provider")

    def get_global_news(self, page_size: int = 20) -> list[dict[str, Any]]:
        """Return global fast-news items."""
        raise NotImplementedError("global news is not implemented by this provider")

    def get_announcements(self, stock_code: str, page_size: int = 10) -> list[dict[str, Any]]:
        """Return stock announcements."""
        raise NotImplementedError("announcements are not implemented by this provider")

    def get_fund_flow_minute(self, stock_code: str) -> list[dict[str, Any]]:
        """Return intraday minute-level fund flow."""
        raise NotImplementedError("minute fund flow is not implemented by this provider")

    def get_fund_flow_120d(self, stock_code: str, limit: int = 120) -> list[dict[str, Any]]:
        """Return recent daily fund-flow rows."""
        raise NotImplementedError("daily fund flow is not implemented by this provider")

    def get_sector_rankings(self, top_n: int = 10) -> dict[str, Any]:
        """Return industry board rankings."""
        raise NotImplementedError("sector rankings are not implemented by this provider")

    def get_hot_stocks(self, trade_date: str | None = None, page_size: int = 20) -> list[dict[str, Any]]:
        """Return THS hot stocks and their reason tags."""
        raise NotImplementedError("hot stocks are not implemented by this provider")

    def get_concept_blocks(self, stock_code: str) -> dict[str, Any]:
        """Return concept, industry, and region blocks for a stock."""
        raise NotImplementedError("concept blocks are not implemented by this provider")

    def get_research_reports(self, stock_code: str, page_size: int = 10) -> list[dict[str, Any]]:
        """Return recent research reports for a stock."""
        raise NotImplementedError("research reports are not implemented by this provider")

    def get_dragon_tiger_board(
        self,
        stock_code: str,
        trade_date: str,
        look_back: int = 30,
    ) -> dict[str, Any]:
        """Return stock-specific dragon-tiger records and seats."""
        raise NotImplementedError("dragon tiger board is not implemented by this provider")

    def get_daily_dragon_tiger(
        self,
        trade_date: str,
        min_net_buy: float | None = None,
    ) -> dict[str, Any]:
        """Return the daily market-wide dragon-tiger board."""
        raise NotImplementedError("daily dragon tiger is not implemented by this provider")

    def get_margin_trading(self, stock_code: str, page_size: int = 10) -> list[dict[str, Any]]:
        """Return margin trading rows."""
        raise NotImplementedError("margin trading is not implemented by this provider")

    def get_block_trades(self, stock_code: str, page_size: int = 10) -> list[dict[str, Any]]:
        """Return block trade rows."""
        raise NotImplementedError("block trades are not implemented by this provider")

    def get_holder_numbers(self, stock_code: str, page_size: int = 10) -> list[dict[str, Any]]:
        """Return shareholder count changes."""
        raise NotImplementedError("holder numbers are not implemented by this provider")

    def get_dividend_history(self, stock_code: str, page_size: int = 10) -> list[dict[str, Any]]:
        """Return dividend and transfer history."""
        raise NotImplementedError("dividend history is not implemented by this provider")

    def get_lockup_expiry(
        self,
        stock_code: str,
        trade_date: str,
        forward_days: int = 90,
    ) -> dict[str, Any]:
        """Return historical and upcoming lockup expiry rows."""
        raise NotImplementedError("lockup expiry is not implemented by this provider")

    def get_northbound_flow(self, history_days: int = 20) -> dict[str, Any]:
        """Return realtime northbound flow plus cached history."""
        raise NotImplementedError("northbound flow is not implemented by this provider")

    def get_stock_info(self, stock_code: str) -> dict[str, Any]:
        """Return basic stock information."""
        raise NotImplementedError("stock info is not implemented by this provider")

    def get_realtime_quotes(self, codes: list[str], kind: str = "auto") -> list[dict[str, Any]]:
        """Return realtime Tencent-style quotes for stocks, indexes, or ETFs."""
        raise NotImplementedError("realtime quotes are not implemented by this provider")

    def get_price_bars(self, stock_code: str, frequency: int = 4, limit: int = 20) -> list[dict[str, Any]]:
        """Return K-line bars from the market-data source."""
        raise NotImplementedError("price bars are not implemented by this provider")

    def get_order_book(self, stock_code: str) -> dict[str, Any]:
        """Return a realtime five-level order book."""
        raise NotImplementedError("order book is not implemented by this provider")

    def get_transactions(self, stock_code: str, start: int = 0, limit: int = 50) -> list[dict[str, Any]]:
        """Return tick-by-tick transactions."""
        raise NotImplementedError("transactions are not implemented by this provider")

    def get_financial_snapshot(self, stock_code: str) -> dict[str, Any]:
        """Return the latest quarterly finance snapshot."""
        raise NotImplementedError("financial snapshot is not implemented by this provider")

    def get_f10_profile(self, stock_code: str, category: str | None = None) -> dict[str, str]:
        """Return F10 text sections keyed by category."""
        raise NotImplementedError("F10 profile is not implemented by this provider")

    def get_financial_report(
        self,
        stock_code: str,
        report_type: str = "lrb",
        page_size: int = 20,
    ) -> list[dict[str, Any]]:
        """Return financial statement rows."""
        raise NotImplementedError("financial reports are not implemented by this provider")

    def get_consensus_eps(self, stock_code: str) -> list[dict[str, Any]]:
        """Return THS consensus EPS rows."""
        raise NotImplementedError("consensus eps is not implemented by this provider")

    def iwencai_search(
        self,
        query: str,
        channel: str = "report",
        size: int = 50,
    ) -> list[dict[str, Any]]:
        """Return iwencai semantic-search results."""
        raise NotImplementedError("iwencai search is not implemented by this provider")

    def iwencai_query(
        self,
        query: str,
        page: int = 1,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Return iwencai structured-query rows."""
        raise NotImplementedError("iwencai query is not implemented by this provider")
