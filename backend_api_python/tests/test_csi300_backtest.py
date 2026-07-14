"""CSI 300 full backtest validation — A-share pipeline from data source to trade simulation.

Validates the complete backtest pipeline for CSI 300 constituent stocks:
  1. K-line data fetching (Tencent fqkline)
  2. Indicator execution (SMA crossover strategy)
  3. Trade simulation (equity curve, trades, metrics)
  4. Multi-stock consistency

CSI 300 constituents tested (major blue chips):
  - SH600519 贵州茅台 (consumer staples)
  - SH600036 招商银行 (financials)
  - SZ000858 五粮液 (consumer staples)
  - SH601318 中国平安 (insurance)
  - SZ300750 宁德时代 (new energy)
"""

from datetime import datetime, timedelta

import pytest

from app.services.backtest import BacktestService

# Built-in A-share SMA crossover strategy — proven simple strategy for validation
SMA_CROSSOVER_CODE = r"""my_indicator_name = "CSI300 SMA Crossover Test"
my_indicator_description = "5/20 SMA crossover for CSI 300 backtest validation"

# @strategy stopLossPct 0.05
# @strategy takeProfitPct 0.15
# @strategy tradeDirection long

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
    'plots': [
        {'name': 'MA5', 'data': short_ma.tolist(), 'color': '#faad14', 'overlay': True},
        {'name': 'MA20', 'data': long_ma.tolist(), 'color': '#1677ff', 'overlay': True}
    ],
    'signals': [
        {'type': 'buy', 'text': 'B', 'data': buy_marks, 'color': '#00E676'},
        {'type': 'sell', 'text': 'S', 'data': sell_marks, 'color': '#FF5252'}
    ]
}
"""

# Top CSI 300 constituents by market cap
CSI300_STOCKS = [
    ("SH600519", "贵州茅台"),
    ("SH600036", "招商银行"),
    ("SH601318", "中国平安"),
    ("SZ000858", "五粮液"),
    ("SZ300750", "宁德时代"),
]


class TestBacktestDataPipeline:
    """Verify the A-share data pipeline feeds the backtest engine correctly."""

    @pytest.fixture(scope="class")
    def service(self):
        return BacktestService()

    def test_fetch_kline_cnstock_daily(self, service):
        """Daily kline for A-shares should return valid OHLCV DataFrame."""
        end = datetime.now()
        start = end - timedelta(days=365)
        df = service._fetch_kline_data("CNStock", "600519", "1D", start, end)
        assert df is not None
        assert not df.empty, "Should have at least some data for Moutai (1 year)"
        for col in ("open", "high", "low", "close", "volume"):
            assert col in df.columns, f"Missing column: {col}"
        assert len(df) >= 100, f"Expected >=100 trading days, got {len(df)}"
        assert df["close"].iloc[-1] > 0, "Last close should be positive"

    def test_fetch_kline_cnstock_weekly(self, service):
        """Weekly kline should work for A-shares."""
        end = datetime.now()
        start = end - timedelta(days=365 * 2)
        df = service._fetch_kline_data("CNStock", "600036", "1W", start, end)
        assert df is not None
        assert not df.empty
        assert len(df) >= 30, f"Expected >=30 weeks, got {len(df)}"

    def test_fetch_kline_date_range(self, service):
        """Kline should respect date range boundaries."""
        end = datetime.now()
        start = end - timedelta(days=90)  # 3 months
        df = service._fetch_kline_data("CNStock", "601318", "1D", start, end)
        assert df is not None
        if not df.empty and "time" in df.columns:
            # Verify timestamps are within range
            min_ts = df["time"].min()
            df["time"].max()
            # Allow some slack — data source may return slightly wider range
            assert min_ts >= (start - timedelta(days=7)).timestamp(), (
                f"Min time {min_ts} before start {start.timestamp()}"
            )


