# Mipham Quant — Product Manual / 产品说明书

> **Version / 版本**: v0.1.0  
> **Date / 日期**: 2026-06-08  
> **Publisher / 发行方**: One Mipham Corporation (北京华安麦逄科技有限公司)

---

## 1. Product Overview / 产品概述

**Mipham Quant** is an AI-powered quantitative trading workstation developed by One Mipham Corporation. It provides end-to-end quantitative research workflows: multi-market data access (A-shares, HK Stock Connect, global markets), Python-based strategy authoring, Polars-accelerated backtesting, and an integrated factor engine for systematic stock screening.

**Mipham Quant**（米旁量化）是北京华安麦逄科技有限公司旗下 One Mipham Corporation 开发的 AI 量化交易工作站。平台提供端到端的量化研究工作流：跨市场行情数据接入（A股、港股通及全球市场）、Python 原生策略开发、Polars 加速回测引擎，以及集成化因子引擎用于系统化选股。

### Key Differentiators / 核心优势

| Feature | Description |
|---------|-------------|
| **Local-First / 本地优先** | All data and strategies run on your machine. No cloud dependency for core workflows. |
| **Multi-Market / 跨市场** | A-shares, HK Stock Connect, crypto, forex, US stocks, futures — unified API. |
| **Python-Native / Python 原生** | Write strategies in pure Python. No DSL, no proprietary language. |
| **Polars Acceleration / Polars 加速** | Backtest hot path 5-10x faster than pandas. Vectorized metrics computation. |
| **AI-Assisted / AI 辅助** | Built-in LLM integration for market analysis, strategy generation, and code assistance. |
| **Self-Hosted / 可自托管** | Docker Compose one-click deployment. Full data sovereignty. |

---

## 2. System Architecture / 系统架构

```
┌─────────────────────────────────────────────────────┐
│                   Nginx (Port 8888)                  │
│              Static Assets + API Proxy               │
└──────────────────────┬──────────────────────────────┘
                       │ /api/*
┌──────────────────────▼──────────────────────────────┐
│              Flask + Gunicorn (Port 5000)            │
│  ┌──────────┬──────────┬──────────┬──────────────┐  │
│  │  Market  │ Backtest │  Factor  │   Strategy   │  │
│  │   Data   │  Engine  │  Engine  │   Runtime    │  │
│  └──────────┴──────────┴──────────┴──────────────┘  │
└──────────────┬──────────────────┬───────────────────┘
               │                  │
┌──────────────▼────────┐ ┌──────▼──────────┐
│   PostgreSQL 16       │ │   Redis 7       │
│  (Port 5432)          │ │  (Port 6379)    │
│  Persistent Storage   │ │  Cache + Queue  │
└───────────────────────┘ └─────────────────┘
```

### Data Source Fallback Architecture / 数据源降级架构

```
A-Shares (CNStock):
  Twelve Data → Tencent fqkline → AKShare → yfinance

HK Stocks (HKStock):
  Twelve Data → futu-api → Tencent fqkline → AKShare HK → yfinance
```

---

## 3. Quick Start / 快速开始

### Prerequisites / 前置条件

- macOS 14+ / Windows 11 / Linux (kernel 5.15+)
- Docker Desktop 4.x+
- 8 GB RAM minimum (16 GB recommended)
- Python 3.12+ (for local development)

### Installation / 安装

```bash
# 1. Clone repository
git clone <repo-url> MiphamQuant
cd MiphamQuant

# 2. One-click launch
./start.sh

# 3. Open browser
# → http://localhost:8888
# → Login: mipham / mipham2026
```

### Shutdown / 关闭

```bash
./stop.sh
```

---

## 4. Feature Guide / 功能指南

### 4.1 Market Data / 行情数据

Supported markets and symbol formats:

| Market | Format | Example |
|--------|--------|---------|
| A-Share (Shanghai) | `XXXXXX.SH` | `600519.SH` (Kweichow Moutai) |
| A-Share (Shenzhen) | `XXXXXX.SZ` | `000001.SZ` (Ping An Bank) |
| ChiNext / STAR | `XXXXXX.SZ` / `XXXXXX.SH` | `300750.SZ` (CATL) |
| HK Stock Connect | `XXXXX.HK` | `00700.HK` (Tencent) |
| Crypto | `BTC/USDT`, `ETH/USDT` | Via CCXT |
| US Stocks | `AAPL`, `TSLA` | Via yfinance |

