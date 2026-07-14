# Mipham Quant Desktop — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build Electron desktop application for Mipham Quant — PyInstaller-packaged Python backend, SQLite local database, Vue 3 frontend, RSA license activation, system tray, .dmg + .exe installers.

**Architecture:** Electron main process spawns Python Flask backend as a child process (localhost:5000), loads Vue 3 SPA via `file://` protocol. SQLite replaces PostgreSQL. Single-user mode (no login). License verified offline via RSA signature.

**Tech Stack:** Electron 34, TypeScript, Vue 3, Vite, Python 3.12, Flask, SQLite, PyInstaller, electron-builder, Node.js crypto (RSA)

## Global Constraints

- Python backend MUST bind `127.0.0.1` only (no external access)
- Electron contextIsolation=true, nodeIntegration=false
- License file stored with Fernet encryption
- DB_TYPE=sqlite as default, PostgreSQL path preserved for legacy
- No code signing (bare .dmg/.exe)
- No auto-update in v1.0
- macOS + Windows only (no Linux)
- Use `apps/frontend/` (new frontend), not old `src/`

---

## Task 1: SQLite Migration Schema

**Files:**
- Create: `backend_api_python/migrations/init_sqlite.sql`

**Interfaces:**
- Produces: `init_sqlite.sql` — run once to create all tables. Called by `db_sqlite.py:init_database()`.

- [ ] **Step 1: Create SQLite schema**

Create `backend_api_python/migrations/init_sqlite.sql`:

```sql
-- Mipham Quant — SQLite Schema (Desktop Edition)
-- INTEGER PRIMARY KEY = auto-increment in SQLite

-- Users (single-user desktop mode, but keep table for data ownership)
CREATE TABLE IF NOT EXISTS qd_users (
    id INTEGER PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT,
    nickname TEXT DEFAULT 'Trader',
    email TEXT,
    avatar TEXT DEFAULT '/avatar2.jpg',
    role TEXT DEFAULT 'admin',
    status TEXT DEFAULT 'active',
    email_verified INTEGER DEFAULT 1,
    token_version INTEGER DEFAULT 1,
    timezone TEXT DEFAULT '',
    notification_settings TEXT DEFAULT '{}',
    chart_templates TEXT DEFAULT '[]',
    referred_by INTEGER,
    last_login_at TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

-- Strategy codes (user-written indicators)
CREATE TABLE IF NOT EXISTS qd_indicator_codes (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL DEFAULT 1,
    name TEXT NOT NULL,
    description TEXT DEFAULT '',
    code TEXT NOT NULL,
    language TEXT DEFAULT 'python',
    category TEXT DEFAULT 'custom',
    version INTEGER DEFAULT 1,
    publish_to_community INTEGER DEFAULT 0,
    review_status TEXT DEFAULT 'approved',
    review_note TEXT DEFAULT '',
    reviewed_by INTEGER,
    reviewed_at TEXT,
    updatetime TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES qd_users(id)
);

-- Trading strategies (configured instances)
CREATE TABLE IF NOT EXISTS qd_strategies (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL DEFAULT 1,
    name TEXT NOT NULL,
    symbol TEXT NOT NULL,
    market TEXT NOT NULL DEFAULT 'Crypto',
    strategy_type TEXT DEFAULT 'IndicatorStrategy',
    indicator_id INTEGER,
    indicator_params TEXT DEFAULT '{}',
    trading_config TEXT DEFAULT '{}',
    exchange_config TEXT DEFAULT '{}',
    status TEXT DEFAULT 'stopped',
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES qd_users(id),
    FOREIGN KEY (indicator_id) REFERENCES qd_indicator_codes(id)
);

-- Trade records
CREATE TABLE IF NOT EXISTS qd_trades (
    id INTEGER PRIMARY KEY,
    strategy_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL DEFAULT 1,
    symbol TEXT NOT NULL,
    market TEXT NOT NULL,
    side TEXT NOT NULL,
    price REAL NOT NULL,
    amount REAL NOT NULL,
    value REAL,
    commission REAL DEFAULT 0,
    profit REAL,
    trade_time TEXT DEFAULT (datetime('now')),
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (strategy_id) REFERENCES qd_strategies(id),
    FOREIGN KEY (user_id) REFERENCES qd_users(id)
);

-- Exchange credentials (encrypted)
CREATE TABLE IF NOT EXISTS qd_exchange_credentials (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL DEFAULT 1,
    exchange TEXT NOT NULL,
    name TEXT,
    encrypted_config TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES qd_users(id),
    UNIQUE(user_id, exchange, name)
);

-- Watchlist
CREATE TABLE IF NOT EXISTS qd_watchlist (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL DEFAULT 1,
    market TEXT NOT NULL,
    symbol TEXT NOT NULL,
    name TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES qd_users(id),
    UNIQUE(user_id, market, symbol)
);

-- Strategy snapshots (for backtest performance tracking)
CREATE TABLE IF NOT EXISTS qd_strategy_snapshots (
    id INTEGER PRIMARY KEY,
    strategy_id INTEGER NOT NULL,
    snapshot_data TEXT NOT NULL DEFAULT '{}',
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (strategy_id) REFERENCES qd_strategies(id)
);

-- Security logs (local)
CREATE TABLE IF NOT EXISTS qd_security_logs (
    id INTEGER PRIMARY KEY,
    user_id INTEGER,
    action TEXT NOT NULL,
    ip_address TEXT,
    user_agent TEXT,
    details TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

-- Login attempts (relevant for license activation tracking)
CREATE TABLE IF NOT EXISTS qd_login_attempts (
    id INTEGER PRIMARY KEY,
    identifier TEXT NOT NULL,
    identifier_type TEXT NOT NULL,
    success INTEGER NOT NULL DEFAULT 0,
    ip_address TEXT,
    user_agent TEXT,
    attempt_time TEXT DEFAULT (datetime('now'))
);

-- Verification codes (simplified, not used in desktop but keep schema)
CREATE TABLE IF NOT EXISTS qd_verification_codes (
    id INTEGER PRIMARY KEY,
    email TEXT NOT NULL,
    code TEXT NOT NULL,
    code_type TEXT DEFAULT 'register',
    ip_address TEXT,
    expires_at TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

-- Polymarket markets cache
CREATE TABLE IF NOT EXISTS qd_polymarket_markets (
    id INTEGER PRIMARY KEY,
    market_id TEXT NOT NULL UNIQUE,
    title TEXT,
    volume REAL DEFAULT 0,
    liquidity REAL DEFAULT 0,
    outcomes TEXT DEFAULT '[]',
    end_date TEXT,
    raw_data TEXT DEFAULT '{}',
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

-- License activation record
CREATE TABLE IF NOT EXISTS qd_license (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    license_key_hash TEXT NOT NULL,
    email TEXT,
    device_id TEXT,
    issued_at TEXT,
    expires_at TEXT,
    features TEXT DEFAULT '["all"]',
    activated_at TEXT DEFAULT (datetime('now'))
);

-- Insert default user for single-user mode
INSERT OR IGNORE INTO qd_users (id, username, nickname, role, status)
VALUES (1, 'trader', 'Trader', 'admin', 'active');

-- Enable WAL mode for concurrent access
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;
```

- [ ] **Step 2: Commit**

```bash
git add backend_api_python/migrations/init_sqlite.sql
git commit -m "feat: add SQLite migration schema for desktop edition

15 tables: users, indicators, strategies, trades, credentials,
watchlist, snapshots, security_logs, polymarket, license.
WAL mode + foreign keys enabled. Default admin user seeded."
```

---

## Task 2: SQLite Database Adapter

**Files:**
- Create: `backend_api_python/app/utils/db_sqlite.py`
- Modify: `backend_api_python/app/utils/db.py`

**Interfaces:**
- Produces: `get_db_connection() -> sqlite3.Connection` (context manager), `init_database()`, `get_pg_connection()` alias, `get_db_type() -> str`
- Consumes: `init_sqlite.sql` from Task 1

- [ ] **Step 1: Create db_sqlite.py**

Create `backend_api_python/app/utils/db_sqlite.py`:

```python
"""
SQLite Database Adapter for Desktop Edition.

Implements the same interface as db_postgres.py so calling code
requires zero changes. Switched via DB_TYPE=sqlite environment variable.
"""

import json
import os
import sqlite3
import threading
from contextlib import contextmanager
from typing import Any

from app.utils.logger import get_logger

logger = get_logger(__name__)

# Default DB path: same directory as this file's grandparent (backend_api_python/)
# In production, set DB_PATH env var to Electron's userData directory.
_DEFAULT_DB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data")
_DB_PATH = os.getenv("DB_PATH", os.path.join(_DEFAULT_DB_DIR, "quant.db"))

# Thread-local connections (one per thread, like a simple pool)
_local = threading.local()
_write_lock = threading.Lock()  # Serialize writes for SQLite


def get_db_path() -> str:
    return _DB_PATH


def _ensure_db_dir():
    db_dir = os.path.dirname(_DB_PATH)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)


def _get_connection() -> sqlite3.Connection:
    """Get or create a thread-local SQLite connection."""
    conn = getattr(_local, "connection", None)
    if conn is None:
        _ensure_db_dir()
        conn = sqlite3.connect(_DB_PATH, check_same_thread=False)
        conn.row_factory = sqlite3.Row  # dict-like access
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA busy_timeout=5000")
        _local.connection = conn
    return conn


@contextmanager
def get_db_connection():
    """
    Context manager that yields a thread-local SQLite connection.
    Auto-commits on successful exit, rolls back on exception.
    Does NOT close the connection (thread-local reuse).

    Usage:
        with get_db_connection() as db:
            cur = db.cursor()
            cur.execute("SELECT ...")
            rows = cur.fetchall()
    """
    conn = _get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def get_db_connection_sync():
    """
    Synchronous accessor (non-context-manager) for legacy code.
    Returns the raw connection. Caller must manage commit/rollback.
    """
    return _get_connection()


# Alias for backward compatibility with db.py's re-export
get_pg_connection = get_db_connection
get_pg_connection_sync = get_db_connection_sync


def init_database():
    """
    Initialize database schema from init_sqlite.sql.
    Idempotent — uses IF NOT EXISTS.
    Also seeds default user row.
    """
    init_sql_paths = [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..",
                     "migrations", "init_sqlite.sql"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..",
                     "..", "migrations", "init_sqlite.sql"),
        # PyInstaller: resources are next to the binary
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..",
                     "..", "..", "migrations", "init_sqlite.sql"),
    ]

    init_sql = None
    for p in init_sql_paths:
        norm = os.path.normpath(p)
        if os.path.exists(norm):
            with open(norm, "r", encoding="utf-8") as f:
                init_sql = f.read()
            logger.info(f"Loaded schema from {norm}")
            break

    if init_sql is None:
        # Fallback: embed the schema inline for PyInstaller bundles
        logger.warning("init_sqlite.sql not found on disk, using embedded schema")
        init_sql = _EMBEDDED_SCHEMA

    with get_db_connection() as db:
        db.executescript(init_sql)

    logger.info("SQLite database initialized successfully")

    # Run seed data if available
    _run_seed_data()


def _run_seed_data():
    """Run seed SQL if database is empty."""
    with get_db_connection() as db:
        cur = db.cursor()
        cur.execute("SELECT COUNT(*) as cnt FROM qd_indicator_codes")
        row = cur.fetchone()
        if row and row["cnt"] > 0:
            return  # Already seeded

    seed_paths = [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "seed.sql"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..",
                     "app", "data", "seed.sql"),
    ]

    for p in seed_paths:
        norm = os.path.normpath(p)
        if os.path.exists(norm):
            with open(norm, "r", encoding="utf-8") as f:
                seed_sql = f.read()
            with get_db_connection() as db:
                db.executescript(seed_sql)
            logger.info(f"Seed data loaded from {norm}")
            return

    logger.info("No seed data file found, skipping")


def close_db_connection():
    """Close all thread-local connections."""
    conn = getattr(_local, "connection", None)
    if conn is not None:
        try:
            conn.close()
        except Exception:
            pass
        _local.connection = None


# ---------------------------------------------------------------------------
# Type conversion helpers (SQLite stores everything as primitive types)
# ---------------------------------------------------------------------------

def _convert_row(row: sqlite3.Row | dict | None) -> dict | None:
    """Convert a sqlite3.Row to a plain dict for API consumers."""
    if row is None:
        return None
    if isinstance(row, dict):
        return row
    return dict(row)


def _convert_rows(rows: list) -> list[dict]:
    """Convert a list of sqlite3.Row to list of plain dicts."""
    return [dict(r) if not isinstance(r, dict) else r for r in rows]


# ---------------------------------------------------------------------------
# Embedded schema fallback (for PyInstaller when file system paths break)
# ---------------------------------------------------------------------------

_EMBEDDED_SCHEMA = """
CREATE TABLE IF NOT EXISTS qd_users (
    id INTEGER PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT,
    nickname TEXT DEFAULT 'Trader',
    email TEXT,
    avatar TEXT DEFAULT '/avatar2.jpg',
    role TEXT DEFAULT 'admin',
    status TEXT DEFAULT 'active',
    email_verified INTEGER DEFAULT 1,
    token_version INTEGER DEFAULT 1,
    timezone TEXT DEFAULT '',
    notification_settings TEXT DEFAULT '{}',
    chart_templates TEXT DEFAULT '[]',
    referred_by INTEGER,
    last_login_at TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS qd_indicator_codes (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL DEFAULT 1,
    name TEXT NOT NULL,
    description TEXT DEFAULT '',
    code TEXT NOT NULL,
    language TEXT DEFAULT 'python',
    category TEXT DEFAULT 'custom',
    version INTEGER DEFAULT 1,
    publish_to_community INTEGER DEFAULT 0,
    review_status TEXT DEFAULT 'approved',
    review_note TEXT DEFAULT '',
    reviewed_by INTEGER,
    reviewed_at TEXT,
    updatetime TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES qd_users(id)
);

CREATE TABLE IF NOT EXISTS qd_strategies (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL DEFAULT 1,
    name TEXT NOT NULL,
    symbol TEXT NOT NULL,
    market TEXT NOT NULL DEFAULT 'Crypto',
    strategy_type TEXT DEFAULT 'IndicatorStrategy',
    indicator_id INTEGER,
    indicator_params TEXT DEFAULT '{}',
    trading_config TEXT DEFAULT '{}',
    exchange_config TEXT DEFAULT '{}',
    status TEXT DEFAULT 'stopped',
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES qd_users(id),
    FOREIGN KEY (indicator_id) REFERENCES qd_indicator_codes(id)
);

CREATE TABLE IF NOT EXISTS qd_trades (
    id INTEGER PRIMARY KEY,
    strategy_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL DEFAULT 1,
    symbol TEXT NOT NULL,
    market TEXT NOT NULL,
    side TEXT NOT NULL,
    price REAL NOT NULL,
    amount REAL NOT NULL,
    value REAL,
    commission REAL DEFAULT 0,
    profit REAL,
    trade_time TEXT DEFAULT (datetime('now')),
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (strategy_id) REFERENCES qd_strategies(id),
    FOREIGN KEY (user_id) REFERENCES qd_users(id)
);

CREATE TABLE IF NOT EXISTS qd_exchange_credentials (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL DEFAULT 1,
    exchange TEXT NOT NULL,
    name TEXT,
    encrypted_config TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES qd_users(id),
    UNIQUE(user_id, exchange, name)
);

CREATE TABLE IF NOT EXISTS qd_watchlist (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL DEFAULT 1,
    market TEXT NOT NULL,
    symbol TEXT NOT NULL,
    name TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES qd_users(id),
    UNIQUE(user_id, market, symbol)
);

CREATE TABLE IF NOT EXISTS qd_strategy_snapshots (
    id INTEGER PRIMARY KEY,
    strategy_id INTEGER NOT NULL,
    snapshot_data TEXT NOT NULL DEFAULT '{}',
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (strategy_id) REFERENCES qd_strategies(id)
);

CREATE TABLE IF NOT EXISTS qd_security_logs (
    id INTEGER PRIMARY KEY,
    user_id INTEGER,
    action TEXT NOT NULL,
    ip_address TEXT,
    user_agent TEXT,
    details TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS qd_login_attempts (
    id INTEGER PRIMARY KEY,
    identifier TEXT NOT NULL,
    identifier_type TEXT NOT NULL,
    success INTEGER NOT NULL DEFAULT 0,
    ip_address TEXT,
    user_agent TEXT,
    attempt_time TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS qd_verification_codes (
    id INTEGER PRIMARY KEY,
    email TEXT NOT NULL,
    code TEXT NOT NULL,
    code_type TEXT DEFAULT 'register',
    ip_address TEXT,
    expires_at TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS qd_polymarket_markets (
    id INTEGER PRIMARY KEY,
    market_id TEXT NOT NULL UNIQUE,
    title TEXT,
    volume REAL DEFAULT 0,
    liquidity REAL DEFAULT 0,
    outcomes TEXT DEFAULT '[]',
    end_date TEXT,
    raw_data TEXT DEFAULT '{}',
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS qd_license (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    license_key_hash TEXT NOT NULL,
    email TEXT,
    device_id TEXT,
    issued_at TEXT,
    expires_at TEXT,
    features TEXT DEFAULT '["all"]',
    activated_at TEXT DEFAULT (datetime('now'))
);

INSERT OR IGNORE INTO qd_users (id, username, nickname, role, status)
VALUES (1, 'trader', 'Trader', 'admin', 'active');

PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;
"""
```

- [ ] **Step 2: Run a quick local SQLite test**

```bash
python3 -c "
import os, sys
sys.path.insert(0, 'backend_api_python')
os.environ['DB_TYPE'] = 'sqlite'
os.environ['DB_PATH'] = '/tmp/test_quant.db'
from app.utils.db_sqlite import init_database, get_db_connection
init_database()
with get_db_connection() as db:
    cur = db.cursor()
    cur.execute('SELECT COUNT(*) as cnt FROM qd_users')
    print('Users:', cur.fetchone()['cnt'])
    cur.execute(\"SELECT name FROM sqlite_master WHERE type='table' ORDER BY name\")
    for row in cur.fetchall():
        print('  Table:', row['name'])
print('SQLite init OK')
"
```

Expected: Users=1, 13+ tables printed.

- [ ] **Step 3: Modify db.py to route by DB_TYPE**

Modify `backend_api_python/app/utils/db.py`:

Read the current file first, then replace the PostgreSQL-specific import block:

```python
# Replace the import block (around lines 19-32) with:
import os as _os

_db_type = _os.getenv("DB_TYPE", "postgresql").lower()

if _db_type == "sqlite":
    from app.utils.db_sqlite import (
        get_db_connection,
        get_db_connection_sync as get_pg_connection_sync,
        get_pg_connection,
        init_database,
        close_db_connection,
    )

    def get_db_type() -> str:
        return "sqlite"

    def is_postgres() -> bool:
        return False

else:
    from app.utils.db_postgres import (
        get_pg_connection as get_db_connection,
        get_pg_connection,
        get_pg_connection_sync as get_db_connection_sync,
        get_pg_connection_sync,
        init_database,
        close_db_connection,
    )

    def get_db_type() -> str:
        return "postgresql"

    def is_postgres() -> bool:
        return True
```

- [ ] **Step 4: Hook init_database into app factory**

Modify `backend_api_python/app/__init__.py` in `create_app()`, replace the existing database init block with:

```python
    # Initialize database (PostgreSQL or SQLite depending on DB_TYPE)
    try:
        from app.utils.db import init_database, get_db_type

        logger.info(f"Database type: {get_db_type()}")
        init_database()

        # Multi-user mode only for PostgreSQL; skip for SQLite desktop
        if get_db_type() == "postgresql":
            from app.services.user_service import get_user_service

            get_user_service().ensure_admin_exists()
    except Exception as e:
        logger.warning(f"Database initialization note: {e}")
```

- [ ] **Step 5: Commit**

```bash
git add backend_api_python/app/utils/db_sqlite.py backend_api_python/app/utils/db.py backend_api_python/app/__init__.py backend_api_python/migrations/init_sqlite.sql
git commit -m "feat: add SQLite database adapter for desktop edition

db_sqlite.py mirrors db_postgres.py interface with sqlite3 backend.
db.py now routes by DB_TYPE env var. init_database creates tables
from init_sqlite.sql and auto-seeds default user.
Embedded schema fallback for PyInstaller bundles."
```

---

## Task 3: Seed Data

**Files:**
- Create: `backend_api_python/app/data/seed.sql`

**Interfaces:**
- Produces: `seed.sql` — 10 strategy templates + default symbols. Consumed by `db_sqlite.py:_run_seed_data()`.

- [ ] **Step 1: Create seed.sql**

Create `backend_api_python/app/data/seed.sql`:

