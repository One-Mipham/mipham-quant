# Mipham Quant — AI 量化交易工作站

> **让量化研究更智能** · 你的数据，你的策略，你的主场

---

## 产品概述

**Mipham Quant**（麦逄量化）是[北京华安麦逄科技有限公司](https://onemipham.com)（One Mipham Corporation）旗下的 AI 量化交易旗舰平台。平台面向 A 股、港股通及全球多市场，提供端到端的量化研究工作流——从跨市场行情数据一站式接入、Python 原生策略开发，到 Polars 加速回测引擎、19 因子系统化选股，再到实盘交易——全部整合在一个平台中。

**核心理念："数据主权 + AI 赋能"**。通过 Docker Compose 一键本地部署，所有行情数据、策略代码、交易记录完全存储于用户自有服务器，确保绝对数据隐私；同时内置 LLM 大模型驱动的市场分析、策略生成与代码辅助能力，让个人投资者也能享受机构级的 AI 量化工具。

---

## 为什么选择 Mipham Quant

### 🏗️ 全栈式量化工作台

传统量化工具往往割裂——数据获取用一个工具，策略回测用另一个，实盘交易再换一个。Mipham Quant 将这些环节无缝整合：

> **数据采集 → 因子研究 → 策略开发 → 回测验证 → 模拟交易 → 实盘执行**
>
> AI 全程辅助每一步

### 🔐 完全数据主权

所有代码和数据均在用户本地或自有服务器运行。我们**不收集、不存储、不上传**任何用户的策略代码、交易记录或账户凭据。一行 `./start.sh`，整个技术栈在本地启动。

### 🧠 AI 原生设计

7 个专业 AI Agent 覆盖量化研究全链路：

| Agent | 职责 |
|-------|------|
| 市场分析 Agent | 多维度市场研判、板块轮动分析 |
| 策略生成 Agent | 根据市场特征自动生成交易策略框架 |
| 因子研究 Agent | 智能挖掘有效因子、多因子组合优化 |
| 代码辅助 Agent | 策略代码生成、调试、性能优化 |
| 回测评估 Agent | 多场景压力测试、参数敏感性分析 |
| 风险监控 Agent | 实时风险评估、极端行情预警 |
| 交易执行 Agent | 智能订单路由、滑点控制、成本优化 |

### ⚡ 高性能回测引擎

- **Polars 加速**：热路径 5–10× 性能提升
- **向量化计算**：夏普比率、最大回撤、胜率、盈亏比一键输出
- **Polars / Pandas 双引擎**：一键切换，兼容现有策略代码
- **多周期支持**：分钟线到月线，T+1 到 T+0 制度适配

### 🔬 19 因子系统化选股

覆盖八大类别的多因子选股引擎，支持全市场并行排名：

| 类别 | 示例因子 |
|------|---------|
| 估值 | PE、PB、PS、PEG |
| 盈利 | ROE、ROA、毛利率、净利率 |
| 成长 | 营收增速、利润增速、EPS 增速 |
| 动量 | 1M / 3M / 6M / 12M 收益率 |
| 流动性 | 换手率、成交量、Amihud 非流动性 |
| 风险 | 波动率、Beta、VaR、最大回撤 |
| 情绪 | 北向资金、融资融券、大宗交易 |
| 质量 | 现金流、杠杆率、应计利润 |

---

## 核心功能一览

| 功能 | 说明 |
|------|------|
| 📊 **跨市场行情数据** | A股（沪深）、港股通、加密货币、美股、外汇 — 统一 API，6 层智能 fallback |
| 🐍 **Python 原生策略开发** | 纯 Python 编写策略，无需学习 DSL，内置 7 个示例策略 |
| 🚀 **Polars 加速回测引擎** | 热路径 5–10× 加速，支持 Polars / Pandas 双引擎切换 |
| 🔬 **19 因子选股引擎** | 八大类别覆盖，支持并行全市场排名 |
| 🤖 **AI 辅助分析** | 内置 LLM 市场分析、策略生成、代码辅助，7 个 AI Agent 全链路覆盖 |
| 📦 **一键本地部署** | `./start.sh` 一键启动完整技术栈，完全数据主权 |

---

## 跨市场覆盖

统一 API 接入以下市场，支持 6 层智能数据 fallback：

| 市场 | 数据源 | 特点 |
|------|--------|------|
| **A 股（沪深）** | AKShare / Tushare / EastMoney | 全量行情、财务数据、龙虎榜 |
| **港股通** | Futu API / 腾讯行情 | 实时行情、资金流向 |
| **加密货币** | Binance / OKX / Bybit 等 12+ 交易所 | 7×24 永续合约 |
| **美股** | yfinance / IBKR / Finnhub | 股票 + 期权 |
| **外汇** | CCXT / OANDA | 主要货币对 |
| **预测市场** | Polymarket | 事件驱动的概率交易 |

---

## 技术架构

```
                    Nginx (:8888)
                         │
                    Flask + Gunicorn (:5000)
                         │
          ┌──────────────┼──────────────┐
          ▼              ▼              ▼
     PostgreSQL 16    Redis 7      LLM 引擎
     (策略/交易/用户)   (缓存/队列)   (OpenRouter)
          │
    ┌─────┴─────────────┐
    ▼                   ▼
  行情数据层          策略执行层
  (6-tier fallback)   (Polars/Pandas)
```

**核心技术栈**：`Python 3.12` · `Flask` · `Polars` · `PostgreSQL 16` · `Redis 7` · `Docker Compose` · `Vue 3` · `Electron`

---

## 适用人群

| 用户角色 | 使用场景 |
|---------|---------|
| 🧑‍💻 **个人量化投资者** | A 股 / 港股策略开发、因子研究、回测验证、模拟交易 |
| 📈 **独立交易员** | 多策略并行管理、风险监控、跨市场套利 |
| 🏢 **小型投资团队** | 策略共享、权限管理、业绩归因 |
| 🎓 **量化学习爱好者** | 内置示例策略、Python 策略 IDE、AI 代码辅助 |
| 🏭 **金融数据研究者** | 多源数据聚合、因子挖掘、市场微观结构分析 |

---

## 部署方式

### 🖥️ 桌面版（推荐个人用户）

macOS / Windows / Linux 原生应用，内置 Python 运行环境，开箱即用。SQLite 本地数据库，零配置单用户模式。

### 🐳 Docker 版（推荐团队 / 服务器）

```bash
git clone https://github.com/One-Mipham/mipham-quant.git
cd mipham-quant
cp backend_api_python/env.example backend_api_python/.env
# 编辑 .env 设置 SECRET_KEY
./start.sh
# 浏览器访问 http://localhost:8888
```

### ☁️ 云部署（SaaS 多用户）

支持腾讯云等任意 Linux 服务器，Docker Compose 一键部署，Nginx 反向代理，多用户注册与权限管理。

---

## 产品状态

| 属性 | 说明 |
|------|------|
| **当前版本** | v0.1.0 — MVP 公测版 |
| **发布日期** | 2026-07-15 |
| **桌面版** | macOS / Windows / Linux — 内测中 |
| **移动端** | iOS / Android — 规划中 |

---

## 获取 Mipham Quant

- 🌐 **官网**：[onemipham.com/quant](https://onemipham.com/quant)
- 💻 **GitHub**：[github.com/One-Mipham/mipham-quant](https://github.com/One-Mipham/mipham-quant)
- 📖 **完整产品说明书**：[PRODUCT_MANUAL.md](https://github.com/One-Mipham/mipham-quant/blob/main/docs/PRODUCT_MANUAL.md)
- 📘 **用户指南**：[user-guide.md](https://github.com/One-Mipham/mipham-quant/blob/main/docs/user-guide.md)

---

## 关于华安麦逄

**北京华安麦逄科技有限公司**（One Mipham Corporation）是一家专注于 AI 技术研发与应用的科技企业。公司以 "MegaSystem AI 体系" 为核心基础设施，构建覆盖量化金融、科学智能、医学智能、AI 游戏等十一大领域的产品矩阵。

- 🌐 官网：[onemipham.com](https://onemipham.com) | [mipham.ai](https://mipham.ai)
- 📧 联系：contact@onemipham.com

---

> *Mipham Quant — 让量化研究更智能*
>
> © 2026 One Mipham Corporation. All rights reserved.
