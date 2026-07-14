# Mipham Quant v0.1.0

> **AI-Powered Quantitative Trading Workstation** — A-Shares · HK Stock Connect · Multi-Market

**Mipham Quant** is the flagship quantitative trading platform by **One Mipham Corporation** (北京华安麦逄科技有限公司). It provides end-to-end quantitative research workflows: cross-market data access, Python-native strategy authoring, Polars-accelerated backtesting, and an integrated factor engine for systematic stock screening.

---

## Quick Start / 快速开始

```bash
./start.sh
```

Browser opens automatically → **http://localhost:8888** → Login: `mipham` / `mipham2026`

```bash
./stop.sh   # Graceful shutdown
```

## System Requirements / 系统要求

| Requirement | Minimum | Recommended |
|-------------|---------|-------------|
| OS | macOS 14+ / Windows 11 / Linux 5.15+ | macOS 15+ |
| Docker | Docker Desktop 4.x+ | Latest |
| RAM | 8 GB | 16 GB |
| Disk | 5 GB free | 20 GB SSD |

## Features / 核心功能

| Category | Features |
|----------|----------|
| **Market Data / 行情** | A-shares (沪深), HK Stock Connect (港股通), Crypto, US Stocks, Forex, Futures |
| **Strategy / 策略** | Python-native strategy IDE, built-in example strategies, AI-assisted code generation |
| **Backtest / 回测** | Polars-accelerated engine (5-10x), multi-timeframe, full metrics suite |
| **Factors / 因子** | 18 factors across 7 categories, multi-factor composite ranking, parallel screening |
| **Trading / 交易** | Quick trade panel, pending orders, IBKR & MT5 integration (optional) |
| **AI / 智能** | LLM market analysis, AI calibration, strategy generation, sentiment analysis |

## Architecture / 技术架构

```
Nginx (:8888) → Flask + Gunicorn (:5000) → PostgreSQL 16 + Redis 7
                     │
      ┌──────────────┼──────────────┐
      ▼              ▼              ▼
  Market Data    Backtest       Factor
  (6-tier        Engine         Engine
   fallback)     (Polars)      (19 factors)
```

## Documentation / 文档

| Document | Description |
|----------|-------------|
| [Product Manual / 产品说明书](docs/PRODUCT_MANUAL.md) | Full product specification (bilingual) |
| [User Guide / 用户指南](docs/user-guide.md) | Quick start and feature walkthrough |
| [Development Guide](DEVELOPMENT.md) | Local development setup |
| [Contributing](CONTRIBUTING.md) | Contribution guidelines |
| [Security](SECURITY.md) | Security policy and reporting |
| [Changelog](CHANGELOG.md) | Version history |

## License / 许可证

Copyright © 2026 **One Mipham Corporation** (北京华安麦逄科技有限公司). All rights reserved.

This product contains code from QuantDinger (Apache 2.0). Modified portions are proprietary. See [LICENSE](LICENSE) for full terms.

---

**Mipham Quant** — 让量化研究更智能