```sql
-- Mipham Quant Desktop — Seed Data
-- Inserted on first run when qd_indicator_codes is empty.

-- Strategy 1: Dual Moving Average Crossover
INSERT OR IGNORE INTO qd_indicator_codes (id, user_id, name, description, category, code, version)
VALUES (1, 1, '双均线交叉 (Dual MA Cross)',
    '当短期均线上穿长期均线时买入，下穿时卖出。经典趋势跟踪策略。',
    'Trend',
    '# @strategy name=双均线交叉
# @param ma_fast int 5 短期均线周期
# @param ma_slow int 20 长期均线周期

def on_init(ctx):
    ctx.param("ma_fast", 5)
    ctx.param("ma_slow", 20)

def on_bar(ctx, bar):
    fast = ctx.param("ma_fast")
    slow = ctx.param("ma_slow")
    bars = ctx.bars(max(slow, 100))
    if len(bars) < slow + 1:
        return
    closes = [b.close for b in bars]
    ma_fast_val = sum(closes[-fast:]) / fast
    ma_slow_val = sum(closes[-slow:]) / slow
    ma_fast_prev = sum(closes[-fast-1:-1]) / fast
    ma_slow_prev = sum(closes[-slow-1:-1]) / slow

    if ma_fast_prev < ma_slow_prev and ma_fast_val >= ma_slow_val:
        ctx.buy(bar.close, ctx.param("amount", 100))
    elif ma_fast_prev > ma_slow_prev and ma_fast_val <= ma_slow_val:
        ctx.sell(bar.close, ctx.param("amount", 100))
', 1);

-- Strategy 2: MACD Signal
INSERT OR IGNORE INTO qd_indicator_codes (id, user_id, name, description, category, code, version)
VALUES (2, 1, 'MACD 信号 (MACD Signal)',
    'MACD金叉买入，死叉卖出。使用EMA12和EMA26计算。',
    'Momentum',
    '# @strategy name=MACD信号
# @param fast int 12 快线周期
# @param slow int 26 慢线周期
# @param signal int 9 信号线周期

def on_init(ctx):
    ctx.param("fast", 12)
    ctx.param("slow", 26)
    ctx.param("signal", 9)

def ema(data, period):
    k = 2.0 / (period + 1)
    result = [data[0]]
    for i in range(1, len(data)):
        result.append(data[i] * k + result[-1] * (1 - k))
    return result

def on_bar(ctx, bar):
    fast_p = ctx.param("fast")
    slow_p = ctx.param("slow")
    sig_p = ctx.param("signal")
    bars = ctx.bars(max(slow_p + sig_p, 200))
    if len(bars) < slow_p + sig_p + 1:
        return
    closes = [b.close for b in bars]
    ema_fast = ema(closes, fast_p)
    ema_slow = ema(closes, slow_p)
    diffs = [f - s for f, s in zip(ema_fast, ema_slow)]
    dea = ema(diffs, sig_p)
    macd = 2 * (diffs[-1] - dea[-1])
    macd_prev = 2 * (diffs[-2] - dea[-2])

    if macd_prev < 0 and macd >= 0:
        ctx.buy(bar.close, ctx.param("amount", 100))
    elif macd_prev > 0 and macd <= 0:
        ctx.sell(bar.close, ctx.param("amount", 100))
', 1);

-- Strategy 3: RSI Oversold/Overbought
INSERT OR IGNORE INTO qd_indicator_codes (id, user_id, name, description, category, code, version)
VALUES (3, 1, 'RSI 超买超卖 (RSI Mean Reversion)',
    'RSI低于30超卖买入，高于70超买卖出。均值回归策略。',
    'Mean Reversion',
    '# @strategy name=RSI超买超卖
# @param period int 14 RSI周期
# @param oversold int 30 超卖阈值
# @param overbought int 70 超买阈值

def on_init(ctx):
    ctx.param("period", 14)
    ctx.param("oversold", 30)
    ctx.param("overbought", 70)

def calc_rsi(closes, period):
    gains = [max(0, closes[i] - closes[i-1]) for i in range(1, len(closes))]
    losses = [max(0, closes[i-1] - closes[i]) for i in range(1, len(closes))]
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    if avg_loss == 0:
        return 100.0
    return 100.0 - (100.0 / (1.0 + avg_gain / avg_loss))

def on_bar(ctx, bar):
    period = ctx.param("period")
    bars = ctx.bars(period + 10)
    if len(bars) < period + 1:
        return
    closes = [b.close for b in bars]
    rsi = calc_rsi(closes, period)
    if rsi < ctx.param("oversold"):
        ctx.buy(bar.close, ctx.param("amount", 100))
    elif rsi > ctx.param("overbought"):
        ctx.sell(bar.close, ctx.param("amount", 100))
', 1);

-- Strategy 4: Bollinger Bands Breakout
INSERT OR IGNORE INTO qd_indicator_codes (id, user_id, name, description, category, code, version)
VALUES (4, 1, '布林带突破 (Bollinger Bands Breakout)',
    '价格突破上轨买入，跌破下轨卖出。波动率突破策略。',
    'Volatility',
    '# @strategy name=布林带突破
# @param period int 20 均线周期
# @param stddev float 2.0 标准差倍数

def on_init(ctx):
    ctx.param("period", 20)
    ctx.param("stddev", 2.0)

def on_bar(ctx, bar):
    period = ctx.param("period")
    bars = ctx.bars(period + 5)
    if len(bars) < period:
        return
    closes = [b.close for b in bars]
    sma = sum(closes[-period:]) / period
    variance = sum((c - sma) ** 2 for c in closes[-period:]) / period
    std = variance ** 0.5
    mult = ctx.param("stddev")
    upper = sma + mult * std
    lower = sma - mult * std

    prev_close = closes[-2] if len(closes) > 1 else closes[-1]
    if prev_close < upper and closes[-1] >= upper:
        ctx.buy(bar.close, ctx.param("amount", 100))
    elif prev_close > lower and closes[-1] <= lower:
        ctx.sell(bar.close, ctx.param("amount", 100))
', 1);

-- Strategy 5: Turtle Trading
INSERT OR IGNORE INTO qd_indicator_codes (id, user_id, name, description, category, code, version)
VALUES (5, 1, '海龟交易 (Turtle Trading)',
    '突破N日高点买入，跌破N日低点卖出。经典趋势跟踪。',
    'Trend',
    '# @strategy name=海龟交易
# @param entry int 20 入场突破周期
# @param exit int 10 离场突破周期

def on_init(ctx):
    ctx.param("entry", 20)
    ctx.param("exit", 10)

def on_bar(ctx, bar):
    entry = ctx.param("entry")
    exit_p = ctx.param("exit")
    bars = ctx.bars(entry + 5)
    if len(bars) < entry:
        return
    highs = [b.high for b in bars]
    lows = [b.low for b in bars]
    entry_high = max(highs[-entry-1:-1])
    exit_low = min(lows[-exit_p-1:-1])

    if bar.close > entry_high:
        ctx.buy(bar.close, ctx.param("amount", 100))
    elif bar.close < exit_low:
        ctx.sell(bar.close, ctx.param("amount", 100))
', 1);

-- Strategy 6: Grid Trading
INSERT OR IGNORE INTO qd_indicator_codes (id, user_id, name, description, category, code, version)
VALUES (6, 1, '网格交易 (Grid Trading)',
    '在价格区间内设置买卖网格，震荡市中低买高卖。',
    'Grid',
    '# @strategy name=网格交易
# @param grid_size float 0.5 网格间距百分比
# @param grid_levels int 5 网格层数

def on_init(ctx):
    ctx.param("grid_size", 0.5)
    ctx.param("grid_levels", 5)
    ctx.param("last_price", 0.0)

def on_bar(ctx, bar):
    size = ctx.param("grid_size") / 100.0
    levels = ctx.param("grid_levels")
    last = ctx.param("last_price")
    if last == 0.0:
        ctx.param("last_price", bar.close)
        return
    if bar.close < last * (1.0 - size):
        ctx.buy(bar.close, ctx.param("amount", 50))
        ctx.param("last_price", bar.close)
    elif bar.close > last * (1.0 + size):
        ctx.sell(bar.close, ctx.param("amount", 50))
        ctx.param("last_price", bar.close)
', 1);

-- Strategy 7: Momentum Timing
INSERT OR IGNORE INTO qd_indicator_codes (id, user_id, name, description, category, code, version)
VALUES (7, 1, '动量择时 (Momentum Timing)',
    '计算N日动量，动量为正买入，为负卖出。',
    'Momentum',
    '# @strategy name=动量择时
# @param period int 10 动量周期

def on_init(ctx):
    ctx.param("period", 10)

def on_bar(ctx, bar):
    period = ctx.param("period")
    bars = ctx.bars(period + 2)
    if len(bars) < period + 1:
        return
    momentum = bar.close - bars[-period-1].close
    if momentum > 0:
        ctx.buy(bar.close, ctx.param("amount", 100))
    elif momentum < 0:
        ctx.sell(bar.close, ctx.param("amount", 100))
', 1);

-- Strategy 8: Volatility Contraction
INSERT OR IGNORE INTO qd_indicator_codes (id, user_id, name, description, category, code, version)
VALUES (8, 1, '波动率收敛 (Volatility Contraction)',
    '当波动率收缩到低点时入场，预期后续突破。',
    'Volatility',
    '# @strategy name=波动率收敛
# @param period int 20 计算周期
# @param threshold float 0.5 波动率阈值

def on_init(ctx):
    ctx.param("period", 20)
    ctx.param("threshold", 0.5)

def on_bar(ctx, bar):
    period = ctx.param("period")
    bars = ctx.bars(period * 2)
    if len(bars) < period * 2:
        return
    highs = [b.high for b in bars[-period:]]
    lows = [b.low for b in bars[-period:]]
    curr_range = max(highs) - min(lows)
    prev_highs = [b.high for b in bars[-2*period:-period]]
    prev_lows = [b.low for b in bars[-2*period:-period]]
    prev_range = max(prev_highs) - min(prev_lows) if prev_highs else curr_range

    if prev_range > 0 and curr_range / prev_range < ctx.param("threshold"):
        ctx.buy(bar.close, ctx.param("amount", 100))
', 1);

-- Strategy 9: OBV Divergence
INSERT OR IGNORE INTO qd_indicator_codes (id, user_id, name, description, category, code, version)
VALUES (9, 1, 'OBV 背离 (OBV Divergence)',
    '价格新低但OBV未创新低 = 看涨背离。量价背离策略。',
    'Volume',
    '# @strategy name=OBV背离
# @param period int 14 比较周期

def on_init(ctx):
    ctx.param("period", 14)
    ctx.param("obv", 0.0)
    ctx.param("obvs", [])

def on_bar(ctx, bar):
    period = ctx.param("period")
    obv = ctx.param("obv")
    if obv == 0:
        ctx.param("obv", bar.volume)
        return
    prev_close = ctx.bars(2)[0].close if len(ctx.bars(2)) > 1 else bar.close
    new_obv = obv + (bar.volume if bar.close > prev_close else (-bar.volume if bar.close < prev_close else 0))
    obvs = ctx.param("obvs")
    obvs.append(new_obv)
    if len(obvs) > period * 2:
        obvs = obvs[-period*2:]
    ctx.param("obvs", obvs)
    ctx.param("obv", new_obv)

    if len(obvs) >= period * 2:
        price_now = bar.close
        price_prev = ctx.bars(period + 1)[0].close
        obv_now = max(obvs[-period:])
        obv_prev = max(obvs[-2*period:-period])
        if price_now < price_prev and obv_now > obv_prev:
            ctx.buy(bar.close, ctx.param("amount", 100))
', 1);

-- Strategy 10: Multi-Factor Composite
INSERT OR IGNORE INTO qd_indicator_codes (id, user_id, name, description, category, code, version)
VALUES (10, 1, '多因子综合 (Multi-Factor Composite)',
    '综合趋势、动量、波动率三个因子打分，分数>0买入，<0卖出。',
    'Composite',
    '# @strategy name=多因子综合

def on_init(ctx):
    ctx.param("trend_weight", 0.4)
    ctx.param("momentum_weight", 0.35)
    ctx.param("volatility_weight", 0.25)

def on_bar(ctx, bar):
    bars = ctx.bars(30)
    if len(bars) < 30:
        return
    closes = [b.close for b in bars]

    ma_short = sum(closes[-5:]) / 5
    ma_long = sum(closes[-20:]) / 20
    trend_score = 1 if ma_short > ma_long else -1

    momentum = closes[-1] - closes[-10]
    momentum_score = 1 if momentum > 0 else -1

    returns = [(closes[i] - closes[i-1]) / closes[i-1] for i in range(1, len(closes))]
    avg_ret = sum(returns[-20:]) / 20
    volatility = (sum((r - avg_ret) ** 2 for r in returns[-20:]) / 20) ** 0.5
    vol_score = -1 if volatility > 0.02 else 1

    composite = (
        trend_score * ctx.param("trend_weight") +
        momentum_score * ctx.param("momentum_weight") +
        vol_score * ctx.param("volatility_weight")
    )

    if composite > 0:
        ctx.buy(bar.close, ctx.param("amount", 100))
    elif composite < 0:
        ctx.sell(bar.close, ctx.param("amount", 100))
', 1);

-- Default watchlist symbols
INSERT OR IGNORE INTO qd_watchlist (user_id, market, symbol, name)
VALUES
    (1, 'Crypto', 'BTC/USDT', 'Bitcoin'),
    (1, 'Crypto', 'ETH/USDT', 'Ethereum'),
    (1, 'Crypto', 'BNB/USDT', 'BNB'),
    (1, 'Crypto', 'SOL/USDT', 'Solana'),
    (1, 'CN', '000300', '沪深300'),
    (1, 'CN', '000016', '上证50'),
    (1, 'US', 'AAPL', 'Apple'),
    (1, 'US', 'TSLA', 'Tesla'),
    (1, 'US', 'SPY', 'SPDR S&P 500'),
    (1, 'US', 'QQQ', 'Invesco QQQ Trust');
```

