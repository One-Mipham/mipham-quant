# Mipham Quant Desktop — 设计规格书

> **版本**: 1.0.0
> **日期**: 2026-07-14
> **状态**: 已确认
> **作者**: One Mipham Corporation 技术委员会

---

## 一、概述

将 Mipham Quant（当前为纯 Web 应用，运行于 `quant.onemipham.com`）改造为 **Electron 桌面应用**。

目标：产品化、市场化、可销售。方案 A（纯本地），一次性买断 License。

### 核心变更

| 维度 | 当前 Web 版 | 桌面版 |
|------|-----------|--------|
| 前端加载 | `https://quant.onemipham.com` | `file://dist/index.html` (Electron BrowserWindow) |
| 后端运行 | Docker/Gunicorn 服务器 | PyInstaller sidecar binary (127.0.0.1:5000) |
| 数据库 | PostgreSQL 16 | SQLite (app/data/quant.db) |
| 认证 | JWT + 多用户 + OAuth | 单用户本地模式 (无登录) |
| API 密钥 | 存服务器 .env | 存本地加密文件 |
| 分发 | 浏览器访问 | .dmg (macOS) + .exe (Windows) |
| 许可 | 无 | RSA 签名 License Key |

---

## 二、架构

```
┌──────────────────────────────────────────────────────┐
│                 Electron Main Process                 │
│                                                      │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ │
│  │ main.ts  │ │ license  │ │ backend  │ │  tray    │ │
│  │ 窗口管理  │ │ 激活验证  │ │ sidecar  │ │ 托盘菜单  │ │
│  └──────────┘ └──────────┘ └────┬─────┘ └──────────┘ │
│                                 │                     │
│                    spawn (child_process)              │
│                        │                             │
│  ┌─────────────────────▼───────────────────────────┐ │
│  │        Python Backend (PyInstaller binary)       │ │
│  │        127.0.0.1:5000                            │ │
│  │        Flask + SQLite + 策略引擎 + 交易所         │ │
│  └─────────────────────────────────────────────────┘ │
│                        │ HTTP (localhost)             │
│  ┌─────────────────────▼───────────────────────────┐ │
│  │      Vue 3 Frontend (BrowserWindow)              │ │
│  │      file://dist/index.html                      │ │
│  │      仪表盘 / K线 / 策略 / 回测 / 快讯            │ │
│  └─────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────┘
```

### 安全边界

- Python 后端**必须**绑定 `127.0.0.1`，不接受外部连接
- Electron preload 脚本暴露最小 API 给渲染进程（contextIsolation: true）
- License 文件使用 Fernet 加密存储
- API 密钥使用操作系统密钥链（macOS Keychain / Windows Credential Manager）

---

## 三、目录结构

```
mipham-quant/
│
├── electron/                          # 🆕 Electron 主进程
│   ├── main.ts                        # 入口：窗口创建、生命周期
│   ├── preload.ts                     # IPC 桥接
│   ├── license.ts                     # License 生成/验证
│   ├── backend.ts                     # Python sidecar 生命周期管理
│   ├── tray.ts                        # 系统托盘
│   └── notifications.ts              # 原生通知
│
├── apps/frontend/                     # 已有 — Vue 3 源码
│   ├── src/
│   │   ├── api/client.ts              # 修改：baseURL 改为 localhost
│   │   ├── router/index.ts            # 修改：添加路由守卫 + hash 模式
│   │   ├── stores/auth.ts            # 修改：本地用户模式
│   │   └── views/                     # 已有，不改
│   └── vite.config.ts                # 修改：base + outDir
│
├── backend_api_python/                # 已有 — Flask 后端
│   ├── app/
│   │   ├── utils/
│   │   │   ├── db.py                  # 修改：根据 DB_TYPE 路由
│   │   │   └── db_sqlite.py           # 🆕 SQLite 适配层
│   │   ├── config/
│   │   │   └── settings.py           # 修改：默认值适配单用户
│   │   └── data/
│   │       └── seed.sql               # 🆕 种子数据
│   ├── migrations/
│   │   └── init_sqlite.sql            # 🆕 SQLite schema
│   ├── pyinstaller.spec               # 🆕 PyInstaller 打包
│   └── build/                         # 🆕 后端构建产物
│
├── build/                             # 🆕 electron-builder 配置
│   ├── mac/
│   │   └── entitlements.plist
│   └── win/
│       └── installer.nsh
│
├── electron-builder.yml               # 🆕 electron-builder 配置
├── package.json                       # 扩展：electron 脚本
└── resources/                         # 🆕 应用图标等资源
    ├── icon.icns
    ├── icon.ico
    └── icon.png
```

