"""Trusted live market data provider backed by Tencent finance endpoints."""

from __future__ import annotations

import html
import json
import re
import secrets
import subprocess
import time
import uuid
from csv import DictReader, DictWriter
from datetime import datetime, timedelta
from pathlib import Path
from statistics import mean
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from src.config import Config
from src.models import MarketSnapshot, StockSnapshot
from src.providers.base import DataNotFoundError, MarketDataProvider, OnlineDataError
from src.utils.time import SHANGHAI_TZ, shanghai_today_str


SYMBOL_PREFIXES = {
    "sh": ("5", "6", "9"),
    "sz": ("0", "1", "2", "3"),
}

THS_MARKET_LABELS = {
    "17": "沪市",
    "33": "深市",
    "48": "北交所",
}

WATCHLIST_METADATA = {
    "300750": {"sector": "储能"},
    "002594": {"sector": "汽车"},
    "600519": {"sector": "白酒"},
    "000001": {"sector": "银行"},
    "600036": {"sector": "银行"},
    "601318": {"sector": "保险"},
    "000333": {"sector": "家电"},
    "002475": {"sector": "消费电子"},
    "601899": {"sector": "有色"},
    "300308": {"sector": "算力"},
}

ALL_A_SHARE_FS = "m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23,m:0+t:81+s:2048"

INDEX_SYMBOLS = {
    "sh000001": "上证指数",
    "sh000300": "沪深300",
    "sz399001": "深证成指",
    "sz399006": "创业板指",
}

INDEX_CODE_SYMBOLS = {
    "000001": "sh000001",
    "000300": "sh000300",
    "399001": "sz399001",
    "399006": "sz399006",
}

F10_CATEGORIES = (
    "最新提示",
    "公司概况",
    "财务分析",
    "股东研究",
    "股本结构",
    "资本运作",
    "业内点评",
    "行业分析",
    "公司大事",
)


