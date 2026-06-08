# Mipham Quant — 设计规格书

> **版本**: 0.1.0
> **日期**: 2026-06-08
> **状态**: 已批准
> **作者**: Guohua Zhang + Claude Opus 4.8

---

## 一、产品定位

Mipham Quant（AI 量化交易平台）是 One Mipham Corporation 旗下的智能量化研究平台。

**双重目标**:
1. **内部使用**: 先服务 Rismed Ronxin Capital 自有资金管理（吃自己的狗粮）
2. **市场销售**: 最终打包为可销售的桌面量化产品，面向个人量化交易者和中小私募机构

**销售形态**:
- Mac 本地桌面应用（Docker-based 一键部署包）
- 后续可扩展至 Windows、Linux
- 定价模式：一次性买断 + 年度数据服务订阅

## 二、目标市场

- **Phase 1**: A 股（沪深两市，股票+ETF）+ 港股通（互联互通）
- **Phase 2**: 扩展至港股全市场、美股

## 三、MVP 核心能力（Phase 1，3 周）

1. **数据管道**: A 股+港股行情接入（日线/周线 K 线）、复权处理、财务数据、ST/停牌标记
2. **策略研究 + 回测**: 因子库、策略编写框架（Python 脚本）、历史回测引擎（Polars）、绩效指标输出

**Phase 1 不做**: 实盘执行、AI 策略生成、多用户/计费

## 四、技术选型

| 层 | 选型 | 理由 |
|---|------|------|
| 后端 | Flask（QuantDinger 现有）→ 逐步迁移至 FastAPI | 最快出产品，渐进改造 |
| 数据处理 | pandas → Polars（回测热路径优先） | 渐进替换，先引擎后数据管道 |
| 数据库 | PostgreSQL 16（Docker） | QuantDinger 现有 |
| 缓存 | Redis 7（Docker） | QuantDinger 现有 |
| 前端 | Vue 3 + Vite + Tailwind CSS + ECharts/KLineCharts | 自研（商业化必需），参考 QuantDinger UI 布局 |
| 部署 | Docker Compose（开发）→ 打包安装器（销售） | 先一键启动，后 .app 安装 |
| A股数据 | AKShare(主) → 腾讯接口 → Tushare(fallback) | 免费优先，多层兜底 |
| 港股数据 | AKShare + futu-api(实时) | 富途 OpenAPI 原生 Mac |
| 前端图表 | ECharts / KLineCharts（QuantDinger 已有） | 不改，直接复用 |

## 五、落地策略（方案 C — 改造增强）

### 5.1 核心原则

**不改架构，改模块。系统一直在跑，每周交付。**

QuantDinger v3.0.3 已经是完整的量化操作系统（后端 59 个 Python 模块 + 前端 Vue 3 完整 UI + Docker Compose 部署）。我们不再重写，而是：
1. 扩展数据源，让它支持 A 股+港股通
2. 把回测引擎热路径从 pandas 换成 Polars
3. 增加 A 股专有因子
4. 品牌化包装

### 5.2 为什么不是从零自研

- QuantDinger 的策略引擎、回测框架、K 线图表、实验编排都是成熟实现
- A股数据源模块（`cn_stock.py`, `hk_stock.py`, `cn_hk_fundamentals.py`）已有骨架，只需增强
- 从零写一套等价的系统至少 2-3 个月，不值得

## 六、三周里程碑

### Week 1 — 跑通 + 增强数据

**Day 1-2**: QuantDinger Docker Compose 本地部署，验证：登录→看行情→写策略→回测→看报告 全链路
**Day 3-4**: 扩展 A 股数据源 — 验证日线/周线 K 线、复权、财务数据可用性；港股同理
**Day 5-6**: 沪深 300 全量日线回测跑通，确认数据质量和性能
**Day 7**: 提交代码，输出数据验证报告

**Week 1 成功标准**: 在 QuantDinger 界面中选择 A 股标的（如 600001.SH），能看到完整 K 线图，写一个简单双均线策略能跑出回测结果。

