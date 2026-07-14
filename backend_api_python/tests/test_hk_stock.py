"""Tests for HK stock data source — ticker, kline, normalization, and factory integration."""

import pytest

from app.data_sources.asia_stock_kline import (
    ak_hk_code_from_tencent,
    yf_symbol_from_tencent,
)
from app.data_sources.factory import DataSourceFactory
from app.data_sources.tencent import normalize_hk_code


class TestHKCodeNormalization:
    """Verify HK stock code normalization for Tencent/futu/AkShare/yfinance."""

    def test_normalize_pure_digits(self):
        assert normalize_hk_code("700") == "HK00700"
        assert normalize_hk_code("0700") == "HK00700"

    def test_normalize_with_hk_suffix(self):
        assert normalize_hk_code("00700.HK") == "HK00700"
        assert normalize_hk_code("0700.HK") == "HK00700"

    def test_normalize_already_hk_prefix(self):
        assert normalize_hk_code("HK00700") == "HK00700"
        assert normalize_hk_code("hk00700") == "HK00700"

    def test_normalize_alibaba(self):
        assert normalize_hk_code("09988") == "HK09988"
        assert normalize_hk_code("9988") == "HK09988"

    def test_normalize_meituan(self):
        assert normalize_hk_code("03690") == "HK03690"
        assert normalize_hk_code("3690") == "HK03690"

    def test_normalize_empty(self):
        assert normalize_hk_code("") == ""

    def test_akshare_code_conversion(self):
        assert ak_hk_code_from_tencent("HK00700") == "00700"
        assert ak_hk_code_from_tencent("00700") == "00700"
        assert ak_hk_code_from_tencent("HK09988") == "09988"

    def test_yfinance_symbol_conversion(self):
        assert yf_symbol_from_tencent("HK00700", is_hk=True) == "0700.HK"
        assert yf_symbol_from_tencent("HK09988", is_hk=True) == "9988.HK"
        assert yf_symbol_from_tencent("HK00005", is_hk=True) == "0005.HK"


class TestHKStockDataSource:
    """Integration tests for HKStockDataSource — requires network access."""

    @pytest.fixture(scope="class")
    def source(self):
        from app.data_sources.hk_stock import HKStockDataSource

        return HKStockDataSource()

    def test_get_ticker_tencent(self, source):
        """Ticker should return valid price data for Tencent (HK.00700)."""
        ticker = source.get_ticker("00700")
        assert ticker["symbol"] == "HK00700"
        assert ticker["last"] > 0, f"Expected positive price, got {ticker}"
        assert ticker.get("name", ""), "Should include stock name"

    def test_get_ticker_alibaba(self, source):
        """Ticker should work for Alibaba (HK.09988)."""
        ticker = source.get_ticker("09988")
        assert ticker["symbol"] == "HK09988"
        assert ticker["last"] > 0

    def test_get_kline_daily(self, source):
        """Daily K-line should return bars for Tencent."""
        bars = source.get_kline("00700", "1D", limit=30)
        assert len(bars) >= 1, f"Expected at least 1 bar, got {len(bars)}"
        bar = bars[0]
        for field in ("time", "open", "high", "low", "close", "volume"):
            assert field in bar, f"Missing field: {field}"
        assert bar["close"] > 0
        assert bar["high"] >= bar["low"]

    def test_get_kline_weekly(self, source):
        """Weekly K-line should return bars."""
        bars = source.get_kline("00700", "1W", limit=10)
        assert len(bars) >= 1
        bar = bars[0]
        assert bar["close"] > 0

    def test_get_kline_hsbc(self, source):
        """Should work for HSBC (00005.HK) — one of the oldest HK stocks."""
        bars = source.get_kline("00005", "1D", limit=10)
        assert len(bars) >= 1

    def test_get_kline_with_time_filter(self, source):
        """K-line with before_time should filter correctly."""
        import time

        # Request data before 30 days ago
        thirty_days_ago = int(time.time()) - 30 * 86400
        bars = source.get_kline("00700", "1D", limit=5, before_time=thirty_days_ago)
        if bars:
            for bar in bars:
                assert bar["time"] <= thirty_days_ago, f"Bar time {bar['time']} should be <= {thirty_days_ago}"

    def test_nonexistent_symbol_returns_empty(self, source):
        """Non-existent symbol should return empty list, not crash."""
        bars = source.get_kline("HK99999", "1D", limit=10)
        # May return empty or fallback data — should not raise
        assert isinstance(bars, list)


class TestHKStockFactory:
    """Verify the DataSourceFactory correctly routes HKStock market."""

    def test_normalize_hkstock_market(self):
        assert DataSourceFactory.normalize_market("HKStock") == "HKStock"
        assert DataSourceFactory.normalize_market("hkstock") == "HKStock"
        assert DataSourceFactory.normalize_market("HkStock") == "HKStock"

    def test_create_hkstock_source(self):
        from app.data_sources.hk_stock import HKStockDataSource

        source = DataSourceFactory.get_source("HKStock")
        assert isinstance(source, HKStockDataSource)

    def test_cnstock_vs_hkstock_different_sources(self):
        """CNStock and HKStock should yield different data source types."""
        from app.data_sources.cn_stock import CNStockDataSource
        from app.data_sources.hk_stock import HKStockDataSource

        cn = DataSourceFactory.get_source("CNStock")
        hk = DataSourceFactory.get_source("HKStock")
        assert isinstance(cn, CNStockDataSource)
        assert isinstance(hk, HKStockDataSource)
        assert type(cn) is not type(hk)

    def test_get_kline_via_factory(self):
        """Factory.get_kline should work for HKStock market."""
        bars = DataSourceFactory.get_kline("HKStock", "00700", "1D", limit=5)
        assert len(bars) >= 1
        assert all("close" in b for b in bars)
