# Mipham Quant — AI 量化交易平台

> Mipham Quant — AI-Powered Quantitative Trading Workstation

---

## 一句话 / Tagline

**让量化研究更智能** — A股+港股通 AI 量化交易工作站，从数据到策略的一站式平台。

*Smarter Quantitative Research* — AI-powered workstation for A-Shares & HK Stock Connect, from data to deployment.

---

## 产品介绍 / Product Overview

**Mipham Quant**（米旁量化）是 One Mipham Corporation（北京华安麦逄科技有限公司）旗下的 AI 量化交易旗舰平台。平台面向 A 股及港股通市场，提供端到端的量化研究工作流：跨市场行情数据一站式接入、Python 原生策略开发、Polars 加速回测引擎，以及覆盖八大类别的 19 因子系统化选股引擎。全部服务通过 Docker Compose 一键本地部署，确保用户完全数据主权。

**Mipham Quant** is One Mipham Corporation's flagship AI quantitative trading platform. Designed for A-share and HK Stock Connect markets, it delivers end-to-end quantitative research workflows: unified cross-market data access, Python-native strategy authoring, a Polars-accelerated backtest engine, and a 19-factor systematic screening engine spanning eight categories. The entire stack deploys locally via Docker Compose in a single command, guaranteeing full data sovereignty.

---

## 核心功能 / Key Features

| 功能 Feature | 说明 Description |
|-------------|-----------------|
| **跨市场行情数据**<br>*Multi-Market Data* | A股（沪深）、港股通、加密货币、美股、外汇 — 统一 API，6 层智能 fallback 确保数据可用性。<br>*A-shares, HK Stock Connect, crypto, US stocks, forex — unified API with 6-tier intelligent fallback.* |
| **Python 原生策略开发**<br>*Python-Native Strategy* | 用纯 Python 编写量化策略，无需学习 DSL。内置 7 个示例策略，`@strategy` 注解配置风控参数。<br>*Write strategies in pure Python — no DSL required. 7 built-in examples with `@strategy` annotation for risk controls.* |
| **Polars 加速回测引擎**<br>*Polars-Accelerated Backtest* | 热路径 5–10× 加速，向量化计算夏普比率、最大回撤、胜率、盈亏比。支持 Polars/Pandas 双引擎切换。<br>*5–10× faster hot path with vectorized Sharpe, max drawdown, win rate, profit factor. Dual-engine: Polars/Pandas.* |
| **19 因子选股引擎**<br>*19-Factor Screening Engine* | 覆盖估值、盈利、成长、动量、流动性、风险、情绪、质量八大类，支持并行全市场排名。<br>*Covers valuation, profitability, growth, momentum, liquidity, risk, sentiment, quality. Parallel universe ranking.* |
| **AI 辅助分析**<br>*AI-Assisted Analysis* | 内置 LLM 市场分析、策略生成、代码辅助。7 个 AI Agent 覆盖研究→策略→回测→执行全链路。<br>*Built-in LLM for market analysis, strategy generation, and code assistance. 7 AI Agents across the full pipeline.* |
| **一键本地部署**<br>*One-Click Deploy* | `./start.sh` 一键启动完整技术栈（PostgreSQL 16 + Redis 7 + Flask + Nginx），完全数据主权。<br>*Single-command launch of the full stack: PostgreSQL 16 + Redis 7 + Flask + Nginx. Full data sovereignty.* |

---

## 技术栈 / Tech Stack

`Python 3.12` · `Flask` · `Polars` · `PostgreSQL 16` · `Redis 7` · `Docker Compose` · `Vue 3` · `AKShare` · `Tushare` · `futu-api`

---

## 项目状态 / Project Status

| 属性 | 值 |
|------|-----|
| **版本 Version** | v0.1.0 — MVP |
| **发布日期 Release** | 2026-06-08 |
| **许可证 License** | Proprietary (含 Apache 2.0 衍生代码) |
| **发行方 Publisher** | One Mipham Corporation（北京华安麦逄科技有限公司） |

---

## 链接 / Links

- 📖 [产品说明书 Product Manual](https://github.com/sarvadaya/omc-project14-MiphamAI-Quant/blob/main/docs/PRODUCT_MANUAL.md) — 完整功能文档、架构说明、环境变量、故障排除
- 📘 [用户指南 User Guide](https://github.com/sarvadaya/omc-project14-MiphamAI-Quant/blob/main/docs/user-guide.md) — 快速开始、核心工作流、常见问题
- 💻 [源代码 Source Code](https://github.com/sarvadaya/omc-project14-MiphamAI-Quant) — GitHub 仓库

---

> 此文档用于官网 onemipham.com 的产品展示页 (`/mipham-quant`) 内容参考。
> *This document serves as content reference for the product page at onemipham.com/mipham-quant.*