### Week 2 — 策略框架改造

**Day 8-9**: 回测引擎热路径换 Polars（信号计算、权益曲线、绩效指标）
**Day 10-11**: 新增 A 股专有因子：PE/PB/ROE/ROA/营收增速/龙虎榜/资金流向
**Day 12-13**: 策略编辑器 A 股适配（参数面板、因子代码提示、示例策略）
**Day 14**: 端到端验证：选 A 股池→写因子策略→回测→比较结果

**Week 2 成功标准**: 能写一个 A 股多因子选股策略（如 "PE<20 AND ROE>15%"），对沪深 300 跑回测，输出绩效报告。

### Week 3 — 封装产品 + 本地安装

**Day 15-16**: 品牌化（Mipham Quant 名称/Logo/配色 替换 QuantDinger）
**Day 17-18**: 一键启动脚本（`./start.sh` → Docker Compose → 自动打开浏览器）
**Day 19-20**: Bug 修复、端到端测试、文档补全
**Day 21**: 发布 v0.1.0，提交代码，写 CHANGELOG

**Week 3 成功标准**: 执行 `./start.sh` 后，浏览器自动打开 http://localhost:8888，显示 Mipham Quant 界面，A股/港股数据可用，策略回测流畅。

## 七、Phase 2 展望（v0.2.0+）

- 自研 Vue 3 前端（替代 QuantDinger 预构建前端，满足商业化要求）
- FastAPI 网关层（API 契约标准化）
- AI 驱动的策略生成（LLM 写策略代码）
- 实验编排管线（市场状态识别→策略候选生成→批量回测→排序→最优输出）

## 八、Phase 3 展望（v0.3.0+）

- 实盘交易 + 风控（富途 OpenAPI，Mac 原生）
- 组合优化
- 多用户体系

## 九、Phase 4 展望（v1.0 — 市场化销售）

- Mac .app 打包安装器（Docker Desktop 捆绑或内嵌服务）
- 许可证激活系统
- 自动更新机制
- Windows/Linux 安装包
- 定价方案：基础版 ¥X / 专业版 ¥Y / 机构版 ¥Z
- 数据服务订阅（实时行情、财务数据更新）

## 十、许可证策略

| 组件 | 许可证 | 说明 |
|------|--------|------|
| Mipham Quant 后端 | Proprietary（闭源商用） | 基于 Apache 2.0（QuantDinger 后端）二次开发 |
| Mipham Quant 前端 | Proprietary（闭源商用） | 完全自研 |
| QuantDinger 后端改造部分 | Apache 2.0（保留原始版权声明） | 合规继承上游许可证 |
| 数据源接口 | MIT / Apache 2.0 | AKShare(MIT)、Tushare(Apache 2.0) 等第三方库 |

## 十一、技术风险与对策

| 风险 | 对策 |
|------|------|
| QuantDinger 数据源依赖 Twelve Data API（海外服务，A股质量差） | 优先 AkShare 直连东方财富等国内源，绕过海外代理 |
| AkShare 海外服务器访问受限 | 配置代理绕过策略（`_bypass_proxy` 已有），或使用 Tushare Pro |
| 港股实时数据短缺 | futu-api（富途 OpenAPI）原生支持 Mac，质量可靠 |
| Polars 替代 pandas 的兼容性 | 只在回测引擎内部替换，API 接口不变，渐进改造 |
| QuantDinger 前端不可商用 | QuantDinger 前端 license 为 Source-Available（商业需授权），Mipham Quant 必须自研前端；内部开发期可临时用预构建文件跑通链路，发布前替换 |

## 十、开发环境

```bash
# Mac 本地
├── Docker Desktop（PostgreSQL 16 + Redis 7）
├── Python 3.12+（虚拟环境）
├── Node.js 22+（前端开发，可选 — 预构建也能用）
└── 浏览器 Chrome/Safari → localhost:8888
```
