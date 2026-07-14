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