- [ ] **Step 2: Test seed data loading**

```bash
rm -f /tmp/test_quant_seed.db
python3 -c "
import os, sys
sys.path.insert(0, 'backend_api_python')
os.environ['DB_TYPE'] = 'sqlite'
os.environ['DB_PATH'] = '/tmp/test_quant_seed.db'
from app.utils.db_sqlite import init_database, get_db_connection
init_database()
with get_db_connection() as db:
    cur = db.cursor()
    cur.execute('SELECT COUNT(*) as cnt FROM qd_indicator_codes')
    print('Strategies:', cur.fetchone()['cnt'])
    cur.execute('SELECT COUNT(*) as cnt FROM qd_watchlist')
    print('Watchlist:', cur.fetchone()['cnt'])
    cur.execute('SELECT name FROM qd_indicator_codes ORDER BY id')
    for row in cur.fetchall():
        print('  -', row['name'])
print('Seed data OK')
"
```

Expected: 10 strategies, 10 watchlist items, all listed.

- [ ] **Step 3: Commit**

```bash
git add backend_api_python/app/data/seed.sql
git commit -m "feat: add seed data — 10 strategy templates + 10 watchlist symbols

Strategies: dual MA, MACD, RSI, Bollinger, Turtle, Grid, Momentum,
Volatility Contraction, OBV Divergence, Multi-Factor Composite.
Watchlist: BTC/ETH/BNB/SOL, CSI300/SSE50, AAPL/TSLA/SPY/QQQ."
```

---

## Task 4: Backend Single-User Mode & Desktop Config

**Files:**
- Modify: `backend_api_python/app/config/settings.py`
- Modify: `backend_api_python/app/utils/auth.py`
- Modify: `backend_api_python/run.py`

**Interfaces:**
- Consumes: SQLite adapter from Task 2
- Produces: `SINGLE_USER_MODE=true` default, `login_required` bypass, desktop banner

- [ ] **Step 1: Set desktop defaults in settings.py**

Modify `backend_api_python/app/config/settings.py`:

Change the `SINGLE_USER_MODE` related section. The class properties to modify:

```python
    @property
    def SINGLE_USER_MODE(cls):
        # Desktop: single-user mode by default when DB_TYPE is sqlite
        if os.getenv("DB_TYPE", "").lower() == "sqlite":
            return True
        return os.getenv("SINGLE_USER_MODE", "false").lower() == "true"

    @property
    def HOST(cls):
        # Desktop: force localhost binding
        if os.getenv("DB_TYPE", "").lower() == "sqlite":
            return "127.0.0.1"
        return os.getenv("PYTHON_API_HOST", "0.0.0.0")

    @property
    def SECRET_KEY(cls):
        # Desktop: auto-generate a random key if not set
        key = os.getenv("SECRET_KEY", "").strip()
        if not key:
            import secrets
            key = secrets.token_hex(32)
            os.environ["SECRET_KEY"] = key
        return key
```

- [ ] **Step 2: Bypass login_required in single-user mode**

Modify `backend_api_python/app/utils/auth.py`, in the `login_required` decorator:

Add this at the top of the `decorated` function, before the token check:

```python
    @wraps(f)
    def decorated(*args, **kwargs):
        # Desktop single-user mode: skip authentication
        if _is_single_user_mode():
            g.user = "trader"
            g.user_id = 1
            g.user_role = "admin"
            return f(*args, **kwargs)

        token = None
        # ... rest unchanged
```

- [ ] **Step 3: Add desktop startup banner in run.py**

Modify `backend_api_python/run.py`, in the `main()` function, change the print statement:

```python
def main():
    """启动应用"""
    db_type = os.getenv("DB_TYPE", "postgresql")
    if db_type == "sqlite":
        print("Mipham Quant Desktop v1.0.0 — 桌面版")
        print(f"数据位置: {os.getenv('DB_PATH', 'data/quant.db')}")
    else:
        print("Mipham Quant v0.1.0 — AI 量化交易平台")
    # ... rest unchanged
```

- [ ] **Step 4: Verify single-user mode**

```bash
rm -f /tmp/test_quant_su.db
python3 -c "
import os, sys
sys.path.insert(0, 'backend_api_python')
os.environ['DB_TYPE'] = 'sqlite'
os.environ['DB_PATH'] = '/tmp/test_quant_su.db'
os.environ['SECRET_KEY'] = 'test-secret-for-ci'
from app import create_app
app = create_app()
with app.test_client() as c:
    # Should work without token in single-user mode
    resp = c.get('/api/auth/info')
    print('Status:', resp.status_code)
    print('Data:', resp.get_json())
print('Single-user mode OK')
"
```

Expected: 200 OK with user info, no token required.

- [ ] **Step 5: Commit**

```bash
git add backend_api_python/app/config/settings.py backend_api_python/app/utils/auth.py backend_api_python/run.py
git commit -m "feat: single-user desktop mode — bypass auth when DB_TYPE=sqlite

settings.py auto-detects SQLite mode: binds 127.0.0.1, enables
single-user, generates SECRET_KEY if empty. login_required decorator
skips JWT verification in single-user mode. run.py shows desktop banner."
```

---

## Task 5: Frontend Desktop Adaptations

**Files:**
- Modify: `apps/frontend/vite.config.ts`
- Modify: `apps/frontend/src/router/index.ts`
- Modify: `apps/frontend/src/api/client.ts`
- Modify: `apps/frontend/src/stores/auth.ts`
- Modify: `apps/frontend/src/layouts/BasicLayout.vue`

**Interfaces:**
- Consumes: Backend changes from Task 4 (single-user API)
- Produces: Desktop-ready SPA with file:// compatibility, hash routing, local API base URL

- [ ] **Step 1: Update vite.config.ts for file:// protocol**

Modify `apps/frontend/vite.config.ts`:

```typescript
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'
import { resolve } from 'path'

export default defineConfig({
  plugins: [vue(), tailwindcss()],
  // Use relative paths for file:// protocol compatibility
  base: './',
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:5000',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: '../../frontend/dist',
    emptyOutDir: true,
  },
})
```

- [ ] **Step 2: Switch router to hash mode**

Modify `apps/frontend/src/router/index.ts`:

```typescript
import { createRouter, createWebHashHistory } from 'vue-router'
import BasicLayout from '@/layouts/BasicLayout.vue'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/auth/Login.vue'),
  },
  {
    path: '/',
    component: BasicLayout,
    children: [
      { path: '', name: 'Dashboard', component: () => import('@/views/dashboard/Dashboard.vue') },
      { path: 'chart/:market?/:symbol?', name: 'Chart', component: () => import('@/views/chart/Chart.vue') },
      { path: 'strategy', name: 'Strategy', component: () => import('@/views/strategy/Strategy.vue') },
      { path: 'backtest', name: 'Backtest', component: () => import('@/views/backtest/Backtest.vue') },
      { path: 'news', name: 'News', component: () => import('@/views/news/News.vue') },
    ],
  },
]

const router = createRouter({
  // Hash mode required for file:// protocol (Electron)
  history: createWebHashHistory(),
  routes,
})

export default router
```

