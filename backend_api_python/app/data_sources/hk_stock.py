"""
港股/H股数据源 — 多层 fallback

有 TWELVE_DATA_API_KEY:
  所有周期 → Twelve Data（主） → futu-api → 腾讯日/周线 → AkShare HK → yfinance → AkShare minute/weekly

无 API Key:
  日/周线 → futu-api → 腾讯 fqkline → AkShare HK → yfinance → AkShare minute/weekly
  分钟/小时 → yfinance → AkShare minute
"""

from __future__ import annotations

from typing import Any

from app.data_sources.asia_stock_kline import (
    _ts_to_date_str,
    fetch_akshare_hk_klines,
    fetch_akshare_minute_klines,
    fetch_akshare_weekly_klines,
    fetch_futu_hk_klines,
    fetch_twelvedata_klines,
    fetch_yfinance_klines,
    normalize_chart_timeframe,
)
from app.data_sources.base import BaseDataSource
from app.data_sources.tencent import (
    fetch_kline,
    fetch_quote,
    normalize_hk_code,
    parse_quote_to_ticker,
    tencent_kline_rows_to_dicts,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)


class HKStockDataSource(BaseDataSource):
    """港股/H股数据源（TwelveData + futu-api + Tencent + AkShare + yfinance） — 6 层 fallback"""

    name = "HKStock/multi-source"

    def get_ticker(self, symbol: str) -> dict[str, Any]:
        code = normalize_hk_code(symbol)
        parts = fetch_quote(code)
        if not parts:
            return {"last": 0, "symbol": code}
        t = parse_quote_to_ticker(parts)
        return {
            "last": t.get("last", 0),
            "change": t.get("change", 0),
            "changePercent": t.get("changePercent", 0),
            "high": t.get("high", 0),
            "low": t.get("low", 0),
            "open": t.get("open", 0),
            "previousClose": t.get("previousClose", 0),
            "name": t.get("name", ""),
            "symbol": code,
        }

    def get_kline(
        self,
        symbol: str,
        timeframe: str,
        limit: int,
        before_time: int | None = None,
        after_time: int | None = None,
    ) -> list[dict[str, Any]]:
        code = normalize_hk_code(symbol)
        tf = normalize_chart_timeframe(timeframe)
        lim = max(int(limit or 300), 1)

        # Tier 1: Twelve Data (paid, most reliable, all timeframes)
        rows = fetch_twelvedata_klines(
            is_hk=True,
            tencent_code=code,
            timeframe=tf,
            limit=lim,
            before_time=before_time,
        )
        if rows:
            return self.filter_and_limit(
                rows,
                limit=lim,
                before_time=before_time,
                after_time=after_time,
                truncate=(after_time is None),
            )

        # --- Daily / Weekly tiers ---
        if tf in ("1D", "1W"):
            # Tier 2: futu-api (best free quality, real-time capable, requires FutuOpenD)
            rows = fetch_futu_hk_klines(
                code,
                timeframe=tf,
                start_date=_ts_to_date_str(after_time),
                end_date=_ts_to_date_str(before_time),
                limit=lim,
            )
            if rows:
                return self.filter_and_limit(
                    rows,
                    limit=lim,
                    before_time=before_time,
                    after_time=after_time,
                    truncate=(after_time is None),
                )

            # Tier 3: Tencent fqkline (fast, free, no API key needed)
            tf_map = {"1D": "day", "1W": "week"}
            period = tf_map.get(tf, "day")
            raw_rows = fetch_kline(code, period=period, count=lim, adj="qfq")
            out = tencent_kline_rows_to_dicts(raw_rows)
            if out:
                return self.filter_and_limit(
                    out,
                    limit=lim,
                    before_time=before_time,
                    after_time=after_time,
                    truncate=(after_time is None),
                )

            # Tier 4: AKShare HK daily/weekly (Eastmoney, good quality, requires CN IP)
            rows = fetch_akshare_hk_klines(
                code,
                timeframe=tf,
                start=after_time,
                end=before_time,
                limit=lim,
            )
            if rows:
                return self.filter_and_limit(
                    rows,
                    limit=lim,
                    before_time=before_time,
                    after_time=after_time,
                    truncate=(after_time is None),
                )

        # Tier 5: yfinance (globally accessible, no API key needed, all timeframes)
        rows = fetch_yfinance_klines(
            is_hk=True,
            tencent_code=code,
            timeframe=tf,
            limit=lim,
            before_time=before_time,
        )
        if rows:
            return self.filter_and_limit(
                rows,
                limit=lim,
                before_time=before_time,
                after_time=after_time,
                truncate=(after_time is None),
            )

        # Tier 6: AkShare minute/weekly (fragile overseas, last resort)
        if tf in ("1m", "5m", "15m", "30m", "1H", "4H"):
            rows = fetch_akshare_minute_klines(
                is_hk=True,
                tencent_code=code,
                timeframe=tf,
                limit=lim,
                before_time=before_time,
            )
        elif tf == "1W":
            rows = fetch_akshare_weekly_klines(is_hk=True, tencent_code=code, limit=lim, before_time=before_time)
        else:
            rows = []

        return self.filter_and_limit(
            rows,
            limit=lim,
            before_time=before_time,
            after_time=after_time,
            truncate=(after_time is None),
        )