class TencentLiveProvider(MarketDataProvider):
    """Fetch the latest stock and index data from Tencent finance."""

    def __init__(self, config: Config | None = None):
        self.config = config or Config.load()
        self._max_retries = 2

    @property
    def source_name(self) -> str:
        return "live-tencent-finance"

    def _request_with_retries(self, label: str, operation) -> Any:
        last_error: Exception | None = None
        for attempt in range(1, self._max_retries + 1):
            try:
                return operation()
            except (HTTPError, URLError, TimeoutError, json.JSONDecodeError, subprocess.CalledProcessError) as exc:
                last_error = exc
                if attempt >= self._max_retries:
                    break
                time.sleep(0.15 * attempt)
        if isinstance(last_error, HTTPError):
            detail = f"HTTP {last_error.code}"
        elif isinstance(last_error, URLError):
            detail = f"network error: {last_error.reason}"
        elif isinstance(last_error, subprocess.CalledProcessError):
            detail = f"curl failed with exit code {last_error.returncode}"
        else:
            detail = str(last_error) if last_error else "unknown error"
        raise OnlineDataError(f"{label} failed after {self._max_retries} attempts: {detail}") from last_error

    def _http_get_text(self, url: str, encoding: str = "gbk") -> str:
        def run() -> str:
            request = Request(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0",
                    "Accept": "application/json,text/plain,*/*",
                    "Referer": "https://gu.qq.com/",
                },
            )
            with urlopen(request, timeout=self.config.source_timeout_seconds) as response:
                return response.read().decode(encoding, errors="ignore")

        return self._request_with_retries(f"GET text {url}", run)

    def _http_get_json(self, url: str, headers: dict[str, str] | None = None) -> dict[str, Any]:
        def run() -> dict[str, Any]:
            request_headers = {
                "User-Agent": "Mozilla/5.0",
                "Accept": "application/json,text/plain,*/*",
            }
            if headers:
                request_headers.update(headers)
            request = Request(url, headers=request_headers)
            with urlopen(request, timeout=self.config.source_timeout_seconds) as response:
                raw = response.read().decode("utf-8", errors="ignore")
            return json.loads(raw)

        return self._request_with_retries(f"GET json {url}", run)

    def _curl_get_json(self, url: str, headers: dict[str, str] | None = None) -> dict[str, Any]:
        def run() -> dict[str, Any]:
            command = ["curl", "-L", "--max-time", str(int(max(self.config.source_timeout_seconds, 1)))]
            for key, value in (headers or {}).items():
                command.extend(["-H", f"{key}: {value}"])
            command.append(url)
            completed = subprocess.run(command, check=True, capture_output=True, text=True)
            return json.loads(completed.stdout)

        return self._request_with_retries(f"curl json {url}", run)

    def _http_post_form_json(
        self,
        url: str,
        form_data: dict[str, str],
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        def run() -> dict[str, Any]:
            request_headers = {
                "User-Agent": "Mozilla/5.0",
                "Accept": "application/json,text/plain,*/*",
                "Content-Type": "application/x-www-form-urlencoded",
            }
            if headers:
                request_headers.update(headers)
            payload = urlencode(form_data).encode("utf-8")
            request = Request(url, data=payload, headers=request_headers, method="POST")
            with urlopen(request, timeout=self.config.source_timeout_seconds) as response:
                raw = response.read().decode("utf-8", errors="ignore")
            return json.loads(raw)

        return self._request_with_retries(f"POST form json {url}", run)

    def _http_post_json(
        self,
        url: str,
        payload: dict[str, Any],
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        def run() -> dict[str, Any]:
            request_headers = {
                "User-Agent": "Mozilla/5.0",
                "Accept": "application/json,text/plain,*/*",
                "Content-Type": "application/json",
            }
            if headers:
                request_headers.update(headers)
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            request = Request(url, data=body, headers=request_headers, method="POST")
            with urlopen(request, timeout=self.config.source_timeout_seconds) as response:
                raw = response.read().decode("utf-8", errors="ignore")
            return json.loads(raw)

        return self._request_with_retries(f"POST json {url}", run)

    def _resolve_symbol(self, code: str) -> str:
        for prefix, starters in SYMBOL_PREFIXES.items():
            if code.startswith(starters):
                return f"{prefix}{code}"
        raise DataNotFoundError(code)

    def _resolve_quote_symbol(self, code: str, kind: str = "auto") -> tuple[str, str]:
        normalized = code.strip().lower()
        if re.fullmatch(r"(sh|sz|bj)\d{6}", normalized):
            return normalized, normalized[2:]
        raw_code = normalized.upper()
        if kind == "index":
            symbol = INDEX_CODE_SYMBOLS.get(raw_code)
            if not symbol:
                symbol = f"sz{raw_code}" if raw_code.startswith("399") else f"sh{raw_code}"
            return symbol, raw_code
        if kind == "etf":
            return self._resolve_symbol(raw_code), raw_code
        if kind == "stock":
            return self._resolve_symbol(raw_code), raw_code
        if raw_code in INDEX_CODE_SYMBOLS and raw_code != "000001":
            return INDEX_CODE_SYMBOLS[raw_code], raw_code
        if raw_code.startswith("399"):
            return f"sz{raw_code}", raw_code
        return self._resolve_symbol(raw_code), raw_code

    def _build_secid(self, code: str) -> str:
        return f"1.{code}" if code.startswith(("5", "6", "9")) else f"0.{code}"

    def _strip_html(self, value: str) -> str:
        return html.unescape(re.sub(r"<[^>]+>", "", value or "")).strip()

    def _normalize_text(self, value: str) -> str:
        cleaned = re.sub(r"\s+", " ", self._strip_html(value))
        return re.sub(r"\s*展开$", "", cleaned).strip()

    def _get_mootdx_client(self) -> Any:
        try:
            from mootdx.quotes import Quotes
        except ImportError as exc:
            raise OnlineDataError("mootdx is not installed. Install the optional mootdx dependency to enable quarterly snapshots and F10.") from exc
        try:
            return Quotes.factory(market="std")
        except Exception as exc:
            raise OnlineDataError(f"mootdx client initialization failed: {exc}") from exc

    def _optimize_f10_text(self, category: str, text: str) -> str:
        cleaned = re.sub(r"\r\n?", "\n", text or "").strip()
        if category == "股东研究":
            marker = re.search(r"(4[\.、]股东变化.*)", cleaned, re.DOTALL)
            if marker and len(marker.group(1)) > 4000:
                prefix = cleaned[: marker.start(1)].rstrip()
                trimmed = marker.group(1)[:4000].rstrip()
                cleaned = f"{prefix}\n\n{trimmed}\n\n[股东变化历史内容已截断]"
        if len(cleaned) > 6000:
            cleaned = cleaned[:6000].rstrip() + "\n\n[内容已截断]"
        return cleaned

    def _normalize_mootdx_payload(self, payload: Any) -> list[dict[str, Any]]:
        if hasattr(payload, "to_dict"):
            rows = payload.to_dict(orient="records")
        elif isinstance(payload, list):
            rows = payload
        elif isinstance(payload, dict):
            rows = [payload]
        else:
            rows = []
        normalized: list[dict[str, Any]] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            item: dict[str, Any] = {}
            for key, value in row.items():
                if hasattr(value, "item"):
                    try:
                        value = value.item()
                    except Exception:
                        pass
                item[str(key)] = value
            normalized.append(item)
        return normalized

    def _parse_jsonp(self, text: str) -> dict[str, Any]:
        start = text.find("(")
        end = text.rfind(")")
        if start < 0 or end <= start:
            raise OnlineDataError("invalid JSONP payload")
        return json.loads(text[start + 1 : end])

    def _claw_headers(self, call_type: str = "normal") -> dict[str, str]:
        return {
            "X-Claw-Call-Type": call_type,
            "X-Claw-Skill-Id": "a-shares-master",
            "X-Claw-Skill-Version": "2.0.0",
            "X-Claw-Plugin-Id": "none",
            "X-Claw-Plugin-Version": "none",
            "X-Claw-Trace-Id": secrets.token_hex(32),
        }

    def _to_float(self, value: Any, default: float = 0.0) -> float:
        if value in (None, "", "-", "--"):
            return default
        try:
            return float(str(value).replace("%", "").replace(",", "").strip())
        except (TypeError, ValueError):
            return default

    def _parse_consensus_table(self, html_text: str) -> list[dict[str, Any]]:
        match = re.search(
            r"汇总--预测年报每股收益.*?<tbody>(.*?)</tbody>",
            html_text,
            re.DOTALL,
        )
        if not match:
            return []
        rows = []
        for row_html in re.findall(r"<tr>(.*?)</tr>", match.group(1), re.DOTALL):
            cells = [
                self._strip_html(cell).replace("\xa0", " ").strip()
                for cell in re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", row_html, re.DOTALL)
            ]
            if len(cells) < 6 or not cells[0].isdigit():
                continue
            rows.append(
                {
                    "year": cells[0],
                    "institution_count": int(cells[1]),
                    "min": float(cells[2]),
                    "mean": float(cells[3]),
                    "max": float(cells[4]),
                    "industry_avg": float(cells[5]),
                }
            )
        return rows

    def _dedup_iwencai_articles(self, articles: list[dict[str, Any]]) -> list[dict[str, Any]]:
        best: dict[str, dict[str, Any]] = {}
        for article in articles:
            uid = article.get("uid") or f"{article.get('title', '')}|{article.get('publish_date', '')}"
            score = float(article.get("score", 0) or 0)
            current = best.get(uid)
            if current is None or score > float(current.get("score", 0) or 0):
                best[uid] = article
        return sorted(best.values(), key=lambda item: item.get("publish_date", ""), reverse=True)

    def _cninfo_org_id(self, code: str) -> str:
        if code.startswith("6"):
            return f"gssh0{code}"
        if code.startswith(("4", "8")):
            return f"gsbj0{code}"
        return f"gssz0{code}"

    def _cninfo_date(self, value: Any) -> str:
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(value / 1000, tz=SHANGHAI_TZ).strftime("%Y-%m-%d")
        return str(value or "")[:10]

    def _eastmoney_datacenter(
        self,
        report_name: str,
        filter_str: str = "",
        page_size: int = 50,
        sort_columns: str = "",
        sort_types: str = "-1",
        columns: str = "ALL",
    ) -> list[dict[str, Any]]:
        payload = self._http_get_json(
            "https://datacenter-web.eastmoney.com/api/data/v1/get?"
            + urlencode(
                {
                    "reportName": report_name,
                    "columns": columns,
                    "filter": filter_str,
                    "pageNumber": "1",
                    "pageSize": str(page_size),
                    "sortColumns": sort_columns,
                    "sortTypes": sort_types,
                    "source": "WEB",
                    "client": "WEB",
                }
            ),
            headers={"Referer": "https://data.eastmoney.com/"},
        )
        result = payload.get("result")
        if not isinstance(result, dict):
            return []
        return result.get("data") or []

    def _cache_path(self, filename: str) -> Path:
        path = Path(self.config.data_cache_dir) / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def _save_northbound_snapshot(self, date: str, hgt: float, sgt: float) -> None:
        path = self._cache_path("northbound_daily.csv")
        rows: dict[str, dict[str, str]] = {}
        if path.exists():
            with path.open("r", encoding="utf-8", newline="") as handle:
                for row in DictReader(handle):
                    if row.get("date"):
                        rows[row["date"]] = row
        rows[date] = {"date": date, "hgt": str(hgt), "sgt": str(sgt)}
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = DictWriter(handle, fieldnames=["date", "hgt", "sgt"])
            writer.writeheader()
            for key in sorted(rows):
                writer.writerow(rows[key])

    def _load_northbound_history(self, limit: int = 20) -> list[dict[str, Any]]:
        path = self._cache_path("northbound_daily.csv")
        if not path.exists():
            return []
        with path.open("r", encoding="utf-8", newline="") as handle:
            rows = list(DictReader(handle))
        result = []
        for row in rows[-limit:]:
            result.append(
                {
                    "date": row.get("date", ""),
                    "hgt": float(row.get("hgt") or 0),
                    "sgt": float(row.get("sgt") or 0),
                }
            )
        return result

    def _fetch_quote_map(self, codes: list[str]) -> dict[str, list[str]]:
        symbols = [self._resolve_symbol(code) for code in codes]
        raw = self._http_get_text(f"https://qt.gtimg.cn/q={','.join(symbols)}")
        result: dict[str, list[str]] = {}
        for line in raw.strip().split(";"):
            line = line.strip()
            if not line or "=" not in line:
                continue
            key, payload = line.split("=", 1)
            symbol = key.replace("v_", "").strip()
            fields = payload.strip().strip('"').split("~")
            if len(fields) < 46 or fields[2] == "":
                continue
            result[fields[2]] = fields
        return result

    def _fetch_all_a_share_rows(
        self,
        limit: int = 5000,
        *,
        sort_field: str = "f3",
        sort_order: str = "1",
        fields: str = "f2,f3,f5,f6,f12,f14",
    ) -> list[dict[str, Any]]:
        payload = self._http_get_json(
            "https://push2.eastmoney.com/api/qt/clist/get?"
            + urlencode(
                {
                    "pn": "1",
                    "pz": str(limit),
                    "po": sort_order,
                    "np": "1",
                    "fltt": "2",
                    "invt": "2",
                    "fid": sort_field,
                    "fs": ALL_A_SHARE_FS,
                    "fields": fields,
                }
            ),
            headers={"Referer": "https://quote.eastmoney.com/center/gridlist.html"},
        )
        return payload.get("data", {}).get("diff", []) or []

    def _market_watchlist_codes(self) -> list[str]:
        configured = [code for code in self.config.live_watchlist if code]
        if not configured or any(code.lower() == "auto" for code in configured):
            rows = self._fetch_all_a_share_rows(limit=80, sort_field="f6", sort_order="1")
            codes = [str(item.get("f12", "")).strip() for item in rows if str(item.get("f12", "")).strip().isdigit()]
            return codes[:40]
        return configured

    def _fetch_market_breadth(self) -> dict[str, Any]:
        rows = self._fetch_all_a_share_rows(limit=5000, sort_field="f3", sort_order="1")
        valid_rows = [item for item in rows if item.get("f3") not in (None, "", "-", "--")]
        advancers = 0
        decliners = 0
        unchanged = 0
        leaders: list[str] = []
        for item in valid_rows:
            pct = self._to_float(item.get("f3"))
            if pct > 0:
                advancers += 1
                if len(leaders) < 5:
                    leaders.append(str(item.get("f14", "")))
            elif pct < 0:
                decliners += 1
            else:
                unchanged += 1
        return {
            "advancers": advancers,
            "decliners": decliners,
            "unchanged": unchanged,
            "leaders": tuple(item for item in leaders if item),
            "sample_size": len(valid_rows),
        }

    def _fetch_symbol_quote_map(self, symbols: list[str]) -> dict[str, list[str]]:
        raw = self._http_get_text(f"https://qt.gtimg.cn/q={','.join(symbols)}")
        result: dict[str, list[str]] = {}
        for line in raw.strip().split(";"):
            line = line.strip()
            if not line or "=" not in line:
                continue
            key, payload = line.split("=", 1)
            symbol = key.replace("v_", "").strip()
            fields = payload.strip().strip('"').split("~")
            if len(fields) < 10:
                continue
            result[symbol] = fields
        return result

    def _fetch_index_quotes(self) -> dict[str, list[str]]:
        raw = self._http_get_text(f"https://qt.gtimg.cn/q={','.join(INDEX_SYMBOLS)}")
        result: dict[str, list[str]] = {}
        for line in raw.strip().split(";"):
            line = line.strip()
            if not line or "=" not in line:
                continue
            key, payload = line.split("=", 1)
            symbol = key.replace("v_", "").strip()
            result[symbol] = payload.strip().strip('"').split("~")
        return result

    def _fetch_kline(self, code: str, limit: int = 20) -> list[list[str]]:
        symbol = self._resolve_symbol(code)
        query = urlencode({"param": f"{symbol},day,,,{limit},qfq"})
        raw = self._http_get_text(f"https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?{query}")
        payload = json.loads(raw)
        data = payload.get("data", {}).get(symbol, {})
        klines = data.get("qfqday") or data.get("day")
        if not klines:
            raise OnlineDataError(f"missing kline data for {code}")
        return klines

    def _find_realtime_anchor(self, fields: list[str]) -> int:
        for index, value in enumerate(fields):
            if len(value) == 14 and value.isdigit():
                return index
        raise OnlineDataError("missing realtime anchor in quote payload")

    def _normalize_snapshot_date(self, value: str) -> str:
        if "-" in value:
            return value
        if len(value) >= 8 and value[:8].isdigit():
            return f"{value[:4]}-{value[4:6]}-{value[6:8]}"
        raise OnlineDataError(f"invalid snapshot date: {value}")

    def _extract_quote_metrics(self, fields: list[str]) -> dict[str, Any]:
        anchor = self._find_realtime_anchor(fields)
        trade_triple = fields[anchor + 5] if len(fields) > anchor + 5 else ""
        amount_wan = None
        if trade_triple and trade_triple.count("/") == 2:
            try:
                amount_wan = float(trade_triple.split("/")[2]) / 10_000
            except (TypeError, ValueError):
                amount_wan = None

        if len(fields) > 50:
            turnover_pct = self._to_float(fields[46] if len(fields) > 46 else "", default=None)
            pe_ttm = self._to_float(fields[52] if len(fields) > 52 else "", default=None)
            pb = self._to_float(fields[53] if len(fields) > 53 else "", default=None)
            amplitude_pct = self._to_float(fields[43] if len(fields) > 43 else "", default=None)
            mcap_yi = self._to_float(fields[44] if len(fields) > 44 else "", default=None)
            float_mcap_yi = self._to_float(fields[45] if len(fields) > 45 else "", default=None)
            limit_up = self._to_float(fields[47] if len(fields) > 47 else "", default=None)
            limit_down = self._to_float(fields[48] if len(fields) > 48 else "", default=None)
        else:
            turnover_pct = self._to_float(fields[anchor + 9] if len(fields) > anchor + 9 else "", default=None)
            pe_ttm = self._to_float(fields[anchor + 16] if len(fields) > anchor + 16 else "", default=None)
            pb = self._to_float(fields[anchor + 19] if len(fields) > anchor + 19 else "", default=None)
            amplitude_pct = self._to_float(fields[anchor + 8] if len(fields) > anchor + 8 else "", default=None)
            mcap_yi = None
            float_mcap_yi = None
            limit_up = None
            limit_down = None

        return {
            "change_amt": self._to_float(fields[anchor + 1] if len(fields) > anchor + 1 else "", default=None),
            "change_pct": self._to_float(fields[anchor + 2] if len(fields) > anchor + 2 else "", default=None),
            "high": self._to_float(fields[anchor + 3] if len(fields) > anchor + 3 else "", default=None),
            "low": self._to_float(fields[anchor + 4] if len(fields) > anchor + 4 else "", default=None),
            "amount_wan": amount_wan,
            "turnover_pct": turnover_pct,
            "pe_ttm": pe_ttm,
            "amplitude_pct": amplitude_pct,
            "mcap_yi": mcap_yi,
            "float_mcap_yi": float_mcap_yi,
            "pb": pb,
            "limit_up": limit_up,
            "limit_down": limit_down,
        }

    def _build_stock_snapshot(self, code: str, fields: list[str]) -> StockSnapshot:
        klines = self._fetch_kline(code, limit=20)
        anchor = self._find_realtime_anchor(fields)
        metrics = self._extract_quote_metrics(fields)
        closes = [float(item[2]) for item in klines]
        highs = [float(item[3]) for item in klines]
        lows = [float(item[4]) for item in klines]
        ma20 = round(mean(closes), 2)
        close_min = min(closes)
        close_max = max(closes)
        price = float(fields[3])
        boll_position = 0.5 if close_max == close_min else round((price - close_min) / (close_max - close_min), 2)
        turnover_million = round((metrics.get("amount_wan") or 0.0) / 100, 2)
        pct_change = float(metrics.get("change_pct") or 0.0)
        momentum = 3.0
        if price >= ma20:
            momentum += 1
        if pct_change > 2:
            momentum += 1
        if pct_change < -2:
            momentum -= 1
        sector = WATCHLIST_METADATA.get(code, {}).get("sector", "A股")
        catalyst = "实时在线价格强于20日均线" if price >= ma20 else "实时在线价格弱于20日均线"
        name = fields[1]
        refreshed_at = fields[anchor]
        return StockSnapshot(
            code=code,
            name=name,
            sector=sector,
            price=price,
            ma20=ma20,
            boll_position=max(0.0, min(1.0, boll_position)),
            pe=float(metrics.get("pe_ttm") or 0.0),
            q1_growth=0.0,
            turnover_million=turnover_million,
            momentum_score=max(1.0, min(5.0, momentum)),
            support=round(min(lows[-10:]), 2),
            resistance=round(max(highs[-10:]), 2),
            catalyst=catalyst,
            under_investigation=False,
            delisting_risk="ST" in name.upper(),
            reduction_plan=False,
            earnings_shock=False,
            earnings_disclosed=True,
            notes=("latest_online_quote", "tencent_finance"),
            data_source=self.source_name,
            refreshed_at=refreshed_at,
        )

    def get_market_snapshot(self, date: str | None = None) -> MarketSnapshot:
        index_quotes = self._fetch_index_quotes()
        if "sh000001" not in index_quotes or "sz399001" not in index_quotes:
            raise OnlineDataError("missing live index quotes")

        sh_fields = index_quotes["sh000001"]
        sz_fields = index_quotes["sz399001"]
        cyb_fields = index_quotes.get("sz399006", [])
        sh_anchor = self._find_realtime_anchor(sh_fields)
        sz_anchor = self._find_realtime_anchor(sz_fields)
        snapshot_date = self._normalize_snapshot_date(date or sh_fields[sh_anchor][:8])
        total_amount = 0.0
        for fields in (sh_fields, sz_fields):
            anchor = self._find_realtime_anchor(fields)
            triple = fields[anchor + 5]
            if triple and triple.count("/") == 2:
                total_amount += float(triple.split("/")[2])

        breadth = self._fetch_market_breadth()
        sector_rankings = self.get_sector_rankings(3)
        advancers = breadth["advancers"]
        decliners = breadth["decliners"]
        unchanged = breadth["unchanged"]
        trend_score = 3.0
        if float(sh_fields[sh_anchor + 2]) > 0:
            trend_score += 0.5
        if cyb_fields:
            cyb_anchor = self._find_realtime_anchor(cyb_fields)
            if float(cyb_fields[cyb_anchor + 2]) > 0:
                trend_score += 0.5
        if not cyb_fields:
            trend_score -= 0.25
        breadth_ratio = (advancers - decliners) / max(advancers + decliners + unchanged, 1)
        sentiment_score = max(1.0, min(5.0, 3 + breadth_ratio * 2 + (trend_score - 3) * 0.6))
        hot_sectors = tuple(item["name"] for item in sector_rankings.get("top", [])[:3])
        cold_sectors = tuple(item["name"] for item in sector_rankings.get("bottom", [])[:2])
        return MarketSnapshot(
            date=snapshot_date,
            total_volume_billion=round(total_amount / 100_000_000, 2),
            policy_score=3.0,
            sentiment_score=round(sentiment_score, 2),
            trend_score=round(trend_score, 2),
            advancers=advancers,
            decliners=decliners,
            unchanged=unchanged,
            hot_sectors=hot_sectors,
            cold_sectors=cold_sectors,
            policy_highlights=("实时在线行情源：腾讯财经", "当前版本未接入政策公告流"),
            leaders=breadth["leaders"],
            overseas_signal="中性",
            data_source=f"{self.source_name}+eastmoney_breadth",
            refreshed_at=sh_fields[sh_anchor],
        )

    def get_stock_snapshot(self, stock_code: str) -> StockSnapshot:
        fields = self._fetch_quote_map([stock_code]).get(stock_code)
        if fields is None or not fields[3]:
            raise DataNotFoundError(stock_code)
        return self._build_stock_snapshot(stock_code, fields)

    def list_stock_candidates(self) -> list[StockSnapshot]:
        quotes = self._fetch_quote_map(self._market_watchlist_codes())
        if not quotes:
            raise OnlineDataError("empty live watchlist response")
        snapshots = [self._build_stock_snapshot(code, fields) for code, fields in quotes.items()]
        return sorted(snapshots, key=lambda item: item.turnover_million, reverse=True)

    def get_stock_news(self, stock_code: str, page_size: int = 10) -> list[dict[str, Any]]:
        query = json.dumps(
            {
                "uid": "",
                "keyword": stock_code,
                "type": ["cmsArticleWebOld"],
                "client": "web",
                "clientType": "web",
                "clientVersion": "curr",
                "param": {
                    "cmsArticleWebOld": {
                        "searchScope": "default",
                        "sort": "default",
                        "pageIndex": 1,
                        "pageSize": page_size,
                        "preTag": "",
                        "postTag": "",
                    }
                },
            },
            ensure_ascii=False,
            separators=(",", ":"),
        )
        raw = self._http_get_text(
            f"https://search-api-web.eastmoney.com/search/jsonp?{urlencode({'cb': 'jQuery_news', 'param': query})}",
            encoding="utf-8",
        )
        payload = self._parse_jsonp(raw)
        article_payload = payload.get("result", {}).get("cmsArticleWebOld", [])
        if isinstance(article_payload, dict):
            articles = article_payload.get("list", [])
        else:
            articles = article_payload
        return [
            {
                "title": self._strip_html(item.get("title", "")),
                "content": self._strip_html(item.get("content", ""))[:200],
                "time": item.get("date", ""),
                "source": item.get("mediaName", ""),
                "url": item.get("url", ""),
            }
            for item in articles
        ]

    def get_market_telegraph(self, page_size: int = 20) -> list[dict[str, Any]]:
        payload = self._http_get_json(
            f"https://www.cls.cn/nodeapi/telegraphList?{urlencode({'rn': str(page_size), 'page': '1'})}",
            headers={"Referer": "https://www.cls.cn/"},
        )
        items = payload.get("data", {}).get("roll_data", [])
        return [
            {
                "title": item.get("title", "") or item.get("brief", ""),
                "content": item.get("content", "") or item.get("brief", ""),
                "time": item.get("ctime", ""),
                "source": "财联社",
            }
            for item in items
        ]

    def get_global_news(self, page_size: int = 20) -> list[dict[str, Any]]:
        payload = self._http_get_json(
            "https://np-weblist.eastmoney.com/comm/web/getFastNewsList?"
            + urlencode(
                {
                    "client": "web",
                    "biz": "web_724",
                    "fastColumn": "102",
                    "sortEnd": "",
                    "pageSize": str(page_size),
                    "req_trace": str(uuid.uuid4()),
                }
            ),
            headers={"Referer": "https://kuaixun.eastmoney.com/"},
        )
        items = payload.get("data", {}).get("fastNewsList", [])
        return [
            {
                "title": item.get("title", ""),
                "summary": item.get("summary", "")[:200],
                "time": item.get("showTime", ""),
                "source": "东方财富",
            }
            for item in items
        ]

    def get_announcements(self, stock_code: str, page_size: int = 10) -> list[dict[str, Any]]:
        payload = self._http_post_form_json(
            "https://www.cninfo.com.cn/new/hisAnnouncement/query",
            form_data={
                "stock": f"{stock_code},{self._cninfo_org_id(stock_code)}",
                "tabName": "fulltext",
                "pageSize": str(page_size),
                "pageNum": "1",
                "column": "",
                "category": "",
                "plate": "",
                "seDate": "",
                "searchkey": "",
                "secid": "",
                "sortName": "",
                "sortType": "",
                "isHLtitle": "true",
            },
            headers={
                "Referer": "https://www.cninfo.com.cn/new/disclosure",
                "Origin": "https://www.cninfo.com.cn",
            },
        )
        return [
            {
                "title": self._strip_html(item.get("announcementTitle", "")),
                "type": item.get("announcementTypeName", ""),
                "date": self._cninfo_date(item.get("announcementTime")),
                "url": f"https://www.cninfo.com.cn/new/disclosure/detail?annoId={item.get('announcementId', '')}",
            }
            for item in (payload.get("announcements") or [])
        ]

    def get_fund_flow_minute(self, stock_code: str) -> list[dict[str, Any]]:
        payload = self._http_get_json(
            "https://push2.eastmoney.com/api/qt/stock/fflow/kline/get?"
            + urlencode(
                {
                    "secid": self._build_secid(stock_code),
                    "klt": "1",
                    "fields1": "f1,f2,f3,f7",
                    "fields2": "f51,f52,f53,f54,f55,f56,f57",
                }
            ),
            headers={
                "Referer": "https://quote.eastmoney.com/",
                "Origin": "https://quote.eastmoney.com",
            },
        )
        rows = []
        for line in payload.get("data", {}).get("klines", []):
            parts = line.split(",")
            if len(parts) < 6:
                continue
            rows.append(
                {
                    "time": parts[0],
                    "main_net": float(parts[1] or 0),
                    "small_net": float(parts[2] or 0),
                    "mid_net": float(parts[3] or 0),
                    "large_net": float(parts[4] or 0),
                    "super_net": float(parts[5] or 0),
                }
            )
        return rows

    def get_fund_flow_120d(self, stock_code: str, limit: int = 120) -> list[dict[str, Any]]:
        payload = self._http_get_json(
            "https://push2his.eastmoney.com/api/qt/stock/fflow/daykline/get?"
            + urlencode(
                {
                    "secid": self._build_secid(stock_code),
                    "fields1": "f1,f2,f3,f7",
                    "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f62,f63,f64,f65",
                    "lmt": str(limit),
                }
            ),
            headers={
                "Referer": "https://quote.eastmoney.com/",
                "Origin": "https://quote.eastmoney.com",
            },
        )
        rows = []
        for line in payload.get("data", {}).get("klines", []):
            parts = line.split(",")
            if len(parts) < 6:
                continue
            rows.append(
                {
                    "date": parts[0],
                    "main_net": float(parts[1]) if parts[1] != "-" else 0.0,
                    "small_net": float(parts[2]) if parts[2] != "-" else 0.0,
                    "mid_net": float(parts[3]) if parts[3] != "-" else 0.0,
                    "large_net": float(parts[4]) if parts[4] != "-" else 0.0,
                    "super_net": float(parts[5]) if parts[5] != "-" else 0.0,
                }
            )
        return rows

    def get_sector_rankings(self, top_n: int = 10) -> dict[str, Any]:
        payload = self._http_get_json(
            "https://push2.eastmoney.com/api/qt/clist/get?"
            + urlencode(
                {
                    "pn": "1",
                    "pz": "100",
                    "po": "1",
                    "np": "1",
                    "fltt": "2",
                    "invt": "2",
                    "fs": "m:90+t:2",
                    "fields": "f2,f3,f4,f12,f13,f14,f104,f105,f128,f136,f140,f141,f207",
                }
            )
        )
        items = payload.get("data", {}).get("diff", [])
        rows = [
            {
                "rank": index + 1,
                "name": item.get("f14", ""),
                "change_pct": item.get("f3", 0),
                "code": item.get("f12", ""),
                "up_count": item.get("f104", 0),
                "down_count": item.get("f105", 0),
                "leader": item.get("f140", ""),
                "leader_change": item.get("f136", 0),
            }
            for index, item in enumerate(items)
        ]
        size = min(top_n, len(rows))
        return {"top": rows[:size], "bottom": rows[-size:], "total": len(rows)}

    def get_hot_stocks(self, trade_date: str | None = None, page_size: int = 20) -> list[dict[str, Any]]:
        observe_date = trade_date or shanghai_today_str()
        payload = self._http_get_json(
            (
                "http://zx.10jqka.com.cn/event/api/getharden/"
                f"date/{observe_date}/orderby/date/orderway/desc/charset/GBK/"
            ),
            headers={"Referer": "http://zx.10jqka.com.cn/"},
        )
        if payload.get("errocode", 0) != 0:
            raise OnlineDataError(payload.get("errormsg", "ths hot stocks failed"))
        rows = payload.get("data") or []
        fallback_quotes = {}
        candidate_codes = [str(item.get("code", "")).strip() for item in rows[:page_size] if str(item.get("code", "")).strip().isdigit()]
        if candidate_codes:
            try:
                fallback_quotes = {item["code"]: item for item in self.get_realtime_quotes(candidate_codes)}
            except Exception:
                fallback_quotes = {}
        results = []
        for item in rows[:page_size]:
            code = str(item.get("code", "")).strip()
            fallback = fallback_quotes.get(code, {})
            results.append(
                {
                    "date": observe_date,
                    "code": code,
                    "name": self._normalize_text(str(item.get("name", ""))),
                    "reason": self._normalize_text(str(item.get("reason", ""))),
                    "close": self._to_float(item.get("close") or item.get("price") or fallback.get("price")),
                    "change_amount": self._to_float(item.get("zhangdie") or item.get("change_amt") or fallback.get("change_amt")),
                    "change_pct": self._to_float(item.get("zhangfu") or item.get("change_pct") or fallback.get("change_pct")),
                    "turnover_pct": self._to_float(item.get("huanshou") or item.get("turnover_pct") or fallback.get("turnover_pct")),
                    "amount": self._to_float(item.get("chengjiaoe") or item.get("amount") or fallback.get("amount_wan")),
                    "volume": self._to_float(item.get("chengjiaoliang") or item.get("volume")),
                    "big_order_net": self._to_float(item.get("ddejingliang") or item.get("big_order_net")),
                    "market": THS_MARKET_LABELS.get(str(item.get("market", "")), str(item.get("market", ""))),
                }
            )
        return results

    def get_concept_blocks(self, stock_code: str) -> dict[str, Any]:
        html_text = self._http_get_text(
            f"https://basic.10jqka.com.cn/{stock_code}/concept.html",
            encoding="gbk",
        )
        match = re.search(r'<table class="gnContent">.*?<tbody>(.*?)</tbody>', html_text, re.DOTALL)
        concept_rows: list[dict[str, Any]] = []
        if match:
            for row_html in re.findall(r"<tr>(.*?)</tr>", match.group(1), re.DOTALL):
                concept_name_match = re.search(r'<td class="gnName"[^>]*>(.*?)</td>', row_html, re.DOTALL)
                desc_match = re.search(r'<td class="wider"[^>]*>(.*?)</td>', row_html, re.DOTALL)
                name = self._strip_html(concept_name_match.group(1)) if concept_name_match else ""
                if not name:
                    continue
                concept_rows.append(
                    {
                        "name": name,
                        "change_pct": 0.0,
                        "desc": self._normalize_text(desc_match.group(1)) if desc_match else "",
                    }
                )
        if not concept_rows:
            raise OnlineDataError("ths concept page returned no concept rows")

        stock_info = self.get_stock_info(stock_code)
        result = {
            "stock_code": stock_code,
            "stock_name": stock_info.get("name", ""),
            "industry": [],
            "concept": concept_rows,
            "region": [],
            "concept_tags": [item["name"] for item in concept_rows],
        }
        if stock_info.get("industry"):
            result["industry"].append(
                {
                    "name": stock_info["industry"],
                    "change_pct": 0.0,
                    "desc": "行业字段来自个股基础信息",
                }
            )
        return result

    def get_research_reports(self, stock_code: str, page_size: int = 10) -> list[dict[str, Any]]:
        payload = self._http_get_json(
            "https://reportapi.eastmoney.com/report/list?"
            + urlencode(
                {
                    "industryCode": "*",
                    "pageSize": str(page_size),
                    "industry": "*",
                    "rating": "*",
                    "ratingChange": "*",
                    "beginTime": "2000-01-01",
                    "endTime": "2030-01-01",
                    "pageNo": "1",
                    "fields": "",
                    "qType": "0",
                    "orgCode": "",
                    "code": stock_code,
                    "rcode": "",
                    "p": "1",
                    "pageNum": "1",
                    "pageNumber": "1",
                }
            ),
            headers={"Referer": "https://data.eastmoney.com/"},
        )
        rows = payload.get("data") or []
        return [
            {
                "title": item.get("title", ""),
                "publishDate": item.get("publishDate", ""),
                "orgSName": item.get("orgSName", ""),
                "emRatingName": item.get("emRatingName", ""),
                "predictThisYearEps": item.get("predictThisYearEps"),
                "predictNextYearEps": item.get("predictNextYearEps"),
                "predictNextTwoYearEps": item.get("predictNextTwoYearEps"),
                "indvInduName": item.get("indvInduName", ""),
                "pdfUrl": (
                    f"https://pdf.dfcfw.com/pdf/H3_{item['infoCode']}_1.pdf"
                    if item.get("infoCode")
                    else ""
                ),
            }
            for item in rows
        ]

    def get_dragon_tiger_board(
        self,
        stock_code: str,
        trade_date: str,
        look_back: int = 30,
    ) -> dict[str, Any]:
        start_date = (datetime.strptime(trade_date, "%Y-%m-%d") - timedelta(days=look_back)).strftime("%Y-%m-%d")
        raw_records = self._eastmoney_datacenter(
            "RPT_DAILYBILLBOARD_DETAILSNEW",
            filter_str=(
                f"(TRADE_DATE>='{start_date}')(TRADE_DATE<='{trade_date}')"
                f'(SECURITY_CODE="{stock_code}")'
            ),
            page_size=50,
            sort_columns="TRADE_DATE",
            sort_types="-1",
        )
        records = [
            {
                "date": str(row.get("TRADE_DATE", ""))[:10],
                "reason": row.get("EXPLANATION", ""),
                "net_buy": round((row.get("BILLBOARD_NET_AMT") or 0) / 10000, 1),
                "turnover": round(float(row.get("TURNOVERRATE") or 0), 2),
            }
            for row in raw_records
        ]
        latest_date = records[0]["date"] if records else trade_date
        buy_rows = self._eastmoney_datacenter(
            "RPT_BILLBOARD_DAILYDETAILSBUY",
            filter_str=f"(TRADE_DATE='{latest_date}')(SECURITY_CODE=\"{stock_code}\")",
            page_size=10,
            sort_columns="BUY",
            sort_types="-1",
        )
        sell_rows = self._eastmoney_datacenter(
            "RPT_BILLBOARD_DAILYDETAILSSELL",
            filter_str=f"(TRADE_DATE='{latest_date}')(SECURITY_CODE=\"{stock_code}\")",
            page_size=10,
            sort_columns="SELL",
            sort_types="-1",
        )
        seats = {
            "buy": [
                {
                    "name": row.get("OPERATEDEPT_NAME", ""),
                    "buy_amt": round((row.get("BUY") or 0) / 10000, 1),
                    "sell_amt": round((row.get("SELL") or 0) / 10000, 1),
                    "net": round((row.get("NET") or 0) / 10000, 1),
                }
                for row in buy_rows[:5]
            ],
            "sell": [
                {
                    "name": row.get("OPERATEDEPT_NAME", ""),
                    "buy_amt": round((row.get("BUY") or 0) / 10000, 1),
                    "sell_amt": round((row.get("SELL") or 0) / 10000, 1),
                    "net": round((row.get("NET") or 0) / 10000, 1),
                }
                for row in sell_rows[:5]
            ],
        }
        institution_buy = sum((row.get("BUY") or 0) for row in buy_rows if str(row.get("OPERATEDEPT_CODE", "")) == "0")
        institution_sell = sum((row.get("SELL") or 0) for row in sell_rows if str(row.get("OPERATEDEPT_CODE", "")) == "0")
        return {
            "stock_code": stock_code,
            "trade_date": trade_date,
            "look_back": look_back,
            "records": records,
            "seats": seats,
            "institution": {
                "buy_amt": round(institution_buy / 10000, 1),
                "sell_amt": round(institution_sell / 10000, 1),
                "net_amt": round((institution_buy - institution_sell) / 10000, 1),
            },
        }

    def get_daily_dragon_tiger(
        self,
        trade_date: str,
        min_net_buy: float | None = None,
    ) -> dict[str, Any]:
        raw_rows = self._eastmoney_datacenter(
            "RPT_DAILYBILLBOARD_DETAILSNEW",
            filter_str=f"(TRADE_DATE>='{trade_date}')(TRADE_DATE<='{trade_date}')",
            page_size=500,
            sort_columns="BILLBOARD_NET_AMT",
            sort_types="-1",
        )
        rows = []
        for row in raw_rows:
            net_buy = round((row.get("BILLBOARD_NET_AMT") or 0) / 10000, 1)
            if min_net_buy is not None and net_buy < min_net_buy:
                continue
            rows.append(
                {
                    "code": row.get("SECURITY_CODE", ""),
                    "name": row.get("SECURITY_NAME_ABBR", ""),
                    "reason": row.get("EXPLANATION", ""),
                    "close": row.get("CLOSE_PRICE") or 0,
                    "change_pct": round(float(row.get("CHANGE_RATE") or 0), 2),
                    "net_buy_wan": net_buy,
                    "buy_wan": round((row.get("BILLBOARD_BUY_AMT") or 0) / 10000, 1),
                    "sell_wan": round((row.get("BILLBOARD_SELL_AMT") or 0) / 10000, 1),
                    "turnover_pct": round(float(row.get("TURNOVERRATE") or 0), 2),
                }
            )
        actual_date = str(raw_rows[0].get("TRADE_DATE", ""))[:10] if raw_rows else trade_date
        return {"date": actual_date, "total_records": len(rows), "stocks": rows}

    def get_margin_trading(self, stock_code: str, page_size: int = 10) -> list[dict[str, Any]]:
        rows = self._eastmoney_datacenter(
            "RPTA_WEB_RZRQ_GGMX",
            filter_str=f'(SCODE="{stock_code}")',
            page_size=page_size,
            sort_columns="DATE",
            sort_types="-1",
        )
        return [
            {
                "date": str(row.get("DATE", ""))[:10],
                "rzye": row.get("RZYE", 0),
                "rzmre": row.get("RZMRE", 0),
                "rzche": row.get("RZCHE", 0),
                "rqye": row.get("RQYE", 0),
                "rqmcl": row.get("RQMCL", 0),
                "rqchl": row.get("RQCHL", 0),
                "rzrqye": row.get("RZRQYE", 0),
            }
            for row in rows
        ]

    def get_block_trades(self, stock_code: str, page_size: int = 10) -> list[dict[str, Any]]:
        rows = self._eastmoney_datacenter(
            "RPT_DATA_BLOCKTRADE",
            filter_str=f'(SECURITY_CODE="{stock_code}")',
            page_size=page_size,
            sort_columns="TRADE_DATE",
            sort_types="-1",
        )
        result = []
        for row in rows:
            close = float(row.get("CLOSE_PRICE") or 0)
            deal_price = float(row.get("DEAL_PRICE") or 0)
            premium = round((deal_price / close - 1) * 100, 2) if close else 0.0
            result.append(
                {
                    "date": str(row.get("TRADE_DATE", ""))[:10],
                    "price": deal_price,
                    "vol": row.get("DEAL_NUM", 0),
                    "amount": row.get("DEAL_AMT", 0),
                    "buyer": row.get("BUYER_NAME", ""),
                    "seller": row.get("SELLER_NAME", ""),
                    "premium_pct": premium,
                }
            )
        return result

    def get_holder_numbers(self, stock_code: str, page_size: int = 10) -> list[dict[str, Any]]:
        rows = self._eastmoney_datacenter(
            "RPT_HOLDERNUMLATEST",
            filter_str=f'(SECURITY_CODE="{stock_code}")',
            page_size=page_size,
            sort_columns="END_DATE",
            sort_types="-1",
        )
        return [
            {
                "date": str(row.get("END_DATE", ""))[:10],
                "holder_num": row.get("HOLDER_NUM", 0),
                "change_num": row.get("HOLDER_NUM_CHANGE", 0),
                "change_ratio": row.get("HOLDER_NUM_RATIO", 0),
                "avg_shares": row.get("AVG_FREE_SHARES", 0),
            }
            for row in rows
        ]

    def get_dividend_history(self, stock_code: str, page_size: int = 10) -> list[dict[str, Any]]:
        rows = self._eastmoney_datacenter(
            "RPT_SHAREBONUS_DET",
            filter_str=f'(SECURITY_CODE="{stock_code}")',
            page_size=page_size,
            sort_columns="EX_DIVIDEND_DATE",
            sort_types="-1",
        )
        return [
            {
                "date": str(row.get("EX_DIVIDEND_DATE", ""))[:10],
                "bonus_rmb": row.get("PRETAX_BONUS_RMB", 0),
                "transfer_ratio": row.get("TRANSFER_RATIO", 0),
                "bonus_ratio": row.get("BONUS_RATIO", 0),
                "plan": row.get("ASSIGN_PROGRESS", ""),
            }
            for row in rows
        ]

    def get_lockup_expiry(
        self,
        stock_code: str,
        trade_date: str,
        forward_days: int = 90,
    ) -> dict[str, Any]:
        history_rows = self._eastmoney_datacenter(
            "RPT_LIFT_STAGE",
            filter_str=f'(SECURITY_CODE="{stock_code}")',
            page_size=15,
            sort_columns="FREE_DATE",
            sort_types="-1",
        )
        end_date = (datetime.strptime(trade_date, "%Y-%m-%d") + timedelta(days=forward_days)).strftime("%Y-%m-%d")
        upcoming_rows = self._eastmoney_datacenter(
            "RPT_LIFT_STAGE",
            filter_str=(
                f'(SECURITY_CODE="{stock_code}")'
                f"(FREE_DATE>='{trade_date}')(FREE_DATE<='{end_date}')"
            ),
            page_size=20,
            sort_columns="FREE_DATE",
            sort_types="1",
        )
        return {
            "stock_code": stock_code,
            "trade_date": trade_date,
            "forward_days": forward_days,
            "history": [
                {
                    "date": str(row.get("FREE_DATE", ""))[:10],
                    "type": row.get("LIMITED_STOCK_TYPE", ""),
                    "shares": row.get("FREE_SHARES_NUM", 0),
                    "ratio": row.get("FREE_RATIO", 0),
                }
                for row in history_rows
            ],
            "upcoming": [
                {
                    "date": str(row.get("FREE_DATE", ""))[:10],
                    "type": row.get("LIMITED_STOCK_TYPE", ""),
                    "shares": row.get("FREE_SHARES_NUM", 0),
                    "ratio": row.get("FREE_RATIO", 0),
                }
                for row in upcoming_rows
            ],
        }

    def get_northbound_flow(self, history_days: int = 20) -> dict[str, Any]:
        payload = self._http_get_json(
            "https://data.hexin.cn/market/hsgtApi/method/dayChart/",
            headers={
                "Host": "data.hexin.cn",
                "Referer": "https://data.hexin.cn/",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/117.0.0.0 Safari/537.36",
            },
        )
        times = payload.get("time", []) or []
        hgt = payload.get("hgt", []) or []
        sgt = payload.get("sgt", []) or []
        realtime = []
        for index, time_value in enumerate(times):
            realtime.append(
                {
                    "time": time_value,
                    "hgt_yi": hgt[index] if index < len(hgt) else None,
                    "sgt_yi": sgt[index] if index < len(sgt) else None,
                }
            )
        latest = next(
            (
                item
                for item in reversed(realtime)
                if item.get("hgt_yi") is not None and item.get("sgt_yi") is not None
            ),
            None,
        )
        today = shanghai_today_str()
        if latest is not None:
            self._save_northbound_snapshot(today, float(latest["hgt_yi"]), float(latest["sgt_yi"]))
        return {
            "date": today,
            "realtime": realtime,
            "latest": latest,
            "history": self._load_northbound_history(history_days),
        }

    def get_stock_info(self, stock_code: str) -> dict[str, Any]:
        url = "https://push2.eastmoney.com/api/qt/stock/get?" + urlencode(
            {
                "fltt": "2",
                "invt": "2",
                "fields": "f57,f58,f84,f85,f127,f116,f117,f189,f43",
                "secid": self._build_secid(stock_code),
            }
        )
        headers = {
            "Referer": "https://quote.eastmoney.com/",
            "Origin": "https://quote.eastmoney.com",
            "User-Agent": "Mozilla/5.0",
        }
        try:
            payload = self._http_get_json(url, headers=headers)
            data = payload.get("data", {}) or {}
            list_date = str(data.get("f189", "") or "")
            formatted_date = (
                f"{list_date[:4]}-{list_date[4:6]}-{list_date[6:8]}"
                if len(list_date) == 8 and list_date.isdigit()
                else list_date
            )
            return {
                "code": data.get("f57", ""),
                "name": data.get("f58", ""),
                "industry": data.get("f127", ""),
                "total_shares": data.get("f84", 0),
                "float_shares": data.get("f85", 0),
                "mcap": data.get("f116", 0),
                "float_mcap": data.get("f117", 0),
                "list_date": formatted_date,
                "price": data.get("f43", 0),
            }
        except Exception:
            snapshot = self.get_stock_snapshot(stock_code)
            return {
                "code": snapshot.code,
                "name": snapshot.name,
                "industry": snapshot.sector,
                "total_shares": 0,
                "float_shares": 0,
                "mcap": 0,
                "float_mcap": 0,
                "list_date": "",
                "price": snapshot.price,
                "fallback_source": "tencent_snapshot",
            }

    def get_realtime_quotes(self, codes: list[str], kind: str = "auto") -> list[dict[str, Any]]:
        requests = [self._resolve_quote_symbol(code, kind) for code in codes]
        symbols = [item[0] for item in requests]
        quote_map = self._fetch_symbol_quote_map(symbols)
        items: list[dict[str, Any]] = []
        for input_code, (symbol, raw_code) in zip(codes, requests):
            fields = quote_map.get(symbol)
            if not fields:
                continue
            metrics = self._extract_quote_metrics(fields)
            item_kind = "index" if symbol in INDEX_SYMBOLS or raw_code in INDEX_CODE_SYMBOLS else ("etf" if raw_code.startswith(("5", "1")) and "ETF" in fields[1].upper() else "stock")
            items.append(
                {
                    "input": input_code,
                    "symbol": symbol,
                    "code": raw_code,
                    "name": fields[1] if len(fields) > 1 else "",
                    "kind": item_kind,
                    "price": self._to_float(fields[3] if len(fields) > 3 else ""),
                    "last_close": self._to_float(fields[4] if len(fields) > 4 else ""),
                    "open": self._to_float(fields[5] if len(fields) > 5 else ""),
                    **metrics,
                }
            )
        return items

    def get_price_bars(self, stock_code: str, frequency: int = 4, limit: int = 20) -> list[dict[str, Any]]:
        client = self._get_mootdx_client()
        try:
            payload = client.bars(symbol=stock_code, frequency=frequency, offset=limit)
        except Exception as exc:
            raise OnlineDataError(f"mootdx bars failed: {exc}") from exc
        rows = self._normalize_mootdx_payload(payload)
        if not rows:
            raise OnlineDataError("mootdx bars returned empty data")
        return rows

    def get_order_book(self, stock_code: str) -> dict[str, Any]:
        client = self._get_mootdx_client()
        try:
            payload = client.quotes(symbol=[stock_code])
        except Exception as exc:
            raise OnlineDataError(f"mootdx quotes failed: {exc}") from exc
        rows = self._normalize_mootdx_payload(payload)
        if not rows:
            raise OnlineDataError("mootdx quotes returned empty data")
        row = rows[0]
        return {
            "code": row.get("code", stock_code),
            "price": row.get("price", 0),
            "last_close": row.get("last_close", 0),
            "open": row.get("open", 0),
            "high": row.get("high", 0),
            "low": row.get("low", 0),
            "servertime": row.get("servertime", ""),
            "vol": row.get("vol", 0),
            "amount": row.get("amount", 0),
            "bids": [
                {"level": level, "price": row.get(f"bid{level}", 0), "volume": row.get(f"bid_vol{level}", 0)}
                for level in range(1, 6)
            ],
            "asks": [
                {"level": level, "price": row.get(f"ask{level}", 0), "volume": row.get(f"ask_vol{level}", 0)}
                for level in range(1, 6)
            ],
        }

    def get_transactions(self, stock_code: str, start: int = 0, limit: int = 50) -> list[dict[str, Any]]:
        client = self._get_mootdx_client()
        try:
            payload = client.transaction(symbol=stock_code, start=start, offset=limit)
        except Exception as exc:
            raise OnlineDataError(f"mootdx transactions failed: {exc}") from exc
        rows = self._normalize_mootdx_payload(payload)
        if not rows:
            return []
        return rows

    def get_financial_snapshot(self, stock_code: str) -> dict[str, Any]:
        client = self._get_mootdx_client()
        try:
            payload = client.finance(symbol=stock_code)
        except Exception as exc:
            raise OnlineDataError(f"mootdx finance snapshot failed: {exc}") from exc
        rows = self._normalize_mootdx_payload(payload)
        payload = rows[0] if rows else {}
        if not isinstance(payload, dict) or not payload:
            raise OnlineDataError("mootdx finance snapshot returned empty data")
        data = {str(key): value for key, value in payload.items()}
        data["code"] = stock_code
        if "name" not in data:
            try:
                data["name"] = self.get_stock_snapshot(stock_code).name
            except Exception:
                data["name"] = ""
        return data

    def get_f10_profile(self, stock_code: str, category: str | None = None) -> dict[str, str]:
        client = self._get_mootdx_client()
        categories = (category,) if category else F10_CATEGORIES
        results: dict[str, str] = {}
        for item in categories:
            try:
                text = client.F10(symbol=stock_code, name=item)
            except Exception as exc:
                raise OnlineDataError(f"mootdx F10 failed for {item}: {exc}") from exc
            if text:
                results[item] = self._optimize_f10_text(item, str(text))
            else:
                results[item] = ""
        return results

    def get_financial_report(
        self,
        stock_code: str,
        report_type: str = "lrb",
        page_size: int = 20,
    ) -> list[dict[str, Any]]:
        prefix = "sh" if stock_code.startswith(("5", "6", "9")) else "sz"
        payload = self._http_get_json(
            "https://quotes.sina.cn/cn/api/openapi.php/CompanyFinanceService.getFinanceReport2022?"
            + urlencode(
                {
                    "paperCode": f"{prefix}{stock_code}",
                    "source": report_type,
                    "type": "0",
                    "page": "1",
                    "num": str(page_size),
                }
            )
        )
        data = payload.get("result", {}).get("data", {}) or {}
        rows = data.get(report_type)
        if isinstance(rows, list) and rows:
            return rows
        report_list = data.get("report_list", {}) or {}
        normalized = []
        for report_date, report_payload in report_list.items():
            row: dict[str, Any] = {
                "报告日": (
                    f"{report_date[:4]}-{report_date[4:6]}-{report_date[6:8]}"
                    if len(report_date) == 8 and report_date.isdigit()
                    else report_date
                )
            }
            for item in report_payload.get("data", []) or []:
                title = item.get("item_title", "")
                if title:
                    row[title] = item.get("item_value")
            normalized.append(row)
        return normalized

    def get_consensus_eps(self, stock_code: str) -> list[dict[str, Any]]:
        html_text = self._http_get_text(
            f"https://basic.10jqka.com.cn/new/{stock_code}/worth.html",
            encoding="gbk",
        )
        return self._parse_consensus_table(html_text)

    def iwencai_search(
        self,
        query: str,
        channel: str = "report",
        size: int = 50,
    ) -> list[dict[str, Any]]:
        payload = self._http_post_json(
            f"{self.config.iwencai_base_url}/v1/comprehensive/search",
            payload={
                "channels": [channel],
                "app_id": "AIME_SKILL",
                "query": query,
                "size": size,
            },
            headers={
                "Authorization": f"Bearer {self.config.iwencai_api_key}",
                **self._claw_headers(),
            },
        )
        if payload.get("status_code", 0) != 0:
            raise OnlineDataError(payload.get("status_msg", "iwencai search failed"))
        rows = payload.get("data") or []
        return self._dedup_iwencai_articles(rows)

    def iwencai_query(
        self,
        query: str,
        page: int = 1,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        payload = self._http_post_json(
            f"{self.config.iwencai_base_url}/v1/query2data",
            payload={
                "query": query,
                "page": str(page),
                "limit": str(limit),
                "is_cache": "1",
                "expand_index": "true",
            },
            headers={
                "Authorization": f"Bearer {self.config.iwencai_api_key}",
                **self._claw_headers(),
            },
        )
        if payload.get("status_code", 0) != 0:
            raise OnlineDataError(payload.get("status_msg", "iwencai query failed"))
        return payload.get("datas") or []