- [ ] **Step 3: Point API client to localhost**

Modify `apps/frontend/src/api/client.ts`:

```typescript
import axios from 'axios'

const api = axios.create({
  // Desktop: Flask backend runs on localhost:5000
  baseURL: 'http://127.0.0.1:5000/api',
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
})

// Desktop single-user mode: no token needed for local access
// Keep interceptor for future multi-user support
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('token')
      // Desktop: don't redirect, just clear state
    }
    return Promise.reject(err)
  },
)

export default api
```

- [ ] **Step 4: Simplify auth store for offline mode**

Modify `apps/frontend/src/stores/auth.ts`:

```typescript
import { defineStore } from 'pinia'

interface User {
  id: number
  username: string
  nickname: string
  avatar: string
  role: string
}

// Desktop: instant local user, no login flow
const DEFAULT_USER: User = {
  id: 1,
  username: 'trader',
  nickname: 'Trader',
  avatar: '/avatar2.jpg',
  role: 'admin',
}

export const useAuthStore = defineStore('auth', {
  state: () => ({
    user: { ...DEFAULT_USER } as User | null,
    token: 'desktop-local',
  }),
  getters: {
    isLoggedIn: () => true, // Desktop: always logged in
  },
  actions: {
    async login(_username: string, _password: string) {
      // Desktop: no-op, already logged in
    },
    async fetchUser() {
      // Try to fetch from local backend for consistency
      try {
        const api = (await import('@/api/client')).default
        const { data } = await api.get('/auth/info')
        if (data?.code === 1) {
          this.user = data.data
        }
      } catch {
        // Offline: use default user
      }
    },
    logout() {
      // Desktop: never truly log out
    },
  },
})
```

- [ ] **Step 5: Add desktop title bar to layout**

Modify `apps/frontend/src/layouts/BasicLayout.vue`, change the footer text:

```html
<a-layout-footer style="text-align:center;">
  Mipham Quant Desktop v1.0.0 ©2026 One Mipham Corporation
</a-layout-footer>
```

- [ ] **Step 6: Build and verify**

```bash
cd apps/frontend && pnpm install && pnpm build
```

Verify `frontend/dist/index.html` has relative paths (`./assets/...`):

```bash
head -5 frontend/dist/index.html
```

Expected: `<script type="module" crossorigin src="./assets/...` (NOT `/assets/...`)

- [ ] **Step 7: Commit**

```bash
git add apps/frontend/vite.config.ts apps/frontend/src/router/index.ts apps/frontend/src/api/client.ts apps/frontend/src/stores/auth.ts apps/frontend/src/layouts/BasicLayout.vue frontend/dist/
git commit -m "feat: adapt frontend for Electron desktop

vite.config.ts: base='./' for file:// protocol compatibility.
router: createWebHashHistory for hash-mode routing.
client.ts: baseURL points to localhost:5000.
auth store: instant local user, no login flow required.
BasicLayout: desktop version footer."
```

---

## Task 6: Electron Shell — Main Process & Preload

**Files:**
- Create: `electron/main.ts`
- Create: `electron/preload.ts`
- Modify: `package.json` (root)
- Create: `electron/tsconfig.json`

**Interfaces:**
- Produces: Electron main process that creates BrowserWindow, loads frontend, manages lifecycle
- Consumes: Frontend build from Task 5

- [ ] **Step 1: Install Electron dependencies**

```bash
pnpm add -D electron electron-builder typescript @types/node
pnpm add electron-store
```

- [ ] **Step 2: Create electron/main.ts**

Create `electron/main.ts`:

```typescript
import { app, BrowserWindow, screen } from 'electron'
import * as path from 'path'

let mainWindow: BrowserWindow | null = null

function createWindow(): void {
  const { width: screenW, height: screenH } = screen.getPrimaryDisplay().workAreaSize

  mainWindow = new BrowserWindow({
    width: Math.min(1400, screenW),
    height: Math.min(900, screenH),
    minWidth: 1024,
    minHeight: 680,
    title: 'Mipham Quant',
    icon: path.join(__dirname, '..', 'resources', 'icon.png'),
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
    // macOS: hide instead of close
    ...(process.platform === 'darwin'
      ? { titleBarStyle: 'hiddenInset' }
      : {}),
  })

  // Load frontend
  const isDev = process.env.NODE_ENV === 'development'
  if (isDev) {
    mainWindow.loadURL('http://localhost:5173')
    mainWindow.webContents.openDevTools()
  } else {
    mainWindow.loadFile(path.join(__dirname, '..', 'frontend', 'dist', 'index.html'))
  }

  mainWindow.on('closed', () => {
    mainWindow = null
  })
}

app.whenReady().then(createWindow)

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit()
  }
})

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    createWindow()
  }
})
```

- [ ] **Step 3: Create electron/preload.ts**

Create `electron/preload.ts`:

```typescript
import { contextBridge, ipcRenderer } from 'electron'

// Expose minimal, safe API to the renderer process.
// All communication goes through IPC — no direct Node.js access.
contextBridge.exposeInMainWorld('electronAPI', {
  // App info
  getVersion: () => ipcRenderer.invoke('app:getVersion'),
  getPlatform: () => process.platform,

  // License
  activateLicense: (key: string) => ipcRenderer.invoke('license:activate', key),
  getLicenseStatus: () => ipcRenderer.invoke('license:status'),

  // Backend status
  getBackendStatus: () => ipcRenderer.invoke('backend:status'),

  // Notifications
  onBackendReady: (callback: () => void) => {
    ipcRenderer.on('backend:ready', callback)
  },
  onBackendError: (callback: (msg: string) => void) => {
    ipcRenderer.on('backend:error', (_event, msg) => callback(msg))
  },
})
```

- [ ] **Step 4: Create electron/tsconfig.json**

Create `electron/tsconfig.json`:

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "commonjs",
    "moduleResolution": "node",
    "outDir": "../dist-electron",
    "rootDir": ".",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true,
    "resolveJsonModule": true,
    "declaration": false,
    "sourceMap": true
  },
  "include": ["./**/*.ts"]
}
```

- [ ] **Step 5: Update root package.json**

Modify root `package.json` — add Electron scripts and build config:

```json
{
  "name": "mipham-quant-desktop",
  "version": "1.0.0",
  "private": true,
  "description": "Mipham Quant — AI Quantitative Trading Desktop",
  "main": "dist-electron/main.js",
  "author": "One Mipham Corporation",
  "license": "Proprietary",
  "scripts": {
    "electron:dev": "NODE_ENV=development tsc -p electron/tsconfig.json && electron .",
    "electron:build:ts": "tsc -p electron/tsconfig.json",
    "electron:build:frontend": "cd apps/frontend && pnpm build",
    "electron:build": "pnpm electron:build:ts && pnpm electron:build:frontend && electron-builder",
    "electron:build:mac": "pnpm electron:build:ts && pnpm electron:build:frontend && electron-builder --mac",
    "electron:build:win": "pnpm electron:build:ts && pnpm electron:build:frontend && electron-builder --win"
  },
  "build": {
    "appId": "com.onemipham.mipham-quant",
    "productName": "Mipham Quant",
    "directories": {
      "output": "dist"
    },
    "files": [
      "dist-electron/**/*",
      "frontend/dist/**/*",
      "resources/**/*"
    ],
    "extraResources": [
      {
        "from": "backend_api_python/dist/",
        "to": "backend/"
      }
    ],
    "mac": {
      "category": "public.app-category.finance",
      "target": ["dmg", "zip"],
      "icon": "resources/icon.icns"
    },
    "win": {
      "target": ["nsis"],
      "icon": "resources/icon.ico"
    },
    "nsis": {
      "oneClick": false,
      "allowToChangeInstallationDirectory": true,
      "installerIcon": "resources/icon.ico"
    }
  },
  "devDependencies": {
    "electron": "^34.0.0",
    "electron-builder": "^25.0.0",
    "typescript": "~5.7.0",
    "@types/node": "^22.0.0"
  },
  "dependencies": {
    "electron-store": "^10.0.0"
  }
}
```

- [ ] **Step 6: Create placeholder icon**

```bash
# Generate a simple placeholder PNG icon (will be replaced with real icon later)
python3 -c "
import struct, zlib
# Minimal 128x128 blue PNG
width, height = 128, 128
raw = b''
for y in range(height):
    raw += b'\x00'  # filter byte
    for x in range(width):
        # Blue gradient with MQ text area
        r, g, b, a = 0x00, 0x16, 0x52, 0xFF
        raw += struct.pack('BBBB', r, g, b, a)
compressed = zlib.compress(raw)
png = b'\x89PNG\r\n\x1a\n' + \
    struct.pack('>I', 13) + b'IHDR' + struct.pack('>IIBBBBB', width, height, 8, 6, 0, 0, 0) + struct.pack('>I', zlib.crc32(b'IHDR' + struct.pack('>IIBBBBB', width, height, 8, 6, 0, 0, 0))) + \
    struct.pack('>I', len(compressed)) + b'IDAT' + compressed + struct.pack('>I', zlib.crc32(b'IDAT' + compressed)) + \
    struct.pack('>I', 0) + b'IEND' + struct.pack('>I', zlib.crc32(b'IEND'))
open('resources/icon.png', 'wb').write(png)
print('Icon created')
"
```

- [ ] **Step 7: Compile and verify**

```bash
pnpm tsc -p electron/tsconfig.json
ls dist-electron/main.js dist-electron/preload.js
```

Expected: Both files exist as compiled JS.

- [ ] **Step 8: Commit**

```bash
git add electron/ package.json pnpm-lock.yaml resources/
git commit -m "feat: add Electron shell — main process, preload, build config

main.ts: BrowserWindow creation, dev/production mode loading.
preload.ts: IPC bridge (app info, license, backend status).
package.json: electron-builder config for mac (.dmg) + win (.nsis).
Placeholder icon created."
```

---

## Task 7: Python Backend Manager (Sidecar)

**Files:**
- Create: `electron/backend.ts`

**Interfaces:**
- Consumes: none (free-standing module)
- Produces: `BackendManager` class — `start()`, `stop()`, `restart()`, `isReady()`

- [ ] **Step 1: Create electron/backend.ts**

Create `electron/backend.ts`:

```typescript
import { spawn, ChildProcess } from 'child_process'
import * as path from 'path'
import * as http from 'http'
import { app } from 'electron'

