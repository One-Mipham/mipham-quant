# Mipham Quant — User Guide / 用户指南 v0.1.0

## Quick Start / 快速开始

1. Install Docker Desktop: https://www.docker.com/products/docker-desktop/
2. Run: `./start.sh`
3. Open: http://localhost:8888
4. Login: `mipham` / `mipham2026`

---

## Core Workflows / 核心工作流

### 1. View Market Data / 查看行情

Navigate to **Market** in the sidebar. Search for symbols:

| Market | Format | Examples |
|--------|--------|----------|
| A-Share (SSE) | `XXXXXX.SH` | `600519.SH` (贵州茅台) |
| A-Share (SZSE) | `XXXXXX.SZ` | `000001.SZ` (平安银行) |
| HK Stock | `XXXXX.HK` | `00700.HK` (腾讯控股) |
| Crypto | `BTC/USDT` | Via CCXT |

### 2. Write a Strategy / 编写策略

Navigate to **Indicator IDE** → **New Indicator**. Write Python code:

```python
my_indicator_name = "My First Strategy"
df = df.copy()
# Buy when price crosses above 20-day MA
df['buy'] = df['close'] > df['close'].rolling(20).mean()
output = {'name': my_indicator_name}
```

Use `# @strategy` comments to configure risk parameters:

```python
# @strategy stopLossPct 0.05    # 5% stop loss
# @strategy takeProfitPct 0.15  # 15% take profit
# @strategy tradeDirection long # Long only
```

### 3. Run Backtest / 运行回测

In the Indicator IDE:
1. Select market, symbol, and date range
2. Click **Run Backtest**
3. Review metrics: Total Return, Sharpe Ratio, Max Drawdown, Win Rate

**Engine selection**: Set `BACKTEST_ENGINE=polars` (fast) or `pandas` (full features) in `.env`.

### 4. Factor Screening / 因子选股

Use the Factor Engine API:

```python
from app.services.factor_engine import FactorEngine

engine = FactorEngine()

# Single stock score
result = engine.score_stock('600519.SH')

# Rank a universe of stocks
ranked = engine.rank_universe(
    ['600519.SH', '000858.SZ', '601318.SH', '600036.SH', '000333.SZ'],
    top_n=10
)
```

### 5. AI-Assisted Analysis / AI 辅助分析

- **Fast Analysis**: Click "AI Analysis" on any chart for instant technical analysis
- **AI Chat**: Use the AI Chat panel for market questions and strategy ideas
- **Strategy Generation**: Describe your strategy in natural language in the Strategy Generator

---

## FAQ / 常见问题

**Q: No data for A-shares? / A股没有数据？**

AKShare requires access to Eastmoney servers. From outside China, use a VPN or set `TWELVE_DATA_API_KEY` in `.env`. The system automatically falls back to Tencent fqkline for A-shares.

**Q: Backtest returns 0 trades? / 回测没有交易？**

Ensure your indicator code sets `df['buy']` and `df['sell']` columns as boolean arrays. Check that `tradeDirection` matches your signal logic.

**Q: Port conflicts? / 端口冲突？**

Port 5000 may be used by macOS AirPlay Receiver. The backend is mapped to port 5010. Update `BACKEND_PORT` in `.env` if needed.

**Q: How to add more data sources? / 如何添加更多数据源？**

Edit `backend_api_python/app/config/data_sources.py` to register new sources. Implement the `BaseDataSource` interface in `app/data_sources/`.

---

## Support / 技术支持

- Product Manual: [PRODUCT_MANUAL.md](./PRODUCT_MANUAL.md)
- Development Guide: [../DEVELOPMENT.md](../DEVELOPMENT.md)
- Email: support@onemipham.com
- Website: https://www.onemipham.com
