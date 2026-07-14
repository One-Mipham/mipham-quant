# Changelog

All notable changes to Mipham Quant will be documented in this file.

## [0.1.0] — 2026-06-09 (MVP Release)

### Added

**Data Sources (Tasks 3-5)**
- A-Share K-line: Tencent fqkline (primary) + AKShare + yfinance + Twelve Data fallback
- HK Stock K-line: Tencent fqkline (primary) + futu-api + AKShare HK + yfinance + Twelve Data (6-tier)
- A-Share ticker: Tencent qt.gtimg.cn real-time quotes for SH/SZ/HK
- A-Share fundamentals: 同花顺 (THS) financial abstract — PE/PB/PS/PEG/ROE/ROA/gross_margin/net_margin/revenue_growth/earnings_growth/current_ratio/quick_ratio/debt_to_equity/eps/bvps/inventory_turnover
- HK Stock fundamentals: Twelve Data + AKShare HK financial indicators
- A-Share seeds: 10 CSI 300 blue chips (CNStock market)
- HK Stock seeds: 10 Hang Seng Index blue chips (HKStock market)

**Backtest Engine (Tasks 6-7)**
- CSI 300 full backtest validation: 5 stocks, SMA crossover, 1-year daily
- Polars-accelerated equity curve computation (1.4x+ faster, long-only)
- Multi-timeframe backtest framework
- Backtest edge cases: empty date range, invalid symbols, short range
- Pandas legacy fallback for short/both trade directions

**Factor Engine (Task 8)**
- 18 factors across 7 categories: valuation, profitability, growth, momentum, liquidity, risk, quality
- FactorEngine: single-stock scoring + parallel universe ranking (ThreadPoolExecutor)
- THS data parsing: correct handling of False→N/A sentinel and percentage strings
- Verified: Moutai PE=19.09, PB=5.83, ROE=54.27%

**Example Strategies (Task 9)**
- SMA Crossover (5/20 双均线) — built-in
- Multi-Factor Trend (60MA + volume surge) — built-in
- Mean Reversion (Bollinger Bands + RSI < 35) — NEW
- Momentum Breakout (20-day high + volume confirmation) — NEW
- Cross-strategy validation on 5 CSI 300 stocks

**Branding (Tasks 10-11)**
- All runtime defaults: mipham/mipham2026, mipham_quant DB
- Container names: mipham-quant-db/redis/backend/frontend
- env.example fully rebranded
- User-facing messages: signal notifications, MT5 comments, AI prompts
- start.sh SECRET_KEY check aligned
- docker-compose.yml health checks: postgres, redis, backend, frontend

**Infrastructure**
- Git submodule: omc-project14-MiphamAI-Quant → github.com/sarvadaya/omc-project14-MiphamAI-Quant
- Docker Compose: PostgreSQL 16 + Redis 7 + Flask backend + Nginx frontend
- One-click launch: ./start.sh (auto-config, health check, browser open)

### Tests
- **124 tests total, all green**
- HK stock: 19 tests (normalization, ticker, kline, factory)
- CN fundamentals: 23 tests (code normalization, THS parsing, multi-stock)
- CSI 300 backtest: 12 tests (pipeline, 5-stock, edge cases)
- Polars engine: 10 tests (correctness, parity, performance, edge cases)
- Factor engine: 24 tests (definitions, helpers, computation, ranking)
- A-share strategies: 13 tests (4 strategies × multi-stock validation)
- Existing tests: 23 tests (data providers, experiment services, health)

---

## History

This project builds upon QuantDinger v3.0.3 (Apache 2.0), enhanced with Chinese market data, Polars acceleration, and Mipham branding. See the original changelog below for the upstream history.
