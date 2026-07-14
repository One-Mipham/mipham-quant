-- Mipham Quant — SQLite Schema (Desktop Edition)
-- Auto-generated from db_sqlite._EMBEDDED_SCHEMA

CREATE TABLE IF NOT EXISTS qd_users (
    id INTEGER PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT,
    nickname TEXT DEFAULT 'Trader',
    email TEXT,
    avatar TEXT DEFAULT '/avatar2.jpg',
    role TEXT DEFAULT 'admin',
    status TEXT DEFAULT 'active',
    credits REAL DEFAULT 0,
    vip_expires_at TEXT,
    vip_plan TEXT DEFAULT '',
    vip_is_lifetime INTEGER DEFAULT 0,
    vip_monthly_credits_last_grant TEXT,
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
    is_buy INTEGER DEFAULT 0 NOT NULL,
    end_time INTEGER DEFAULT 1 NOT NULL,
    name TEXT NOT NULL,
    code TEXT NOT NULL DEFAULT '',
    description TEXT DEFAULT '',
    language TEXT DEFAULT 'python',
    category TEXT DEFAULT 'custom',
    version INTEGER DEFAULT 1,
    publish_to_community INTEGER DEFAULT 0,
    pricing_type TEXT DEFAULT 'free',
    price REAL DEFAULT 0,
    is_encrypted INTEGER DEFAULT 0,
    preview_image TEXT DEFAULT '',
    vip_free INTEGER DEFAULT 0,
    createtime INTEGER,
    updatetime INTEGER,
    review_status TEXT DEFAULT 'approved',
    review_note TEXT DEFAULT '',
    reviewed_by INTEGER,
    reviewed_at TEXT,
    purchase_count INTEGER DEFAULT 0,
    avg_rating REAL DEFAULT 0,
    rating_count INTEGER DEFAULT 0,
    view_count INTEGER DEFAULT 0,
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

-- =============================================================================
-- Extended tables for desktop edition (critical for strategy/trading/analysis)
-- =============================================================================

CREATE TABLE IF NOT EXISTS qd_strategies_trading (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL DEFAULT 1 REFERENCES qd_users(id) ON DELETE CASCADE,
    strategy_name TEXT NOT NULL,
    strategy_type TEXT DEFAULT 'IndicatorStrategy',
    market_category TEXT DEFAULT 'Crypto',
    execution_mode TEXT DEFAULT 'signal',
    notification_config TEXT DEFAULT '',
    status TEXT DEFAULT 'stopped',
    symbol TEXT,
    timeframe TEXT,
    initial_capital REAL DEFAULT 1000,
    leverage INTEGER DEFAULT 1,
    market_type TEXT DEFAULT 'swap',
    exchange_config TEXT,
    indicator_config TEXT,
    trading_config TEXT,
    ai_model_config TEXT,
    decide_interval INTEGER DEFAULT 300,
    strategy_group_id TEXT DEFAULT '',
    group_base_name TEXT DEFAULT '',
    strategy_mode TEXT DEFAULT 'signal',
    strategy_code TEXT DEFAULT '',
    last_rebalance_at TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS qd_strategy_positions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL DEFAULT 1 REFERENCES qd_users(id) ON DELETE CASCADE,
    strategy_id INTEGER REFERENCES qd_strategies_trading(id) ON DELETE CASCADE,
    symbol TEXT,
    side TEXT,
    size REAL,
    entry_price REAL,
    current_price REAL,
    highest_price REAL DEFAULT 0,
    lowest_price REAL DEFAULT 0,
    unrealized_pnl REAL DEFAULT 0,
    pnl_percent REAL DEFAULT 0,
    equity REAL DEFAULT 0,
    updated_at TEXT DEFAULT (datetime('now')),
    UNIQUE(strategy_id, symbol, side)
);

CREATE TABLE IF NOT EXISTS qd_strategy_trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL DEFAULT 1 REFERENCES qd_users(id) ON DELETE CASCADE,
    strategy_id INTEGER REFERENCES qd_strategies_trading(id) ON DELETE CASCADE,
    symbol TEXT,
    type TEXT,
    price REAL,
    amount REAL,
    value REAL,
    commission REAL DEFAULT 0,
    commission_ccy TEXT DEFAULT '',
    profit REAL DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS pending_orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL DEFAULT 1 REFERENCES qd_users(id) ON DELETE CASCADE,
    strategy_id INTEGER REFERENCES qd_strategies_trading(id) ON DELETE SET NULL,
    symbol TEXT NOT NULL,
    signal_type TEXT NOT NULL,
    signal_ts INTEGER,
    market_type TEXT DEFAULT 'swap',
    order_type TEXT DEFAULT 'market',
    amount REAL DEFAULT 0,
    price REAL DEFAULT 0,
    execution_mode TEXT DEFAULT 'signal',
    status TEXT DEFAULT 'pending',
    priority INTEGER DEFAULT 0,
    attempts INTEGER DEFAULT 0,
    max_attempts INTEGER DEFAULT 10,
    last_error TEXT DEFAULT '',
    payload_json TEXT DEFAULT '',
    dispatch_note TEXT DEFAULT '',
    exchange_id TEXT DEFAULT '',
    exchange_order_id TEXT DEFAULT '',
    exchange_response_json TEXT DEFAULT '',
    filled REAL DEFAULT 0,
    avg_price REAL DEFAULT 0,
    error_msg TEXT DEFAULT '',
    executed_at TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    processed_at TEXT,
    sent_at TEXT
);

