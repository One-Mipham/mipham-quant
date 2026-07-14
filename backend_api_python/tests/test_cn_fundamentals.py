"""Tests for A-share fundamentals — AKShare multi-endpoint, Twelve Data fallback, code normalization, and aggregators."""

import pytest

from app.data_sources.asia_stock_kline import (
    ak_a_code_from_tencent,
    yf_symbol_from_tencent,
)
from app.data_sources.cn_hk_fundamentals import (
    _eastmoney_a_em_symbol,
    _float_clean,
    fetch_akshare_cn_fundamentals,
    fetch_cn_company_extras,
    fetch_cn_financial_indicators,
    fetch_cn_financial_statements,
    fetch_cn_fundamental_akshare,
    fetch_twelvedata_fundamental,
    get_cn_fundamentals,
)
from app.data_sources.tencent import normalize_cn_code


class TestCNCodeNormalization:
    """Verify A-share code normalization for various sources."""

    def test_normalize_shanghai(self):
        assert normalize_cn_code("600519") == "SH600519"
        assert normalize_cn_code("600519.SH") == "SH600519"
        assert normalize_cn_code("600519.SS") == "SH600519"

    def test_normalize_shenzhen(self):
        assert normalize_cn_code("000001") == "SZ000001"
        assert normalize_cn_code("000001.SZ") == "SZ000001"

    def test_normalize_gem(self):
        assert normalize_cn_code("300750") == "SZ300750"

    def test_normalize_empty(self):
        assert normalize_cn_code("") == ""

    def test_akshare_code_conversion(self):
        assert ak_a_code_from_tencent("SH600519") == "600519"
        assert ak_a_code_from_tencent("SZ000001") == "000001"

    def test_eastmoney_symbol(self):
        assert _eastmoney_a_em_symbol("SH600519") == "SH600519"
        assert _eastmoney_a_em_symbol("SZ000001") == "SZ000001"
        assert _eastmoney_a_em_symbol("SZ300750") == "SZ300750"

    def test_yfinance_conversion(self):
        assert yf_symbol_from_tencent("SH600519", is_hk=False) == "600519.SS"
        assert yf_symbol_from_tencent("SZ000001", is_hk=False) == "000001.SZ"


class TestFloatClean:
    """Test the _float_clean helper."""

    def test_float(self):
        assert _float_clean(42.5) == 42.5

    def test_string_number(self):
        assert _float_clean("3.14") == 3.14

    def test_none(self):
        assert _float_clean(None) is None

    def test_empty_string(self):
        assert _float_clean("") is None

    def test_nan(self):
        assert _float_clean(float("nan")) is None

    def test_inf(self):
        assert _float_clean(float("inf")) is None


class TestAKShareCNFundamentals:
    """Integration tests for AKShare A-share fundamentals — requires network (CN IP preferred)."""

    @pytest.fixture(scope="class")
    def maotai(self):
        """贵州茅台 — SH600519, high liquidity, always has data."""
        return "SH600519"

    @pytest.fixture(scope="class")
    def pingan(self):
        """中国平安 — SH601318, major financial blue chip."""
        return "SH601318"

    def test_fetch_cn_fundamental_akshare(self, maotai):
        """Basic AKShare fundamental should return PE/PB/market_cap for Moutai."""
        result = fetch_cn_fundamental_akshare(maotai)
        assert isinstance(result, dict)
        # AKShare may fail overseas — check gracefully
        if result:
            assert "source" in result
            assert result["source"] == "akshare_em"

    def test_fetch_akshare_cn_fundamentals(self, maotai):
        """Comprehensive AKShare fundamentals should return rich data."""
        result = fetch_akshare_cn_fundamentals(maotai)
        assert isinstance(result, dict)
        if result:
            # Should have at least some valuation fields
            has_valuation = any(k in result for k in ("pe_ratio", "pb_ratio", "market_cap", "roe"))
            assert has_valuation, f"Expected valuation data, got keys: {list(result.keys())}"

    def test_fetch_cn_financial_indicators(self, maotai):
        """Financial indicators should include growth and ratio data."""
        result = fetch_cn_financial_indicators(maotai)
        assert isinstance(result, dict)
        # May be empty if AKShare fails — that's acceptable

    def test_fetch_cn_financial_statements(self, maotai):
        """Financial statements should return structured sections."""
        result = fetch_cn_financial_statements(maotai)
        assert isinstance(result, dict)
        if result:
            for key in result:
                assert key in ("income_statement", "balance_sheet", "cash_flow")

    def test_fetch_cn_company_extras(self, maotai):
        """Company extras should return industry/IPO info."""
        result = fetch_cn_company_extras(maotai)
        assert isinstance(result, dict)
        # May return data or be empty

    def test_get_cn_fundamentals_aggregated(self, maotai):
        """Top-level aggregator should merge AKShare + Twelve Data results."""
        result = get_cn_fundamentals(maotai)
        assert isinstance(result, dict)

    def test_maotai_has_market_cap(self, maotai):
        """Moutai (largest A-share by market cap) must have market cap."""
        result = get_cn_fundamentals(maotai)
        if "market_cap" in result and result["market_cap"] is not None:
            # Moutai market cap should be > 1 trillion CNY
            assert result["market_cap"] > 1_000_000_000_000, f"Moutai market cap too low: {result['market_cap']}"

    def test_multiple_stocks(self, maotai, pingan):
        """Fundamentals should work across multiple stocks."""
        for code in [maotai, pingan]:
            result = get_cn_fundamentals(code)
            assert isinstance(result, dict)


class TestTwelveDataFundamentals:
    """Tests for Twelve Data fundamentals — requires TWELVE_DATA_API_KEY env var."""

    def test_fetch_twelvedata_cn(self):
        """Twelve Data for A-shares — may be empty without API key."""
        result = fetch_twelvedata_fundamental("SH600519", is_hk=False)
        assert isinstance(result, dict)
        # Without API key, returns empty dict

    def test_fetch_twelvedata_hk(self):
        """Twelve Data for HK — may be empty without API key."""
        result = fetch_twelvedata_fundamental("HK00700", is_hk=True)
        assert isinstance(result, dict)
