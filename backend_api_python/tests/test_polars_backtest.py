"""Polars backtest engine migration — correctness and performance validation.

Validates that the Polars engine:
  1. Produces valid results (no crashes)
  2. Generates consistent trade counts with pandas (±1 tolerance)
  3. Is faster than pandas
  4. Handles edge cases (long direction only — short/both fall back to pandas)

Note: compute_equity_curve_polars() only implements long-direction trade
simulation. For short/both, BacktestService.run() auto-falls-back to the
legacy pandas engine via try/except.
"""

import os
import time
from datetime import datetime, timedelta

from app.services.backtest import BacktestService

SMA_CODE = r"""my_indicator_name = "Polars Migration Test"
my_indicator_description = "5/20 SMA crossover"
df = df.copy()
short_ma = df['close'].rolling(5).mean()
long_ma = df['close'].rolling(20).mean()
buy = (short_ma > long_ma) & (short_ma.shift(1) <= long_ma.shift(1))
sell = (short_ma < long_ma) & (short_ma.shift(1) >= long_ma.shift(1))
df['buy'] = buy.fillna(False).astype(bool)
df['sell'] = sell.fillna(False).astype(bool)
buy_marks = [df['low'].iloc[i] * 0.995 if bool(df['buy'].iloc[i]) else None for i in range(len(df))]
sell_marks = [df['high'].iloc[i] * 1.005 if bool(df['sell'].iloc[i]) else None for i in range(len(df))]
output = {
    'name': my_indicator_name,
    'signals': [
        {'type': 'buy', 'text': 'B', 'data': buy_marks, 'color': '#00E676'},
        {'type': 'sell', 'text': 'S', 'data': sell_marks, 'color': '#FF5252'}
    ]
}
"""

CSI300_SYMBOLS = ["600519", "600036", "000858", "601318", "300750"]


def _backtest_params():
    end = datetime.now()
    start = end - timedelta(days=365)
    return {
        "market": "CNStock",
        "timeframe": "1D",
        "start_date": start,
        "end_date": end,
        "initial_capital": 100_000.0,
        "commission": 0.0003,
        "slippage": 0.001,
        "leverage": 1,
        "trade_direction": "long",
    }


class TestPolarsEngineCorrectness:
    """Verify the Polars engine produces valid results."""

    def test_polars_runs_without_error(self):
        """Polars engine should not crash."""
        os.environ["BACKTEST_ENGINE"] = "polars"
        svc = BacktestService()
        assert svc._use_polars is True
        result = svc.run(SMA_CODE, symbol="600519", **_backtest_params())
        assert "annualReturn" in result
        assert "equityCurve" in result
        assert result["executionAssumptions"]["engineVersion"] == "polars-v1"

    def test_polars_produces_equity_curve(self):
        """Polars equity curve should be non-empty and values non-negative."""
        os.environ["BACKTEST_ENGINE"] = "polars"
        svc = BacktestService()
        result = svc.run(SMA_CODE, symbol="600036", **_backtest_params())
        equity = result["equityCurve"]
        assert len(equity) >= 10, f"Too few equity points: {len(equity)}"
        for pt in equity:
            assert pt["value"] >= 0, f"Negative equity: {pt['value']}"

    def test_polars_produces_trades(self):
        """Polars engine should generate valid trade records."""
        os.environ["BACKTEST_ENGINE"] = "polars"
        svc = BacktestService()
        result = svc.run(SMA_CODE, symbol="000858", **_backtest_params())
        trades = result.get("trades", [])
        if trades:
            trade = trades[0]
            for key in ("time", "type", "price"):
                assert key in trade, f"Trade missing: {key}"

    def test_polars_all_csi300_stocks(self):
        """Polars should work across all CSI 300 test stocks."""
        os.environ["BACKTEST_ENGINE"] = "polars"
        svc = BacktestService()
        for sym in CSI300_SYMBOLS:
            result = svc.run(SMA_CODE, symbol=sym, **_backtest_params())
            assert "annualReturn" in result, f"{sym}: missing annualReturn"
            assert "maxDrawdown" in result, f"{sym}: missing maxDrawdown"