CREATE TABLE IF NOT EXISTS qd_strategy_notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL DEFAULT 1,
    strategy_id INTEGER,
    title TEXT NOT NULL DEFAULT '',
    body TEXT DEFAULT '',
    is_read INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS qd_strategy_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    strategy_id INTEGER NOT NULL DEFAULT 0,
    level TEXT DEFAULT 'INFO',
    message TEXT DEFAULT '',
    timestamp TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS qd_manual_positions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL DEFAULT 1 REFERENCES qd_users(id) ON DELETE CASCADE,
    market TEXT NOT NULL,
    symbol TEXT NOT NULL,
    name TEXT DEFAULT '',
    side TEXT DEFAULT 'long',
    quantity REAL NOT NULL DEFAULT 0,
    entry_price REAL NOT NULL DEFAULT 0,
    entry_time INTEGER,
    notes TEXT DEFAULT '',
    tags TEXT DEFAULT '',
    group_name TEXT DEFAULT '',
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    UNIQUE(user_id, market, symbol, side, group_name)
);

CREATE INDEX IF NOT EXISTS idx_manual_positions_user_id ON qd_manual_positions(user_id);

CREATE TABLE IF NOT EXISTS qd_position_alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL DEFAULT 1 REFERENCES qd_users(id) ON DELETE CASCADE,
    position_id INTEGER,
    market TEXT DEFAULT '',
    symbol TEXT DEFAULT '',
    alert_type TEXT NOT NULL,
    threshold REAL NOT NULL DEFAULT 0,
    notification_config TEXT DEFAULT '',
    is_active INTEGER DEFAULT 1,
    is_triggered INTEGER DEFAULT 0,
    last_triggered_at TEXT,
    trigger_count INTEGER DEFAULT 0,
    repeat_interval INTEGER DEFAULT 0,
    notes TEXT DEFAULT '',
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS qd_position_monitors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL DEFAULT 1 REFERENCES qd_users(id) ON DELETE CASCADE,
    name TEXT DEFAULT '',
    position_ids TEXT DEFAULT '',
    monitor_type TEXT DEFAULT 'ai',
    config TEXT DEFAULT '',
    notification_config TEXT DEFAULT '',
    is_active INTEGER DEFAULT 1,
    last_run_at TEXT,
    next_run_at TEXT,
    last_result TEXT DEFAULT '',
    run_count INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS qd_ai_calibration (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    market TEXT NOT NULL DEFAULT 'Crypto',
    timeframe TEXT NOT NULL DEFAULT '1D',
    signal_type TEXT NOT NULL DEFAULT 'buy',
    confidence REAL NOT NULL DEFAULT 0,
    buy_threshold REAL,
    sell_threshold REAL,
    min_consensus_abs_override REAL,
    quality_hold_threshold REAL,
    actual_outcome INTEGER DEFAULT 0,
    predicted_at TEXT DEFAULT (datetime('now')),
    outcome_at TEXT,
    validated_at TEXT,
    created_at TEXT,
    meta TEXT DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS qd_analysis_memory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL DEFAULT 1,
    market TEXT NOT NULL DEFAULT 'Crypto',
    symbol TEXT NOT NULL DEFAULT '',
    signal_type TEXT NOT NULL DEFAULT 'buy',
    decision TEXT NOT NULL DEFAULT '',
    confidence REAL NOT NULL DEFAULT 0,
    price_at_analysis REAL,
    summary TEXT DEFAULT '',
    reasons TEXT DEFAULT '{}',
    scores TEXT DEFAULT '{}',
    indicators_snapshot TEXT DEFAULT '{}',
    raw_result TEXT DEFAULT '{}',
    consensus_score REAL,
    consensus_abs REAL,
    agreement_ratio REAL,
    quality_multiplier REAL,
    result TEXT DEFAULT '',
    is_validated INTEGER DEFAULT 0,
    meta TEXT DEFAULT '{}',
    created_at TEXT DEFAULT (datetime('now')),
    validated_at TEXT,
    actual_outcome TEXT DEFAULT '',
    actual_return_pct REAL
);