const BACKEND_PORT = 5000
const HEALTH_URL = `http://127.0.0.1:${BACKEND_PORT}/api/health`
const MAX_RETRIES = 3
const HEALTH_POLL_MS = 500
const HEALTH_TIMEOUT_MS = 30000

export class BackendManager {
  private process: ChildProcess | null = null
  private crashCount = 0
  private _ready = false

  get isReady(): boolean {
    return this._ready
  }

  async start(): Promise<void> {
    if (this.process) return

    const isDev = process.env.NODE_ENV === 'development'
    const userDataPath = app.getPath('userData')

    let cmd: string
    let args: string[]

    if (isDev) {
      cmd = 'python3'
      args = [path.join(__dirname, '..', 'backend_api_python', 'run.py')]
    } else {
      // Production: PyInstaller binary in extraResources
      const backendDir = path.join(process.resourcesPath, 'backend')
      if (process.platform === 'win32') {
        cmd = path.join(backendDir, 'mipham-quant-backend.exe')
      } else {
        cmd = path.join(backendDir, 'mipham-quant-backend')
      }
      args = []
    }

    const env = {
      ...process.env,
      DB_TYPE: 'sqlite',
      DB_PATH: path.join(userDataPath, 'quant.db'),
      PYTHON_API_HOST: '127.0.0.1',
      PYTHON_API_PORT: String(BACKEND_PORT),
      PYTHON_API_DEBUG: isDev ? 'true' : 'false',
      SINGLE_USER_MODE: 'true',
      ENABLE_CACHE: 'false',
      ENABLE_REGISTRATION: 'false',
      // Bypass proxy for local
      PROXY_URL: '',
      // Generate a local SECRET_KEY if not already set
      SECRET_KEY: process.env.SECRET_KEY || require('crypto').randomBytes(32).toString('hex'),
    }

    console.log(`[Backend] Starting: ${cmd} ${args.join(' ')}`)
    console.log(`[Backend] DB_PATH: ${env.DB_PATH}`)

    this.process = spawn(cmd, args, {
      env,
      stdio: ['ignore', 'pipe', 'pipe'],
    })

    this.process.stdout?.on('data', (data: Buffer) => {
      console.log(`[Backend] ${data.toString().trim()}`)
    })

    this.process.stderr?.on('data', (data: Buffer) => {
      console.error(`[Backend:err] ${data.toString().trim()}`)
    })

    this.process.on('exit', (code, signal) => {
      console.log(`[Backend] Process exited: code=${code} signal=${signal}`)
      this._ready = false
      if (code !== 0 && code !== null) {
        this.crashCount++
        if (this.crashCount < MAX_RETRIES) {
          console.log(`[Backend] Auto-restart attempt ${this.crashCount}/${MAX_RETRIES}`)
          setTimeout(() => this.start(), 2000)
        }
      }
    })

    // Wait for backend to be healthy
    await this._waitForHealth()
  }

  async stop(): Promise<void> {
    if (!this.process) return

    return new Promise((resolve) => {
      const timeout = setTimeout(() => {
        if (this.process) {
          console.log('[Backend] Force kill after timeout')
          this.process.kill('SIGKILL')
        }
        resolve()
      }, 5000)

      this.process!.on('exit', () => {
        clearTimeout(timeout)
        this.process = null
        this._ready = false
        resolve()
      })

      this.process!.kill('SIGTERM')
    })
  }

  async restart(): Promise<void> {
    await this.stop()
    this.crashCount = 0
    await this.start()
  }

  private _waitForHealth(): Promise<void> {
    return new Promise((resolve, reject) => {
      const startTime = Date.now()

      const poll = () => {
        if (Date.now() - startTime > HEALTH_TIMEOUT_MS) {
          reject(new Error('Backend health check timed out'))
          return
        }

        http.get(HEALTH_URL, (res) => {
          if (res.statusCode === 200) {
            this._ready = true
            this.crashCount = 0
            console.log('[Backend] Ready!')
            resolve()
          } else {
            setTimeout(poll, HEALTH_POLL_MS)
          }
        }).on('error', () => {
          setTimeout(poll, HEALTH_POLL_MS)
        })
      }

      poll()
    })
  }
}
```

- [ ] **Step 2: Wire BackendManager into main.ts**

Modify `electron/main.ts` to integrate BackendManager:

```typescript
import { app, BrowserWindow, screen, ipcMain } from 'electron'
import * as path from 'path'
import { BackendManager } from './backend'

let mainWindow: BrowserWindow | null = null
const backend = new BackendManager()

function createWindow(): void {
  // ... same as before ...
}

// Start backend before creating window
async function bootstrap(): Promise<void> {
  try {
    await backend.start()
  } catch (err) {
    console.error('Failed to start backend:', err)
    // Show error in window later
  }

  createWindow()

  // IPC handlers
  ipcMain.handle('backend:status', () => backend.isReady)
  ipcMain.handle('app:getVersion', () => app.getVersion())
  ipcMain.handle('app:getPlatform', () => process.platform)
}

app.whenReady().then(bootstrap)

app.on('before-quit', async () => {
  await backend.stop()
})

app.on('window-all-closed', () => {
  // Don't quit on window close — keep running in tray (Task 9)
})

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    createWindow()
  }
})
```

- [ ] **Step 3: Recompile and verify**

```bash
pnpm tsc -p electron/tsconfig.json
```

Expected: No errors.

- [ ] **Step 4: Commit**

```bash
git add electron/backend.ts electron/main.ts
git commit -m "feat: add Python backend manager (sidecar lifecycle)

BackendManager: spawns Python/Flask as child process, health-polling,
auto-restart on crash (max 3 retries), graceful shutdown.
Wired into main.ts bootstrap sequence."
```

---

## Task 8: License System

**Files:**
- Create: `electron/license.ts`
- Create: `scripts/generate-license.py`
- Modify: `electron/main.ts` (IPC handlers)
- Modify: `electron/preload.ts` (already has handlers)

**Interfaces:**
- Produces: `activateLicense(key) -> bool`, `checkLicense() -> bool`, `getLicenseInfo() -> object`
- Consumes: Node.js `crypto` module

- [ ] **Step 1: Create electron/license.ts**

Create `electron/license.ts`:

```typescript
import * as crypto from 'crypto'
import * as fs from 'fs'
import * as path from 'path'
import { app } from 'electron'

// ⚠️  PUBLIC KEY ONLY — embedded in the app.
// The PRIVATE KEY stays with the license generator script (never shipped).
//
// GENERATE THE REAL KEY:
//   1. Run: python3 -c "
//      from cryptography.hazmat.primitives.asymmetric import rsa
//      from cryptography.hazmat.primitives import serialization
//      private = rsa.generate_private_key(65537, 2048)
//      with open('license_private.pem','wb') as f:
//          f.write(private.private_bytes(encoding=serialization.Encoding.PEM,
//              format=serialization.PrivateFormat.PKCS8,
//              encryption_algorithm=serialization.NoEncryption()))
//      print(private.public_key().public_bytes(
//          encoding=serialization.Encoding.PEM,
//          format=serialization.PublicFormat.SubjectPublicKeyInfo).decode())"
//   2. Copy the output (-----BEGIN PUBLIC KEY----- ... -----END PUBLIC KEY-----)
//   3. Paste it below, replacing this placeholder.
const PUBLIC_KEY_PEM = `-----BEGIN PUBLIC KEY-----
<PASTE THE REAL PUBLIC KEY HERE — SEE INSTRUCTIONS ABOVE>
-----END PUBLIC KEY-----`

interface LicensePayload {
  product: string
  email: string
  device_id?: string
  issued_at: string
  expires_at: string
  features: string[]
}

function getLicensePath(): string {
  return path.join(app.getPath('userData'), 'license.enc')
}

function generateDeviceId(): string {
  // Simple device fingerprint: hostname + platform + arch
  const parts = [
    require('os').hostname(),
    process.platform,
    process.arch,
  ]
  return crypto.createHash('sha256').update(parts.join('-')).digest('hex').slice(0, 16)
}

function base32Decode(encoded: string): Buffer {
  const alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ234567'
  const cleaned = encoded.toUpperCase().replace(/-/g, '').replace(/\s/g, '')
  let bits = 0
  let value = 0
  const output: number[] = []

  for (const char of cleaned) {
    const idx = alphabet.indexOf(char)
    if (idx === -1) throw new Error(`Invalid Base32 character: ${char}`)
    value = (value << 5) | idx
    bits += 5
    if (bits >= 8) {
      output.push((value >>> (bits - 8)) & 0xFF)
      bits -= 8
    }
  }
  return Buffer.from(output)
}

function verifySignature(data: Buffer, signature: Buffer): boolean {
  const verify = crypto.createVerify('SHA256')
  verify.update(data)
  return verify.verify(PUBLIC_KEY_PEM, signature)
}

function encryptLicense(payload: LicensePayload): string {
  // Simple Fernet-like encryption using AES-256-GCM with a key derived from device ID
  const deviceId = generateDeviceId()
  const key = crypto.createHash('sha256').update('mipham-quant-license-' + deviceId).digest()
  const iv = crypto.randomBytes(12)
  const cipher = crypto.createCipheriv('aes-256-gcm', key, iv)
  const json = JSON.stringify(payload)
  let encrypted = cipher.update(json, 'utf8', 'hex')
  encrypted += cipher.final('hex')
  const authTag = cipher.getAuthTag()
  // Store as: iv:authTag:ciphertext
  return `${iv.toString('hex')}:${authTag.toString('hex')}:${encrypted}`
}

function decryptLicense(encrypted: string): LicensePayload | null {
  try {
    const deviceId = generateDeviceId()
    const key = crypto.createHash('sha256').update('mipham-quant-license-' + deviceId).digest()
    const [ivHex, authTagHex, ciphertext] = encrypted.split(':')
    const iv = Buffer.from(ivHex, 'hex')
    const authTag = Buffer.from(authTagHex, 'hex')
    const decipher = crypto.createDecipheriv('aes-256-gcm', key, iv)
    decipher.setAuthTag(authTag)
    let decrypted = decipher.update(ciphertext, 'hex', 'utf8')
    decrypted += decipher.final('utf8')
    return JSON.parse(decrypted)
  } catch {
    return null
  }
}