**Timeframes / 时间周期**: `1m`, `5m`, `15m`, `30m`, `1H`, `4H`, `1D`, `1W`

### 4.2 Strategy Development / 策略开发

Strategies are written in Python using the Indicator IDE convention:

```python
my_indicator_name = "Dual MA Cross"
my_indicator_description = "5/20 EMA crossover strategy for CSI 300"

# @strategy stopLossPct 0.05
# @strategy takeProfitPct 0.15
# @strategy tradeDirection long

df = df.copy()
sma5 = df['close'].rolling(5).mean()
sma20 = df['close'].rolling(20).mean()

# Golden cross → buy, Dead cross → sell
buy = (sma5 > sma20) & (sma5.shift(1) <= sma20.shift(1))
sell = (sma5 < sma20) & (sma5.shift(1) >= sma20.shift(1))

df['buy'] = buy.fillna(False).astype(bool)
df['sell'] = sell.fillna(False).astype(bool)

output = {
    'name': my_indicator_name,
    'plots': [
        {'name': 'MA5', 'data': sma5.tolist(), 'color': '#faad14', 'overlay': True},
        {'name': 'MA20', 'data': sma20.tolist(), 'color': '#1677ff', 'overlay': True}
    ]
}
```

**Strategy Annotations / 策略注解**:

| Annotation | Description | Default |
|------------|-------------|---------|
| `@strategy stopLossPct` | Stop-loss percentage | 0 (disabled) |
| `@strategy takeProfitPct` | Take-profit percentage | 0 (disabled) |
| `@strategy entryPct` | Position size (% of capital) | 1.0 (100%) |
| `@strategy tradeDirection` | `long` / `short` / `both` | `long` |

### 4.3 Backtesting / 回测

**Engine Options / 引擎选项**:

| Engine | Environment Variable | Features |
|--------|---------------------|----------|
| **Polars (default)** | `BACKTEST_ENGINE=polars` | 5-10x faster, long-only |
| **Pandas (legacy)** | `BACKTEST_ENGINE=pandas` | Full features: short, both, stop-loss, take-profit |

**Metrics / 回测指标**:

| Metric | Description |
|--------|-------------|
| Total Return / 总收益率 | Percentage return over backtest period |
| Annualized Return / 年化收益 | Simple annualization (total / years) |
| Sharpe Ratio / 夏普比率 | Risk-adjusted return (2% risk-free rate) |
| Max Drawdown / 最大回撤 | Largest peak-to-trough decline |
| Win Rate / 胜率 | Percentage of profitable round-trip trades |
| Profit Factor / 盈亏比 | Gross profit / gross loss |

### 4.4 Factor Engine / 因子引擎

**19 Factors across 8 Categories / 19 个因子覆盖 8 大类**:

| Category | Factors | Direction |
|----------|---------|-----------|
| **Valuation / 估值** | PE_TTM, PB, PS_TTM | Lower is better |
| **Profitability / 盈利** | ROE, ROA, Gross Margin, Net Margin | Higher is better |
| **Growth / 成长** | Revenue Growth YoY, Profit Growth YoY | Higher is better |
| **Momentum / 动量** | 1M / 3M / 6M Return | Higher is better |
| **Liquidity / 流动性** | 20D Avg Turnover, 20D Avg Volume | Higher is better |
| **Risk / 风险** | 60D Volatility, 1Y Max Drawdown | Lower is better |
| **Sentiment / 情绪** | Northbound Holding, Institution Holding | Higher is better |
| **Quality / 质量** | ST Flag | Lower is better |

**API Usage / API 使用**:

```python
from app.services.factor_engine import FactorEngine

engine = FactorEngine(max_workers=8)

# Score a single stock
result = engine.score_stock('600519.SH')

# Rank a universe
ranked = engine.rank_universe(
    ['600519.SH', '000858.SZ', '601318.SH'],
    top_n=10
)
```

---

## 5. Technical Specifications / 技术规格

| Component | Technology | Version |
|-----------|-----------|---------|
| Backend Framework | Flask + Gunicorn | 3.1.3 / 22.0 |
| Data Processing | Polars + Pandas | 1.0+ / 1.5+ |
| Database | PostgreSQL | 16 |
| Cache | Redis | 7 |
| Frontend | Vue 3 + ECharts | Prebuilt dist |
| Web Server | Nginx | 1.25-alpine |
| Containerization | Docker Compose | v2+ |
| Python | CPython | 3.12 |