CREATE TABLE IF NOT EXISTS qd_backtest_trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL DEFAULT 0,
    user_id INTEGER NOT NULL DEFAULT 1,
    symbol TEXT NOT NULL DEFAULT '',
    signal_type TEXT NOT NULL DEFAULT '',
    entry_time TEXT,
    exit_time TEXT,
    entry_price REAL DEFAULT 0,
    exit_price REAL DEFAULT 0,
    amount REAL DEFAULT 0,
    profit REAL DEFAULT 0,
    profit_pct REAL DEFAULT 0,
    meta TEXT DEFAULT '{}',
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS qd_backtest_equity_points (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL DEFAULT 0,
    timestamp TEXT NOT NULL DEFAULT '',
    equity REAL DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS qd_backtest_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL DEFAULT 1,
    indicator_id INTEGER,
    strategy_id INTEGER,
    run_type TEXT DEFAULT 'single',
    status TEXT DEFAULT 'running',
    symbol TEXT,
    market TEXT DEFAULT 'Crypto',
    timeframe TEXT DEFAULT '1D',
    start_date TEXT,
    end_date TEXT,
    initial_capital REAL DEFAULT 10000,
    final_equity REAL,
    total_return REAL,
    max_drawdown REAL,
    sharpe_ratio REAL,
    win_rate REAL,
    total_trades INTEGER DEFAULT 0,
    config TEXT DEFAULT '{}',
    result TEXT DEFAULT '{}',
    error_msg TEXT DEFAULT '',
    started_at TEXT DEFAULT (datetime('now')),
    completed_at TEXT
);

CREATE TABLE IF NOT EXISTS qd_analysis_tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL DEFAULT 1,
    market TEXT DEFAULT 'Crypto',
    symbol TEXT DEFAULT '',
    task_type TEXT DEFAULT 'analysis',
    status TEXT DEFAULT 'pending',
    priority INTEGER DEFAULT 0,
    result TEXT DEFAULT '{}',
    error_msg TEXT DEFAULT '',
    created_at TEXT DEFAULT (datetime('now')),
    completed_at TEXT
);

INSERT OR IGNORE INTO qd_users (id, username, nickname, role, status)
VALUES (1, 'trader', 'Trader', 'admin', 'active');

PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;