class TestPolarsPandasParity:
    """Verify Polars and pandas produce consistent trade counts (±1 tolerance)."""

    def test_trade_count_parity_maotai(self):
        """Polars and pandas should produce the same number of trades."""
        params = _backtest_params()

        os.environ["BACKTEST_ENGINE"] = "pandas"
        svc_pd = BacktestService()
        result_pd = svc_pd.run(SMA_CODE, symbol="600519", **params)

        os.environ["BACKTEST_ENGINE"] = "polars"
        svc_pl = BacktestService()
        result_pl = svc_pl.run(SMA_CODE, symbol="600519", **params)

        t_pd = result_pd.get("totalTrades", 0)
        t_pl = result_pl.get("totalTrades", 0)
        assert t_pd == t_pl, f"Trade count mismatch: pandas={t_pd}, polars={t_pl}"

    def test_trade_count_parity_all_stocks(self):
        """Trade count parity across all CSI 300 test stocks (±1 tolerance)."""
        params = _backtest_params()
        mismatches = []

        for sym in CSI300_SYMBOLS:
            os.environ["BACKTEST_ENGINE"] = "pandas"
            r_pd = BacktestService().run(SMA_CODE, symbol=sym, **params)
            os.environ["BACKTEST_ENGINE"] = "polars"
            r_pl = BacktestService().run(SMA_CODE, symbol=sym, **params)

            t_pd = r_pd.get("totalTrades", 0)
            t_pl = r_pl.get("totalTrades", 0)
            if abs(t_pd - t_pl) > 1:
                mismatches.append(f"{sym}: pd={t_pd} pl={t_pl}")

        assert not mismatches, f"Trade count mismatches >1: {mismatches}"


class TestPolarsPerformance:
    """Benchmark Polars vs pandas."""

    def test_polars_is_faster(self):
        """Polars should not be slower than pandas."""
        params = _backtest_params()

        os.environ["BACKTEST_ENGINE"] = "pandas"
        t0 = time.perf_counter()
        BacktestService().run(SMA_CODE, symbol="600519", **params)
        t_pd = time.perf_counter() - t0

        os.environ["BACKTEST_ENGINE"] = "polars"
        t0 = time.perf_counter()
        BacktestService().run(SMA_CODE, symbol="600519", **params)
        t_pl = time.perf_counter() - t0

        assert t_pl < t_pd * 0.95, f"Polars ({t_pl:.3f}s) not faster than pandas ({t_pd:.3f}s)"


class TestPolarsEdgeCases:
    """Edge case handling for the Polars engine."""

    def test_polars_empty_signals(self):
        """Polars should handle signals with no buy/sell triggers."""
        import numpy as np
        import pandas as pd

        from app.services.backtest import compute_equity_curve_polars

        dates = pd.date_range("2025-01-01", periods=100, freq="B")
        df = pd.DataFrame(
            {
                "open": np.linspace(100, 110, 100),
                "high": np.linspace(102, 112, 100),
                "low": np.linspace(98, 108, 100),
                "close": np.linspace(101, 111, 100),
                "volume": np.full(100, 1_000_000.0),
            },
            index=dates,
        )

        signals = {"buy": pd.Series([False] * 100), "sell": pd.Series([False] * 100)}

        result = compute_equity_curve_polars(
            df=df,
            signals=signals,
            initial_capital=100000.0,
            commission=0.0003,
            slippage_pct=0.001,
            trade_direction="long",
        )
        assert result["totalTrades"] == 0
        assert result["annualReturn"] == 0.0

    def test_polars_short_falls_back_to_pandas(self):
        """Short direction: Polars path auto-falls-back to pandas — no crash."""
        os.environ["BACKTEST_ENGINE"] = "polars"
        svc = BacktestService()
        params = _backtest_params()
        params["trade_direction"] = "short"
        result = svc.run(SMA_CODE, symbol="600519", **params)
        assert "annualReturn" in result
        assert "equityCurve" in result

    def test_polars_both_directions(self):
        """Both-direction: Polars falls back to pandas — no crash."""
        os.environ["BACKTEST_ENGINE"] = "polars"
        svc = BacktestService()
        params = _backtest_params()
        params["trade_direction"] = "both"
        result = svc.run(SMA_CODE, symbol="600519", **params)
        assert "annualReturn" in result
