#!/usr/bin/env python3
"""
CSI 300 full backtest validation.
Tests: data completeness, backtest execution, performance metrics.

Usage:
    docker exec mipham-quant-backend python3 /app/../scripts/validate_csi300.py
"""

import os
import sys
import json
import time
from datetime import datetime

# Ensure backend modules are importable when run from project root
_BACKEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'backend_api_python')
if os.path.isdir(_BACKEND_DIR):
    sys.path.insert(0, _BACKEND_DIR)

# CSI 300 constituent sample (top 20 by weight)
CSI300_SAMPLE = [
    '600519.SH',  # 贵州茅台
    '000858.SZ',  # 五粮液
    '601318.SH',  # 中国平安
    '600036.SH',  # 招商银行
    '000333.SZ',  # 美的集团
    '600276.SH',  # 恒瑞医药
    '000651.SZ',  # 格力电器
    '601166.SH',  # 兴业银行
    '600900.SH',  # 长江电力
    '002415.SZ',  # 海康威视
    '600030.SH',  # 中信证券
    '000002.SZ',  # 万科A
    '601398.SH',  # 工商银行
    '600887.SH',  # 伊利股份
    '000568.SZ',  # 泸州老窖
    '601888.SH',  # 中国中免
    '002714.SZ',  # 牧原股份
    '600809.SH',  # 山西汾酒
    '000725.SZ',  # 京东方A
    '603259.SH',  # 药明康德
]


def test_data_completeness():
    """Verify all CSI 300 sample stocks return valid kline data."""
    from app.data_sources import DataSourceFactory

    results = {}
    print("  Symbol        Bars   Status")
    print("  ------------  -----  ------")
    for symbol in CSI300_SAMPLE:
        try:
            data = DataSourceFactory.get_kline(
                market='CNStock',
                symbol=symbol,
                timeframe='1D',
                limit=100,
            )
            count = len(data) if data else 0
            results[symbol] = count
            status = '✅' if count > 50 else '⚠️' if count > 0 else '❌'
            print(f"  {symbol:12s}  {count:5d}  {status}")
        except Exception as e:
            results[symbol] = 0
            print(f"  {symbol:12s}  {0:5d}  ❌ {e!s:.60s}")

    success = sum(1 for v in results.values() if v > 50)
    total = len(CSI300_SAMPLE)
    pct = success / total * 100 if total else 0
    print(f"\n  Summary: {success}/{total} stocks have >50 bars ({pct:.0f}%)")
    return success >= 15  # At least 75% pass


def test_simple_backtest():
    """Run a dual-MA backtest on 平安银行 (000001.SZ)."""
    from app.services.backtest import BacktestService

    bt = BacktestService()

    indicator_code = '''
my_indicator_name = "双均线交叉"
my_indicator_description = "SMA 5/20 交叉策略"

df = df.copy()
sma_short = df['close'].rolling(5).mean()
sma_long = df['close'].rolling(20).mean()
buy = (sma_short > sma_long) & (sma_short.shift(1) <= sma_long.shift(1))
sell = (sma_short < sma_long) & (sma_short.shift(1) >= sma_long.shift(1))
df['buy'] = buy.fillna(False).astype(bool)
df['sell'] = sell.fillna(False).astype(bool)

output = {
    'name': my_indicator_name,
    'plots': [{'name': 'SMA5', 'data': sma_short.tolist(), 'color': '#faad14', 'overlay': True},
              {'name': 'SMA20', 'data': sma_long.tolist(), 'color': '#1677ff', 'overlay': True}]
}
'''

    try:
        result = bt.run(
            indicator_code=indicator_code,
            market='CNStock',
            symbol='000001.SZ',
            timeframe='1D',
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 12, 31),
            initial_capital=100000,
            commission=0.0003,
            slippage=0.001,
            trade_direction='long',
        )

        trades = result.get('trades', [])
        if trades is not None and len(trades) > 0:
            n_trades = len(trades)
            real_trades = result.get('totalTrades', n_trades // 2)
            print(f"  ✅ Backtest OK: {real_trades} round-trip trades ({n_trades} actions)")
            # Metrics are at result top-level, not nested
            total_ret = result.get('totalReturn', 0)
            sharpe = result.get('sharpeRatio', 0)
            max_dd = result.get('maxDrawdown', 0)
            win_rate = result.get('winRate', 0)
            profit = result.get('totalProfit', 0)
            profit_factor = result.get('profitFactor', 0)
            try:
                print(f"     Total Return: {float(total_ret):.2%}")
            except (ValueError, TypeError):
                print(f"     Total Return: {total_ret}")
            try:
                print(f"     Sharpe: {float(sharpe):.2f}")
            except (ValueError, TypeError):
                print(f"     Sharpe: {sharpe}")
            try:
                print(f"     Max DD: {float(max_dd):.2%}")
            except (ValueError, TypeError):
                print(f"     Max DD: {max_dd}")
            try:
                print(f"     Win Rate: {float(win_rate):.1f}%")
            except (ValueError, TypeError):
                print(f"     Win Rate: {win_rate}")
            try:
                print(f"     Profit: ¥{float(profit):.2f}")
            except (ValueError, TypeError):
                print(f"     Profit: {profit}")
            try:
                print(f"     Profit Factor: {float(profit_factor):.2f}")
            except (ValueError, TypeError):
                print(f"     Profit Factor: {profit_factor}")
            return True
        else:
            print(f"  ❌ Backtest produced no trades: {result.get('error', str(result)[:200])}")
            return False

    except Exception as e:
        print(f"  ❌ Backtest error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    print("=" * 54)
    print("Mipham Quant — CSI 300 Validation")
    print("=" * 54)

    print("\n1. Data Completeness (CSI 300 top 20):")
    data_ok = test_data_completeness()

    print("\n2. Backtest (000001.SZ 双均线 2024):")
    bt_ok = test_simple_backtest()

    print("\n" + "=" * 54)
    if data_ok and bt_ok:
        print("✅ ALL CHECKS PASSED")
    else:
        parts = []
        if not data_ok:
            parts.append("data=❌")
        else:
            parts.append("data=✅")
        if not bt_ok:
            parts.append("backtest=❌")
        else:
            parts.append("backtest=✅")
        print(f"❌ ISSUES: {', '.join(parts)}")
    print("=" * 54)
