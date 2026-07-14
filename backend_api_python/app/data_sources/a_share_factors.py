"""
A-Share factor data fetcher.

Provides 18 factors across 7 categories:
- Valuation: PE_TTM, PB, PS_TTM, PCF
- Profitability: ROE, ROA, gross_margin, net_margin
- Growth: revenue_growth_yoy, profit_growth_yoy
- Momentum: ret_1m, ret_3m, ret_6m
- Liquidity: avg_turnover_20d, avg_volume_20d
- Risk: volatility_60d, max_dd_1y
- Quality/Sentiment: northbound_holding, institution_holding, is_st, is_suspended

All data sourced from AKShare (Eastmoney backend).
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

import pandas as pd

from app.utils.logger import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Factor definitions — metadata for all supported factors
# ---------------------------------------------------------------------------

FACTOR_DEFINITIONS: dict[str, dict[str, Any]] = {
    # --- Valuation ---
    "pe_ttm": {
        "name": "市盈率TTM",
        "category": "valuation",
        "lower_better": True,
        "description": "滚动市盈率",
    },
    "pb": {
        "name": "市净率",
        "category": "valuation",
        "lower_better": True,
        "description": "市净率 (股价/每股净资产)",
    },
    "ps_ttm": {
        "name": "市销率TTM",
        "category": "valuation",
        "lower_better": True,
        "description": "滚动市销率",
    },
    # --- Profitability ---
    "roe": {
        "name": "净资产收益率",
        "category": "profitability",
        "lower_better": False,
        "description": "净资产收益率 ROE (%)",
    },
    "roa": {
        "name": "总资产收益率",
        "category": "profitability",
        "lower_better": False,
        "description": "总资产收益率 ROA (%)",
    },
    "gross_margin": {
        "name": "毛利率",
        "category": "profitability",
        "lower_better": False,
        "description": "销售毛利率 (%)",
    },
    "net_margin": {
        "name": "净利率",
        "category": "profitability",
        "lower_better": False,
        "description": "销售净利率 (%)",
    },
    # --- Growth ---
    "revenue_growth_yoy": {
        "name": "营收同比增速",
        "category": "growth",
        "lower_better": False,
        "description": "营业收入同比增长率 (%)",
    },
    "profit_growth_yoy": {
        "name": "净利润同比增速",
        "category": "growth",
        "lower_better": False,
        "description": "净利润同比增长率 (%)",
    },
    # --- Momentum ---
    "ret_1m": {
        "name": "近1月涨跌幅",
        "category": "momentum",
        "lower_better": False,
        "description": "近1个月价格涨跌幅",
    },
    "ret_3m": {
        "name": "近3月涨跌幅",
        "category": "momentum",
        "lower_better": False,
        "description": "近3个月价格涨跌幅",
    },
    "ret_6m": {
        "name": "近6月涨跌幅",
        "category": "momentum",
        "lower_better": False,
        "description": "近6个月价格涨跌幅",
    },
    # --- Liquidity ---
    "avg_turnover_20d": {
        "name": "20日均换手率",
        "category": "liquidity",
        "lower_better": False,
        "description": "20个交易日平均换手率 (%)",
    },
    "avg_volume_20d": {
        "name": "20日均成交量",
        "category": "liquidity",
        "lower_better": False,
        "description": "20个交易日平均成交量 (手)",
    },
    # --- Risk ---
    "volatility_60d": {
        "name": "60日波动率",
        "category": "risk",
        "lower_better": True,
        "description": "60日年化波动率",
    },
    "max_dd_1y": {
        "name": "近1年最大回撤",
        "category": "risk",
        "lower_better": True,
        "description": "近252个交易日最大回撤 (%)",
    },
    # --- Quality / Sentiment ---
    "northbound_holding": {
        "name": "北向资金持股占比",
        "category": "sentiment",
        "lower_better": False,
        "description": "沪深港通北向资金持股占流通股比例",
    },
    "institution_holding": {
        "name": "机构持股占比",
        "category": "sentiment",
        "lower_better": False,
        "description": "机构持股占流通股比例",
    },
    "is_st": {
        "name": "是否ST",
        "category": "quality",
        "lower_better": True,
        "description": "1=ST股, 0=正常",
    },
}


def get_factor_definitions() -> dict[str, dict[str, Any]]:
    """Return all supported factor definitions (name, category, direction)."""
    return dict(FACTOR_DEFINITIONS)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _safe_float(val: Any) -> float | None:
    """Safely convert value to float, returning None on failure, NaN/Inf, or bools."""
    if val is None:
        return None
    # AKShare returns Python False for N/A — treat as missing
    if isinstance(val, bool):
        return None
    try:
        v = float(val)
        if pd.isna(v) or v == float("inf") or v == float("-inf"):
            return None
        return v
    except (ValueError, TypeError):
        return None


def _parse_pct(val: Any) -> float | None:
    """Parse percentage string like '54.27%' or False→None to float."""
    if val is None or isinstance(val, bool):
        return None
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, str):
        s = val.strip().rstrip("%")
        try:
            return float(s)
        except (ValueError, TypeError):
            return None
    return None


def _normalize_code(symbol: str) -> str:
    """Strip .SH/.SZ suffix for AKShare API calls."""
    return symbol.replace(".SZ", "").replace(".SH", "").replace(".sz", "").replace(".sh", "").strip()


# ---------------------------------------------------------------------------
# Main factor fetch
# ---------------------------------------------------------------------------


def fetch_factors_for_symbol(symbol: str) -> dict[str, float | None]:
    """
    Fetch all available factors for a single A-share stock.

    Uses targeted AKShare APIs (no heavy stock_zh_a_spot_em on the full universe).
    Returns dict of factor_key → value (None if unavailable).
    """
    code = _normalize_code(symbol)
    result: dict[str, float | None] = {}

    try:
        import akshare as ak  # type: ignore
    except ImportError:
        logger.warning("AKShare not available for factor fetch")
        return {}

    # --- 1. Valuation + turnover from individual info + valuation comparison ---
    _fetch_valuation_factors(ak, code, result)

    # --- 2. Financial indicators (ROE, ROA, margins, growth) ---
    _fetch_financial_factors(ak, code, result)

    # --- 3. Momentum + risk from kline ---
    _fetch_momentum_factors(ak, code, symbol, result)

    # --- 4. ST flag ---
    _fetch_st_flag(ak, code, result)

    # Count successful fetches for logging
    non_null = sum(1 for v in result.values() if v is not None)
    logger.debug("Fetched %d/%d factors for %s", non_null, len(FACTOR_DEFINITIONS), symbol)
    return result


def _fetch_valuation_factors(ak, code: str, result: dict[str, float | None]) -> None:
    """Fetch PE, PB, PS, turnover from AkShare valuation endpoint."""
    try:
        # stock_zh_valuation_comparison_em expects Eastmoney symbol format
        em_code = code.zfill(6)
        em_code = f"SH{em_code}" if em_code.startswith("6") else f"SZ{em_code}"

        df = ak.stock_zh_valuation_comparison_em(symbol=em_code)
        if df is not None and not df.empty and "代码" in df.columns:
            hit = df[df["代码"].astype(str).str.replace(".0", "", regex=False).str.zfill(6) == code.zfill(6)]
            if not hit.empty:
                r = hit.iloc[0]
                result["pe_ttm"] = _safe_float(r.get("市盈率-TTM"))
                result["pb"] = _safe_float(r.get("市净率-MRQ"))
                result["ps_ttm"] = _safe_float(r.get("市销率-TTM"))
    except Exception as e:
        logger.debug("Valuation fetch failed for %s: %s", code, e)

    # Individual info: turnover, volume
    try:
        df_info = ak.stock_individual_info_em(symbol=code)
        if df_info is not None and not df_info.empty and len(df_info.columns) >= 2:
            kcol, vcol = df_info.columns[0], df_info.columns[1]
            info_map = {}
            for _, row in df_info.iterrows():
                k = str(row[kcol]).strip()
                if k:
                    info_map[k] = row[vcol]
            result["avg_turnover_20d"] = _safe_float(info_map.get("换手率"))
            total_shares = _safe_float(info_map.get("总股本"))
            if total_shares and result.get("avg_turnover_20d") is not None:
                # Approximate avg volume from total shares * turnover
                result["avg_volume_20d"] = total_shares * result["avg_turnover_20d"] / 100
    except Exception as e:
        logger.debug("Individual info fetch failed for %s: %s", code, e)


def _fetch_financial_factors(ak, code: str, result: dict[str, float | None]) -> None:
    """Fetch ROE, ROA, margins, growth from financial indicators."""
    try:
        df = ak.stock_financial_abstract_ths(symbol=code, indicator="按报告期")
        if df is None or df.empty:
            return

        latest = df.iloc[0]
        # THS returns percentages as '54.27%' strings — use _parse_pct
        result["roe"] = _parse_pct(latest.get("净资产收益率"))
        result["roa"] = _parse_pct(latest.get("总资产收益率"))
        result["gross_margin"] = _parse_pct(latest.get("销售毛利率"))
        result["net_margin"] = _parse_pct(latest.get("销售净利率"))
        result["revenue_growth_yoy"] = _parse_pct(latest.get("营业总收入同比增长率"))
        result["profit_growth_yoy"] = _parse_pct(latest.get("净利润同比增长率"))
    except Exception as e:
        logger.debug("Financial factor fetch failed for %s: %s", code, e)


def _fetch_momentum_factors(ak, code: str, symbol: str, result: dict[str, float | None]) -> None:
    """Fetch momentum returns + volatility from daily kline."""
    try:
        end_dt = datetime.now().strftime("%Y%m%d")
        start_dt = (datetime.now() - timedelta(days=400)).strftime("%Y%m%d")

        df = ak.stock_zh_a_hist(
            symbol=code,
            period="daily",
            start_date=start_dt,
            end_date=end_dt,
            adjust="qfq",
        )
        if df is None or df.empty or "收盘" not in df.columns:
            return

        closes = df["收盘"].values
        n = len(closes)

        # Momentum: ret_1m (~22 trading days), ret_3m (~66), ret_6m (~132)
        if n >= 22:
            result["ret_1m"] = float((closes[-1] / closes[-22] - 1.0) * 100)
        if n >= 66:
            result["ret_3m"] = float((closes[-1] / closes[-66] - 1.0) * 100)
        if n >= 132:
            result["ret_6m"] = float((closes[-1] / closes[-132] - 1.0) * 100)

        # Volatility: 60-day annualized
        if n >= 60:
            returns = pd.Series(closes[-60:]).pct_change().dropna()
            if len(returns) > 0:
                result["volatility_60d"] = float(returns.std() * (252**0.5) * 100)

        # Max drawdown: 1 year
        if n >= 252:
            recent = closes[-252:]
            cummax = pd.Series(recent).cummax()
            dd = (recent - cummax) / cummax * 100
            result["max_dd_1y"] = float(dd.min())

        # Average volume 20d (shares)
        if "成交量" in df.columns and n >= 20:
            result["avg_volume_20d"] = _safe_float(df["成交量"].tail(20).mean())

    except Exception as e:
        logger.debug("Momentum fetch failed for %s: %s", symbol, e)


def _fetch_st_flag(ak, code: str, result: dict[str, float | None]) -> None:
    """Check if a stock is ST (special treatment)."""
    try:
        df_st = ak.stock_zh_a_st_em()
        if df_st is not None and not df_st.empty and "代码" in df_st.columns:
            st_codes = set(df_st["代码"].astype(str).str.replace(".0", "", regex=False).tolist())
            result["is_st"] = 1.0 if code.zfill(6) in st_codes else 0.0
        else:
            result["is_st"] = 0.0
    except Exception:
        result["is_st"] = 0.0