---

## 四、关键模块设计

### 4.1 SQLite 适配层 (`db_sqlite.py`)

实现与 `db_postgres.py` 相同的接口：

| 接口 | PostgreSQL | SQLite |
|------|-----------|--------|
| 连接 | `psycopg2.pool.ThreadedConnectionPool` | `sqlite3.connect` + WAL 模式 |
| 行格式 | `RealDictCursor` | `sqlite3.Row` (dict-like) |
| 占位符 | `%s` → 运行时转换 | `?` 原生 |
| 自增主键 | `SERIAL` | `INTEGER PRIMARY KEY AUTOINCREMENT` |
| 当前时间 | `NOW()` | `datetime('now')` |
| Upsert | `INSERT ... ON CONFLICT ... DO UPDATE` | `INSERT OR REPLACE` |
| JSON | `JSONB` 原生类型 | `TEXT` (json.dumps/loads) |
| 连接池 | 内置 | WAL mode + `check_same_thread=False` |

**关键实现：**
- 数据库文件路径：`{app_data_dir}/quant.db`（Electron `app.getPath('userData')`）
- WAL 模式启用，支持并发读写
- 所有 SQL 统一使用 `?` 占位符（SQLite 原生）

### 4.2 License 系统

```
激活码格式: MQ-XXXX-XXXX-XXXX-XXXX (5段，Base32编码)

激活码结构（RSA签名后Base32编码）:
  {
    "product": "mipham-quant",
    "device_id": "abc123...",      # 可选：绑定设备
    "email": "user@example.com",
    "issued_at": "2026-07-14",
    "expires_at": "2099-12-31",   # 一次性买断=极远日期
    "features": ["all"]
  }

离线验证流程:
  1. 用户输入激活码
  2. Base32 解码 → RSA 公钥验签
  3. 提取 payload → 检查过期日
  4. 如绑定设备：对比设备指纹 (SHA256(MAC+CPU+主板))
  5. 写入 license.json (Fernet 加密)
  6. 每次启动读取验证
```

**设备指纹生成：**
```typescript
// 取 MAC 地址 + CPU 序列号 + 主板序列号的 SHA256
// macOS: system_profiler SPHardwareDataType
// Windows: wmic bios get serialnumber
```

**大师用激活码生成脚本（仅你持有私钥）：**
```bash
python scripts/generate-license.py \
  --email buyer@example.com \
  --output MQ-XXXX-XXXX-XXXX-XXXX
```

### 4.3 Python Sidecar 管理

```typescript
// electron/backend.ts — 生命周期管理
class BackendManager {
  private process: ChildProcess | null

  async start(): Promise<void> {
    // 1. 找 Python binary 路径
    //    - 开发: python backend_api_python/run.py
    //    - 生产: process.resourcesPath + '/backend/mipham-quant-backend'
    // 2. 设置环境变量:
    //    - DB_TYPE=sqlite
    //    - DB_PATH={userData}/quant.db
    //    - SECRET_KEY={随机生成}
    // 3. spawn 子进程
    // 4. 轮询 http://127.0.0.1:5000/api/health 直到就绪
    // 5. 监听 stdout/stderr，记录日志
  }

  async stop(): Promise<void> {
    // SIGTERM → 等 5 秒 → SIGKILL
  }

  // 崩溃自动重启 (最多 3 次)
  onCrash(): void { ... }
}
```

### 4.4 单用户模式

桌面版不需要登录系统。改动点：

| 文件 | 变更 |
|------|------|
| `settings.py` | `SINGLE_USER_MODE` 默认 `true` |
| `auth.py` | `login_required` → 单用户模式跳过验证 |
| `client.ts` | 移除 token 逻辑（或保留兼容） |
| `auth_store.ts` | 本地用户信息，不调登录接口 |
| `Login.vue` | 隐藏（或改为欢迎页） |

### 4.5 系统托盘

```
托盘菜单:
  ┌─────────────────┐
  │ 📊 显示主窗口    │
  │ 📈 策略运行中 (3) │
  ├─────────────────┤
  │ ⏸  暂停所有策略   │
  │ ▶  恢复所有策略   │
  ├─────────────────┤
  │ ⚙  设置          │
  │ ❓ 关于           │
  │ ✕  退出          │
  └─────────────────┘
```

关窗 = 隐藏到托盘（不退出）。真正的退出通过托盘菜单。

