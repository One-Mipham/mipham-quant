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