class TestCSI300Backtest:
    """Full end-to-end backtest validation for CSI 300 constituents."""

    @pytest.fixture(scope="class")
    def service(self):
        return BacktestService()

    @pytest.fixture(scope="class")
    def backtest_params(self):
        """Common backtest parameters."""
        end = datetime.now()
        start = end - timedelta(days=365)  # 1 year
        return {
            "market": "CNStock",
            "timeframe": "1D",
            "start_date": start,
            "end_date": end,
            "initial_capital": 100_000.0,  # 10万人民币
            "commission": 0.0003,  # 万三
            "slippage": 0.001,
            "leverage": 1,
            "trade_direction": "long",
        }

    def test_sma_crossover_maotai(self, service, backtest_params):
        """Full backtest on Moutai with SMA crossover."""
        result = service.run(
            indicator_code=SMA_CROSSOVER_CODE,
            symbol="600519",
            **backtest_params,
        )
        self._validate_backtest_result(result, "SH600519")

    def test_sma_crossover_cmb(self, service, backtest_params):
        """Full backtest on China Merchants Bank."""
        result = service.run(
            indicator_code=SMA_CROSSOVER_CODE,
            symbol="600036",
            **backtest_params,
        )
        self._validate_backtest_result(result, "SH600036")

    def test_sma_crossover_pingan(self, service, backtest_params):
        """Full backtest on Ping An Insurance."""
        result = service.run(
            indicator_code=SMA_CROSSOVER_CODE,
            symbol="601318",
            **backtest_params,
        )
        self._validate_backtest_result(result, "SH601318")

    def test_sma_crossover_wuliangye(self, service, backtest_params):
        """Full backtest on Wuliangye."""
        result = service.run(
            indicator_code=SMA_CROSSOVER_CODE,
            symbol="000858",
            **backtest_params,
        )
        self._validate_backtest_result(result, "SZ000858")

    def test_sma_crossover_catl(self, service, backtest_params):
        """Full backtest on CATL (宁德时代)."""
        result = service.run(
            indicator_code=SMA_CROSSOVER_CODE,
            symbol="300750",
            **backtest_params,
        )
        self._validate_backtest_result(result, "SZ300750")

    def test_all_csi300_stocks_produce_metrics(self, service, backtest_params):
        """Every CSI 300 test stock should produce valid metrics."""
        results = {}
        for code, name in CSI300_STOCKS:
            result = service.run(
                indicator_code=SMA_CROSSOVER_CODE,
                symbol=code[2:],  # strip SH/SZ prefix
                **backtest_params,
            )
            results[name] = result
            assert "annualReturn" in result, f"{name}: missing annualReturn"
            assert "equityCurve" in result, f"{name}: missing equityCurve"

        # At least one stock should have trades (SMA crossover triggered)
        stocks_with_trades = [name for name, r in results.items() if r.get("totalTrades", 0) > 0]
        assert len(stocks_with_trades) >= 1, (
            f"No CSI 300 stock produced trades! Trades: { {k: r.get('totalTrades', 0) for k, r in results.items()} }"
        )

    # ── Validation helpers ──

    @staticmethod
    def _validate_backtest_result(result: dict, label: str):
        """Comprehensive validation of a backtest result dict.

        The backtest result uses flat keys (not nested 'metrics' sub-dict):
          - annualReturn, maxDrawdown, totalTrades, winRate, sharpeRatio
          - equityCurve: [{time, value}, ...]
          - trades: [{time, type, price, ...}, ...]
          - executionAssumptions: metadata
        """
        assert isinstance(result, dict), f"{label}: result should be dict"

        # Core metrics — flat keys
        assert "annualReturn" in result, f"{label}: missing annualReturn"
        assert "maxDrawdown" in result, f"{label}: missing maxDrawdown"

        # Return is in percentage form: -17.13 means -17.13%
        annual_return = result.get("annualReturn", 0)
        assert isinstance(annual_return, (int, float)), (
            f"{label}: annualReturn should be numeric, got {type(annual_return)}"
        )
        assert -100.0 <= annual_return <= 1000.0, f"{label}: annualReturn {annual_return}% unreasonable"

        # Max drawdown is in percentage form: -21.44 means -21.44%
        mdd = abs(result.get("maxDrawdown", 0))
        assert 0 <= mdd <= 100.0, f"{label}: maxDrawdown {mdd}% outside [0%, 100%]"

        # Win rate: 0.0-1.0 (decimal) or 0-100 (percentage)
        total_trades = result.get("totalTrades", 0)
        if total_trades > 0:
            wr = result.get("winRate", 0)
            # Accept both decimal (0-1) and percentage (0-100) formats
            if wr > 1.0:
                wr = wr / 100.0
            assert 0 <= wr <= 1.0, f"{label}: winRate {wr} outside [0, 1]"

        # Equity curve
        equity = result.get("equityCurve", [])
        assert isinstance(equity, list), f"{label}: equityCurve should be list"
        if equity:
            assert len(equity) >= 2, f"{label}: equityCurve too short ({len(equity)} points)"
            for pt in equity[:3]:
                assert "time" in pt and "value" in pt

        # Trades list
        trades = result.get("trades", [])
        assert isinstance(trades, list), f"{label}: trades should be list"

        # Execution metadata
        exec_info = result.get("executionAssumptions", {})
        assert "engineVersion" in exec_info or "actualDataRange" in exec_info, f"{label}: missing execution metadata"


class TestBacktestEdgeCases:
    """Edge case handling for A-share backtests."""

    @pytest.fixture(scope="class")
    def service(self):
        return BacktestService()

    def test_empty_date_range_raises(self, service):
        """Backtest with future date range should raise ValueError."""
        future = datetime.now() + timedelta(days=30)
        future_end = future + timedelta(days=90)
        with pytest.raises(ValueError, match="No candle data"):
            service.run(
                indicator_code=SMA_CROSSOVER_CODE,
                market="CNStock",
                symbol="600519",
                timeframe="1D",
                start_date=future,
                end_date=future_end,
            )

    def test_invalid_symbol_raises(self, service):
        """Completely invalid symbol should raise ValueError."""
        end = datetime.now()
        start = end - timedelta(days=365)
        with pytest.raises(ValueError, match="No candle data"):
            service.run(
                indicator_code=SMA_CROSSOVER_CODE,
                market="CNStock",
                symbol="INVALID",
                timeframe="1D",
                start_date=start,
                end_date=end,
            )

    def test_short_date_range(self, service):
        """Very short date range (30 days) should still work."""
        end = datetime.now()
        start = end - timedelta(days=30)
        result = service.run(
            indicator_code=SMA_CROSSOVER_CODE,
            market="CNStock",
            symbol="600519",
            timeframe="1D",
            start_date=start,
            end_date=end,
        )
        assert "annualReturn" in result, "Short range: missing annualReturn"