### Key Dependencies / 核心依赖

| Package | Purpose |
|---------|---------|
| `akshare>=1.14.0` | A-share / HK data (Eastmoney) |
| `tushare>=1.4.0` | A-share fundamental data |
| `futu-api>=9.0.0` | HK real-time quotes (FutuOpenD) |
| `polars>=1.0.0` | Accelerated backtest engine |
| `pyarrow>=14.0.0` | Polars-pandas interop |
| `yfinance>=0.2.18` | Global market data |
| `ccxt>=4.0.0` | Cryptocurrency exchange data |

---

## 6. Built-in Example Strategies / 内置示例策略

| Strategy | Logic | Timeframe | Style |
|----------|-------|-----------|-------|
| RSI Edge Trigger | RSI < 30 → buy, RSI > 70 → sell | Any | Mean reversion |
| Dual MA Cross | Fast MA crosses slow MA → signal | Any | Trend following |
| MACD Zero Cross | MACD histogram crosses zero | Any | Momentum |
| Bollinger Bounce | Price touches lower band → buy | Any | Mean reversion |
| **A-Share Dual MA** | 5/20 EMA cross for CSI 300 | 1D | Trend following |
| **A-Share Multi-Factor** | Trend + volume surge filter | 1D | Factor-based |
| **A-Share Dragon-Tiger** | Limit-up + 2x volume breakout | 1D | T+1 scalping |

---

## 7. Environment Variables / 环境变量

| Variable | Default | Description |
|----------|---------|-------------|
| `SECRET_KEY` | Auto-generated | JWT signing key |
| `ADMIN_USER` | `mipham` | Default admin username |
| `ADMIN_PASSWORD` | `mipham2026` | Default admin password |
| `BACKTEST_ENGINE` | `polars` | Backtest engine: `polars` or `pandas` |
| `PYTHON_API_HOST` | `0.0.0.0` | Backend listen address |
| `PYTHON_API_PORT` | `5000` | Backend listen port |
| `POSTGRES_USER` | `mipham` | Database user |
| `POSTGRES_DB` | `mipham` | Database name |
| `TWELVE_DATA_API_KEY` | (none) | Twelve Data premium API key |
| `FUTU_HOST` | `127.0.0.1` | FutuOpenD host |
| `FUTU_PORT` | `11111` | FutuOpenD port |

---

## 8. Troubleshooting / 故障排除

| Problem | Solution |
|---------|----------|
| **Port conflict / 端口冲突** | Port 5000 may be used by macOS AirPlay. Backend maps to 5010 by default. |
| **No data for A-shares / A股无数据** | AKShare requires access to Eastmoney (Chinese IP recommended). Falls back to Tencent fqkline. |
| **FutuOpenD connection refused** | FutuOpenD must be running locally on port 11111. TCP pre-check skips within 2s if unavailable. |
| **Polars import error** | Install pyarrow: `pip install pyarrow>=14.0.0`. Engine falls back to pandas automatically. |
| **Backtest produces 0 trades** | Check that `df['buy']` and `df['sell']` columns are properly set. Verify trade direction matches signal columns. |

---

## 9. Roadmap / 路线图

| Phase | Timeline | Features |
|-------|----------|----------|
| **v0.1.0** | June 2026 | A-share + HK data, Polars backtest, Factor engine, Branding |
| **v0.2.0** | Q3 2026 | Proprietary Vue 3 frontend, Walk-forward backtest, AI strategy generation |
| **v0.3.0** | Q4 2026 | Paper trading, Live trading (IBKR/MT5), Multi-user enterprise mode |
| **v1.0.0** | Q1 2027 | Production release, Cloud deployment, Commercial licensing |

---

## 10. License & Contact / 许可证与联系方式

**License / 许可证**: Proprietary. Copyright © 2026 One Mipham Corporation. All rights reserved.

This product contains code from QuantDinger (Apache 2.0). Modified portions are proprietary.

**Contact / 联系方式**:
- Website: [mipham.ai](https://www.onemipham.com)
- Email: support@onemipham.com
- Organization: One Mipham Corporation (北京华安麦逄科技有限公司)

---

> **Document Version / 文档版本**: 1.0 | **Last Updated / 最后更新**: 2026-06-08  
> **Approved by / 批准人**: One Mipham Corporation 技术委员会