export function activateLicense(licenseKey: string): { success: boolean; message: string } {
  try {
    // The license key format: MQ-XXXX-XXXX-XXXX-XXXX (Base32 encoded)
    if (!licenseKey.startsWith('MQ-') && !licenseKey.startsWith('MQ')) {
      return { success: false, message: 'Invalid license key format' }
    }

    const keyBody = licenseKey.replace('MQ-', 'MQ').replace(/-/g, '')
    const raw = base32Decode(keyBody)

    // First 256 bytes = RSA signature, rest = JSON payload
    const SIGNATURE_SIZE = 256 // 2048-bit RSA
    const signature = raw.subarray(0, SIGNATURE_SIZE)
    const payloadBytes = raw.subarray(SIGNATURE_SIZE)

    if (!verifySignature(payloadBytes, signature)) {
      return { success: false, message: 'License key is invalid (signature check failed)' }
    }

    const payload: LicensePayload = JSON.parse(payloadBytes.toString('utf8'))

    // Check product
    if (payload.product !== 'mipham-quant') {
      return { success: false, message: 'License key is for a different product' }
    }

    // Check expiration
    if (payload.expires_at) {
      const expires = new Date(payload.expires_at)
      if (expires < new Date()) {
        return { success: false, message: `License expired on ${payload.expires_at}` }
      }
    }

    // Check device binding (optional — only if device_id is set)
    if (payload.device_id) {
      const currentDeviceId = generateDeviceId()
      if (payload.device_id !== currentDeviceId) {
        return { success: false, message: 'License is bound to a different device' }
      }
    }

    // Save encrypted license to disk
    const encrypted = encryptLicense(payload)
    fs.writeFileSync(getLicensePath(), encrypted, 'utf8')

    return { success: true, message: 'License activated successfully' }
  } catch (err: any) {
    return { success: false, message: `Activation failed: ${err.message}` }
  }
}

export function checkLicense(): boolean {
  const licensePath = getLicensePath()
  if (!fs.existsSync(licensePath)) return false

  const encrypted = fs.readFileSync(licensePath, 'utf8')
  const payload = decryptLicense(encrypted)
  if (!payload) return false

  if (payload.expires_at) {
    return new Date(payload.expires_at) >= new Date()
  }
  return true
}

export function getLicenseInfo(): LicensePayload | null {
  const licensePath = getLicensePath()
  if (!fs.existsSync(licensePath)) return null

  const encrypted = fs.readFileSync(licensePath, 'utf8')
  return decryptLicense(encrypted)
}

export function isActivated(): boolean {
  return checkLicense()
}
```

- [ ] **Step 2: Create license generation script**

Create `scripts/generate-license.py`:

```python
#!/usr/bin/env python3
"""
Mipham Quant — License Key Generator
=====================================
Generates RSA-signed license keys for desktop edition.

⚠️  KEEP THE PRIVATE KEY SECRET. Never commit it or ship it.
    Store it offline. Only the PUBLIC KEY goes into the app.

Usage:
    python scripts/generate-license.py --email buyer@example.com

Output:
    MQ-XXXX-XXXX-XXXX-XXXX (5 blocks, Base32 encoded)
"""

import argparse
import base64
import json
import os
import sys
from datetime import datetime, timedelta
from typing import Optional

# ---- RSA Key Generation (run once) ----
# If you haven't generated keys yet, uncomment and run:
#
#   from cryptography.hazmat.primitives.asymmetric import rsa
#   from cryptography.hazmat.primitives import serialization
#   private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
#   public_key = private_key.public_key()
#   with open('license_private.pem', 'wb') as f:
#       f.write(private_key.private_bytes(
#           encoding=serialization.Encoding.PEM,
#           format=serialization.PrivateFormat.PKCS8,
#           encryption_algorithm=serialization.NoEncryption()))
#   with open('license_public.pem', 'wb') as f:
#       f.write(public_key.public_bytes(
#           encoding=serialization.Encoding.PEM,
#           format=serialization.PublicFormat.SubjectPublicKeyInfo))

# ---- Configuration ----
PRODUCT = "mipham-quant"
DEFAULT_EXPIRY_DAYS = 36500  # ~100 years = effectively permanent

# Path to private key (absolute or relative to this script)
PRIVATE_KEY_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "license_private.pem"
)

try:
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding, rsa
    HAS_CRYPTO = True
except ImportError:
    HAS_CRYPTO = False
    print("⚠️  'cryptography' not installed. Run: pip install cryptography")
    print("   Then re-run this script.")
    sys.exit(1)

BASE32_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567"


def base32_encode(data: bytes) -> str:
    """Encode bytes to Base32 string (RFC 4648, uppercase, no padding)."""
    result = []
    bits = 0
    value = 0
    for byte in data:
        value = (value << 8) | byte
        bits += 8
        while bits >= 5:
            result.append(BASE32_ALPHABET[(value >> (bits - 5)) & 0x1F])
            bits -= 5
    if bits > 0:
        result.append(BASE32_ALPHABET[(value << (5 - bits)) & 0x1F])
    return "".join(result)


def format_license_key(encoded: str) -> str:
    """Format as MQ-XXXX-XXXX-XXXX-XXXX (5 blocks of 4)."""
    # Strip MQ prefix if present, then chunk into blocks of 4
    raw = encoded.upper()
    if raw.startswith("MQ"):
        raw = raw[2:]
    blocks = [raw[i:i+4] for i in range(0, len(raw), 4)]
    return "MQ-" + "-".join(blocks[:5])


def sign_payload(payload: dict, private_key_path: str) -> bytes:
    """Sign JSON payload with RSA-SHA256."""
    with open(private_key_path, "rb") as f:
        private_key = serialization.load_pem_private_key(f.read(), password=None)

    payload_json = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    signature = private_key.sign(
        payload_json,
        padding.PKCS1v15(),
        hashes.SHA256(),
    )
    # Concatenate: signature + payload
    return signature + payload_json


def generate_license(
    email: str,
    device_id: Optional[str] = None,
    expiry_days: int = DEFAULT_EXPIRY_DAYS,
    features: Optional[list] = None,
) -> str:
    """Generate a license key for the given email."""
    if not os.path.exists(PRIVATE_KEY_PATH):
        print(f"❌ Private key not found at: {PRIVATE_KEY_PATH}")
        print("   Generate keys first (see script header).")
        sys.exit(1)

    if features is None:
        features = ["all"]

    issued_at = datetime.utcnow().strftime("%Y-%m-%d")
    expires_at = (datetime.utcnow() + timedelta(days=expiry_days)).strftime("%Y-%m-%d")

    payload = {
        "product": PRODUCT,
        "email": email,
        "issued_at": issued_at,
        "expires_at": expires_at,
        "features": features,
    }

    if device_id:
        payload["device_id"] = device_id

    signed = sign_payload(payload, PRIVATE_KEY_PATH)
    encoded = base32_encode(signed)
    return format_license_key(encoded)


def main():
    parser = argparse.ArgumentParser(description="Mipham Quant License Generator")
    parser.add_argument("--email", required=True, help="Buyer email address")
    parser.add_argument("--device-id", help="Bind to specific device ID")
    parser.add_argument("--expiry-days", type=int, default=DEFAULT_EXPIRY_DAYS,
                        help=f"Days until expiry (default: {DEFAULT_EXPIRY_DAYS})")
    parser.add_argument("--features", nargs="+", default=["all"],
                        help="Enabled features (default: all)")

    args = parser.parse_args()

    license_key = generate_license(
        email=args.email,
        device_id=args.device_id,
        expiry_days=args.expiry_days,
        features=args.features,
    )

    print()
    print("=" * 50)
    print("  Mipham Quant License Key")
    print("=" * 50)
    print(f"  {license_key}")
    print("=" * 50)
    print(f"  Email:     {args.email}")
    print(f"  Device:    {args.device_id or 'any'}")
    print(f"  Expires:   {args.expiry_days} days from now")
    print(f"  Features:  {', '.join(args.features)}")
    print("=" * 50)
    print()
    print("Send this key to the buyer. They enter it in:")
    print("  Mipham Quant → Help → Enter License Key")
    print()


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Wire license IPC handlers**

Modify `electron/main.ts`, add after backend bootstrap:

```typescript
import { activateLicense, checkLicense, getLicenseInfo } from './license'

// ... in bootstrap():
ipcMain.handle('license:activate', (_event, key: string) => {
  return activateLicense(key)
})
ipcMain.handle('license:status', () => {
  return {
    activated: checkLicense(),
    info: getLicenseInfo(),
  }
})
```

- [ ] **Step 4: Generate RSA keys (once)**

```bash
python3 -c "
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
public_key = private_key.public_key()
with open('license_private.pem', 'wb') as f:
    f.write(private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()))
with open('license_public.pem', 'wb') as f:
    f.write(public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo))
print('RSA keys generated:')
print('  license_private.pem — KEEP SECRET (do not commit)')
print('  license_public.pem  — embed in app')
"
```

- [ ] **Step 5: Update .gitignore**

Add to root `.gitignore`:
```
# License keys (NEVER commit private key)
license_private.pem
license_public.pem
```

- [ ] **Step 6: Commit**

```bash
git add electron/license.ts scripts/generate-license.py electron/main.ts .gitignore
git commit -m "feat: add license activation system (RSA signature offline verification)

license.ts: Base32 decode → RSA verify → device binding → AES-256-GCM
encrypted local storage. Full offline operation.
generate-license.py: CLI tool for signing license keys with private key.
RSA key pair generation instructions included."
```

---

## Task 9: System Tray & Native Notifications

**Files:**
- Create: `electron/tray.ts`
- Modify: `electron/main.ts`

**Interfaces:**
- Produces: System tray with menu, close-to-tray behavior, native notifications

- [ ] **Step 1: Create electron/tray.ts**

Create `electron/tray.ts`:

```typescript
import { Tray, Menu, nativeImage, app, BrowserWindow } from 'electron'
import * as path from 'path'

let tray: Tray | null = null

export function createTray(mainWindow: BrowserWindow): Tray {
  const iconPath = path.join(__dirname, '..', 'resources', 'icon.png')
  const icon = nativeImage.createFromPath(iconPath).resize({ width: 16, height: 16 })

  tray = new Tray(icon)
  tray.setToolTip('Mipham Quant')

  const updateMenu = () => {
    const contextMenu = Menu.buildFromTemplate([
      {
        label: '📊 显示主窗口',
        click: () => {
          mainWindow.show()
          mainWindow.focus()
        },
      },
      { type: 'separator' },
      {
        label: '⏸ 暂停所有策略',
        enabled: false, // Future: query backend for running strategies
        click: () => {
          mainWindow.webContents.send('tray:pauseAll')
        },
      },
      {
        label: '▶ 恢复所有策略',
        enabled: false,
        click: () => {
          mainWindow.webContents.send('tray:resumeAll')
        },
      },
      { type: 'separator' },
      {
        label: '⚙ 设置',
        click: () => {
          mainWindow.show()
          mainWindow.focus()
          mainWindow.webContents.send('nav:settings')
        },
      },
      {
        label: '❓ 关于',
        click: () => {
          const { dialog } = require('electron')
          dialog.showMessageBox(mainWindow, {
            type: 'info',
            title: '关于 Mipham Quant',
            message: 'Mipham Quant Desktop v1.0.0',
            detail: 'AI 量化交易平台\n\n©2026 One Mipham Corporation\n北京华安麦逄科技有限公司',
          })
        },
      },
      { type: 'separator' },
      {
        label: '✕ 退出',
        click: () => {
          app.isQuitting = true
          app.quit()
        },
      },
    ])
    tray!.setContextMenu(contextMenu)
  }

  updateMenu()

  tray.on('double-click', () => {
    mainWindow.show()
    mainWindow.focus()
  })

  return tray
}

export function showNotification(title: string, body: string): void {
  const { Notification } = require('electron')
  if (Notification.isSupported()) {
    new Notification({ title, body, icon: path.join(__dirname, '..', 'resources', 'icon.png') }).show()
  }
}
```