### 4.6 种子数据

首次启动（数据库文件不存在）时自动执行：

- **策略模板 (10个)**：双均线交叉、MACD、RSI 超买超卖、布林带突破、海龟交易、网格交易、动量择时、波动率收敛、OBV 背离、多因子综合
- **交易对**：BTC/USDT, ETH/USDT, BNB/USDT, SOL/USDT, 沪深300, 上证50, AAPL, TSLA, SPY, QQQ
- **默认配置**：模拟交易模式，初始资金 10,000 USDT

### 4.7 前端适配

| 文件 | 变更 |
|------|------|
| `vite.config.ts` | `base: './'` (file:// 协议兼容) |
| `router/index.ts` | `createWebHashHistory()` (hash 模式) |
| `api/client.ts` | `baseURL: 'http://127.0.0.1:5000/api'` |

---

## 五、构建与打包

### 5.1 PyInstaller

```python
# backend_api_python/pyinstaller.spec
a = Analysis(['run.py'],
    binaries=[],
    datas=[
        ('app/', 'app'),
        ('migrations/init_sqlite.sql', 'migrations'),
        ('app/data/seed.sql', 'app/data'),
    ],
    hiddenimports=['app', 'app.routes', 'app.services', 'app.utils'],
    ...
)
pyz = PYZ(a.pure)
exe = EXE(pyz, ...)  # 单文件 binary
```

产物：`dist/mipham-quant-backend` (macOS) / `dist/mipham-quant-backend.exe` (Windows)
大小估算：~40MB（Python 运行时 + Flask + pandas + ccxt + numpy）

### 5.2 electron-builder

```yaml
# electron-builder.yml
appId: com.onemipham.mipham-quant
productName: Mipham Quant
mac:
  category: public.app-category.finance
  target: [dmg, zip]
  icon: resources/icon.icns
  extraResources:
    - from: backend_api_python/dist/
      to: backend/
win:
  target: [nsis]
  icon: resources/icon.ico
  extraResources:
    - from: backend_api_python/dist/
      to: backend/
nsis:
  oneClick: false
  allowToChangeInstallationDirectory: true
```

### 5.3 版本发布流程

```
1. 修改版本号 (package.json, settings.py)
2. 构建 Python binary:  cd backend_api_python && pyinstaller pyinstaller.spec
3. 构建前端:            cd apps/frontend && pnpm build
4. 构建 Electron:       pnpm electron:build
5. 产物:
   - dist/mipham-quant-1.0.0.dmg
   - dist/mipham-quant Setup 1.0.0.exe
6. 上传到下载服务器:    scp dist/* root@192.144.235.27:/var/www/downloads/
```

---

## 六、不做什么（明确排除）

- ❌ 不上 Mac App Store / Microsoft Store（先裸发）
- ❌ 不做代码签名（下载页标注"安全提示：右键打开/仍要运行"）
- ❌ v1.0 不做自动更新（手动下载覆盖。v1.1 再引入 `electron-updater`）
- ❌ 不改造旧 `src/` 前端代码（只维护 `apps/frontend/` 新前端）
- ❌ 不做社区功能本地化（社区策略依赖云端，桌面版隐藏）
- ❌ 不做 USDT 支付（桌面版用激活码，无需内购）
- ❌ 不支持 Linux（先 mac + win）

---

## 七、风险评估

| 风险 | 影响 | 缓解 |
|------|------|------|
| Pandas/NumPy 打包体积大 | 安装包 ~150MB | 可接受 |
| ccxt 部分交易所需要系统库 | 个别交易所不可用 | 文档注明 |
| SQLite 并发写入性能 | 多策略同时写可能慢 | WAL 模式 + 串行写入 |
| 杀毒软件误报 | 用户安装受阻 | 申请白名单 / 签名 |
| macOS Apple Silicon 兼容 | Rosetta 运行 | arm64 单独构建 |

---

## 八、成功标准

- [ ] macOS .dmg 双击安装后可直接使用
- [ ] Windows .exe 安装后可直接使用
- [ ] 首次启动自动初始化数据库 + 种子数据
- [ ] 仪表盘 + K线 + 策略 + 回测 + 快讯 5 页面正常
- [ ] 模拟交易完整链路跑通（策略创建 → 运行 → 信号 → 模拟成交）
- [ ] License 激活码可激活/验证/拒绝
- [ ] 关闭窗口 = 托盘运行，策略不中断
- [ ] 设备重启后策略自动恢复