- [ ] **Step 2: Update main.ts for close-to-tray**

Modify `electron/main.ts`:

```typescript
import { createTray, showNotification } from './tray'

// Extend app type for quit tracking
declare module 'electron' {
  interface App {
    isQuitting?: boolean
  }
}

// In bootstrap(), after creating window:
createTray(mainWindow)

// Close = hide to tray (not quit)
mainWindow.on('close', (event) => {
  if (!app.isQuitting) {
    event.preventDefault()
    mainWindow.hide()
    showNotification('Mipham Quant', '应用已最小化到系统托盘，策略继续运行中。')
  }
})

// Notify renderer when backend is ready
backend.onReady(() => {
  mainWindow?.webContents.send('backend:ready')
})

// Forward tray commands to renderer
ipcMain.on('tray:pauseAll', () => {
  // TODO: Implement backend API call
  showNotification('Mipham Quant', '所有策略已暂停')
})

ipcMain.on('tray:resumeAll', () => {
  showNotification('Mipham Quant', '所有策略已恢复')
})
```

- [ ] **Step 3: Commit**

```bash
git add electron/tray.ts electron/main.ts
git commit -m "feat: add system tray and native notifications

tray.ts: system tray with menu (show/pause/resume/settings/about/quit),
double-click to restore, notification support.
main.ts: close-to-tray behavior (window hides instead of closing),
tray notifications on minimize."
```

---

## Task 10: PyInstaller Packaging

**Files:**
- Create: `backend_api_python/pyinstaller.spec`
- Create: `backend_api_python/build.py`
- Modify: `backend_api_python/run.py` (add PyInstaller path handling)

**Interfaces:**
- Produces: Single-file Python backend binary for macOS and Windows

- [ ] **Step 1: Create pyinstaller build script**

Create `backend_api_python/build.py`:

```python
#!/usr/bin/env python3
"""
Build script for Mipham Quant Backend (PyInstaller one-file binary).

Usage:
    python build.py          # Build for current platform
    python build.py --clean  # Clean build
"""

import os
import shutil
import subprocess
import sys


def build():
    """Run PyInstaller to create a single-file backend binary."""
    spec_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pyinstaller.spec")

    if not os.path.exists(spec_file):
        print("pyinstaller.spec not found. Generating...")
        _generate_spec()

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--clean",
        "--noconfirm",
        spec_file,
    ]

    print(f"Running: {' '.join(cmd)}")
    subprocess.run(cmd, check=True)

    # Copy binary to dist/
    dist_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dist")
    os.makedirs(dist_dir, exist_ok=True)

    binary_name = "mipham-quant-backend"
    if sys.platform == "win32":
        binary_name += ".exe"
        src = os.path.join("dist", binary_name)
    else:
        src = os.path.join("dist", binary_name)

    if os.path.exists(src):
        dest = os.path.join(dist_dir, binary_name)
        shutil.copy2(src, dest)
        print(f"Binary copied to: {dest}")
        print(f"Size: {os.path.getsize(dest) / 1024 / 1024:.1f} MB")
    else:
        print(f"Binary not found at: {src}")


def _generate_spec():
    """Generate pyinstaller.spec file."""
    spec_content = """# -*- mode: python ; coding: utf-8 -*-
import os
import sys
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

block_cipher = None

# Collect all Flask blueprints and services
hiddenimports = collect_submodules('app')
hiddenimports += [
    'flask', 'flask_cors', 'werkzeug', 'jinja2',
    'numpy', 'pandas', 'ccxt', 'yfinance',
    'sqlite3', 'json', 'hashlib', 'cryptography',
    'requests', 'urllib3', 'certifi',
    'bcrypt', 'pyjwt', 'bip_utils',
    'akshare',
]

# Data files to bundle
datas = [
    ('migrations/init_sqlite.sql', 'migrations'),
]

# Try to add seed data
seed_path = os.path.join('app', 'data', 'seed.sql')
if os.path.exists(seed_path):
    datas.append((seed_path, os.path.join('app', 'data')))

a = Analysis(
    ['run.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter', 'matplotlib', 'PIL', 'scipy',
        'torch', 'tensorflow', 'sklearn',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# Single-file executable
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='mipham-quant-backend',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # Show console for logs
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
"""
    with open("pyinstaller.spec", "w") as f:
        f.write(spec_content)
    print("pyinstaller.spec generated")


if __name__ == "__main__":
    print("Installing PyInstaller...")
    subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)
    build()
```

- [ ] **Step 2: Update PATH handling in run.py for PyInstaller**

Add at the top of `backend_api_python/run.py`, after the docstring:

```python
# PyInstaller: when running as a bundled executable, the binary is in a
# temp directory. We need to find bundled data files relative to sys._MEIPASS.
import sys as _sys
if getattr(_sys, 'frozen', False):
    # Running as PyInstaller bundle
    _bundle_dir = _sys._MEIPASS
    _sys.path.insert(0, _bundle_dir)
    # Ensure the working directory is the user's data directory
    _data_dir = os.path.join(os.path.expanduser("~"), ".mipham-quant")
    os.makedirs(_data_dir, exist_ok=True)
    os.chdir(_data_dir)
```

- [ ] **Step 3: Commit**

```bash
git add backend_api_python/build.py backend_api_python/run.py
git commit -m "feat: add PyInstaller build script for backend binary

build.py: generates pyinstaller.spec, runs PyInstaller, copies binary.
Excludes heavy deps (tkinter, matplotlib, torch, tensorflow).
run.py: PyInstaller _MEIPASS path handling for bundled data files."
```

---

## Task 11: Final Integration & Build Verification

**Files:**
- Modify: `electron/main.ts` (license gate)
- Create: `scripts/build-desktop.sh`

**Interfaces:**
- Consumes: All previous tasks
- Produces: Runnable desktop app

- [ ] **Step 1: Add license activation gate to main.ts**

Modify `electron/main.ts` bootstrap to check license before showing window:

```typescript
import { isActivated } from './license'

async function bootstrap(): Promise<void> {
  // Check license before starting backend
  if (!isActivated()) {
    // Show activation dialog
    createWindow()
    mainWindow?.webContents.on('did-finish-load', () => {
      mainWindow?.webContents.send('license:required')
    })
    return
  }

  // Start backend and show main window
  try {
    await backend.start()
  } catch (err) {
    console.error('Failed to start backend:', err)
  }
  createWindow()
}
```

- [ ] **Step 2: Create build script**

Create `scripts/build-desktop.sh`:

```bash
#!/bin/bash
# Mipham Quant Desktop — Full Build Script
set -e

echo "=== Building Mipham Quant Desktop v1.0.0 ==="

# Step 1: Build Python backend (on macOS only; Windows needs separate build)
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo ""
    echo "[1/4] Building Python backend..."
    cd backend_api_python
    python3 build.py
    cd ..
    echo "Backend built: backend_api_python/dist/"
    ls -lh backend_api_python/dist/
else
    echo "[1/4] Skipping Python build (not macOS — build on target platform)"
    mkdir -p backend_api_python/dist
    touch backend_api_python/dist/mipham-quant-backend
fi

# Step 2: Build frontend
echo ""
echo "[2/4] Building frontend..."
cd apps/frontend
pnpm install --frozen-lockfile
pnpm build
cd ../..
echo "Frontend built: frontend/dist/"

# Step 3: Compile Electron TypeScript
echo ""
echo "[3/4] Compiling Electron..."
pnpm tsc -p electron/tsconfig.json
echo "Electron compiled: dist-electron/"

# Step 4: Package with electron-builder
echo ""
echo "[4/4] Packaging with electron-builder..."
if [[ "$OSTYPE" == "darwin"* ]]; then
    pnpm electron:build:mac
    echo ""
    echo "=== Build Complete ==="
    ls -lh dist/*.dmg dist/*.zip 2>/dev/null || echo "Check dist/ for output"
else
    pnpm electron:build:win
    echo ""
    echo "=== Build Complete ==="
    ls -lh dist/*.exe 2>/dev/null || echo "Check dist/ for output"
fi
```

```bash
chmod +x scripts/build-desktop.sh
```

- [ ] **Step 3: Verify dev mode**

```bash
# Terminal 1: Start backend
DB_TYPE=sqlite DB_PATH=/tmp/quant-dev.db python3 backend_api_python/run.py

# Terminal 2: Start frontend dev server
cd apps/frontend && pnpm dev

# Terminal 3: Start Electron in dev mode
NODE_ENV=development pnpm electron:dev
```

Expected: Electron window opens, shows Mipham Quant dashboard, data from SQLite backend.

- [ ] **Step 4: Commit**

```bash
git add electron/main.ts scripts/build-desktop.sh
git commit -m "feat: final integration — license gate, build script

main.ts checks license before starting backend.
build-desktop.sh: 4-step full build pipeline (backend, frontend,
Electron TS, electron-builder packaging)."
```

---

## Verification Checklist

After all tasks complete, verify:

- [ ] `DB_TYPE=sqlite python3 backend_api_python/run.py` starts without PostgreSQL
- [ ] `cd apps/frontend && pnpm build` produces relative-path frontend
- [ ] `pnpm tsc -p electron/tsconfig.json` compiles without errors
- [ ] `NODE_ENV=development pnpm electron:dev` opens Electron with working dashboard
- [ ] `python3 scripts/generate-license.py --email test@test.com` produces valid key
- [ ] Full build: `bash scripts/build-desktop.sh` produces `.dmg` or `.exe`
