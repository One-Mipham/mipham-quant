"""
SQLite Database Adapter for Desktop Edition.

Implements the same interface as db_postgres.py so calling code
requires zero changes. Switched via DB_TYPE=sqlite environment variable.

Auto-translates PostgreSQL SQL to SQLite at query execution time:
    NOW()          → datetime('now')
    %s             → ?
    ILIKE          → LIKE
    SERIAL         → INTEGER PRIMARY KEY AUTOINCREMENT
    DOUBLE PRECISION → REAL
    DECIMAL(p,s)   → REAL
    VARCHAR(n)     → TEXT
    TIMESTAMP      → TEXT
    BOOLEAN        → INTEGER
    JSONB          → TEXT
"""

import os
import re
import sqlite3
import threading
from contextlib import contextmanager

from app.utils.logger import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Minimal SQL translation: only convert psycopg2 %s placeholders to SQLite ?
# ---------------------------------------------------------------------------


def _translate_sql(query: str):
    """Translate PostgreSQL SQL to SQLite-compatible SQL.

    Handles:
    - %s -> ? (psycopg2 -> sqlite3 parameter placeholder)
    - DDL types: SERIAL, VARCHAR, DECIMAL, TIMESTAMP, BOOLEAN, JSONB
    - NOW() -> (datetime('now'))
    - CURDATE() -> DATE('now')
    - ILIKE -> LIKE
    - INTERVAL expressions -> datetime() modifiers
    - ::type casts -> removed
    - RETURNING clause -> stripped (column names returned for cursor wrapper)

    Returns:
        (translated_query, returning_cols) where returning_cols is a list of
        column names from the RETURNING clause (empty list if none).
    """
    if not query or not isinstance(query, str):
        return query, []

    result = query

    # -- INTERVAL translation (BEFORE %s→? so %s inside INTERVAL is handled) --
    # Pattern A: NOW() +/- INTERVAL '%s <unit>'  (placeholder inside interval)
    #   → datetime('now', '+' || %s || ' <unit>')
    result = re.sub(
        r"\bNOW\s*\(\s*\)\s*\+\s*INTERVAL\s+'%s\s+(\w+)'",
        r"datetime('now', '+' || %s || ' \1')",
        result, flags=re.IGNORECASE,
    )
    result = re.sub(
        r"\bNOW\s*\(\s*\)\s*-\s*INTERVAL\s+'%s\s+(\w+)'",
        r"datetime('now', '-' || %s || ' \1')",
        result, flags=re.IGNORECASE,
    )
    # Pattern B: column +/- INTERVAL '%s <unit>' (generic, no NOW())
    #   → datetime(column, '+' || %s || ' <unit>')
    #   This is complex; handled case-by-case below.
    #   For now, the common pattern is with NOW().

    # Pattern C: NOW() +/- INTERVAL '<N> <unit>'  (f-string inlined literal)
    #   → datetime('now', '+N <unit>')
    result = re.sub(
        r"\bNOW\s*\(\s*\)\s*\+\s*INTERVAL\s+'(\d+)\s+(\w+)'",
        r"datetime('now', '+\1 \2')",
        result, flags=re.IGNORECASE,
    )
    result = re.sub(
        r"\bNOW\s*\(\s*\)\s*-\s*INTERVAL\s+'(\d+)\s+(\w+)'",
        r"datetime('now', '-\1 \2')",
        result, flags=re.IGNORECASE,
    )

    # Parameter placeholder (safe: %s only appears in SQL, not in string data)
    result = result.replace("%s", "?")

    # DDL type translations (only in CREATE/ALTER context — safe)
    result = re.sub(r"\bSERIAL\s+PRIMARY\s+KEY\b", "INTEGER PRIMARY KEY AUTOINCREMENT", result, flags=re.IGNORECASE)
    result = re.sub(r"\bBIGSERIAL\s+PRIMARY\s+KEY\b", "INTEGER PRIMARY KEY AUTOINCREMENT", result, flags=re.IGNORECASE)
    result = re.sub(r"\bSERIAL\b", "INTEGER", result, flags=re.IGNORECASE)
    result = re.sub(r"\bBIGSERIAL\b", "INTEGER", result, flags=re.IGNORECASE)
    result = re.sub(r"\bDOUBLE\s+PRECISION\b", "REAL", result, flags=re.IGNORECASE)
    result = re.sub(r"\bDECIMAL\s*\(\s*\d+\s*,\s*\d+\s*\)", "REAL", result, flags=re.IGNORECASE)
    result = re.sub(r"\bDECIMAL\b", "REAL", result, flags=re.IGNORECASE)
    result = re.sub(r"\bVARCHAR\s*\(\s*\d+\s*\)", "TEXT", result, flags=re.IGNORECASE)
    result = re.sub(r"\bBOOLEAN\b", "INTEGER", result, flags=re.IGNORECASE)
    result = re.sub(r"\bJSONB\b", "TEXT", result, flags=re.IGNORECASE)
    result = re.sub(r"\bTIMESTAMPTZ\b", "TEXT", result, flags=re.IGNORECASE)
    result = re.sub(r"\bTIMESTAMP\s+WITH\s+TIME\s+ZONE\b", "TEXT", result, flags=re.IGNORECASE)
    result = re.sub(r"\bTIMESTAMP\b", "TEXT", result, flags=re.IGNORECASE)

    # NOW() → (datetime('now'))  — parentheses required for DEFAULT clauses
    result = re.sub(r"\bNOW\s*\(\s*\)", "(datetime('now'))", result, flags=re.IGNORECASE)

    # CURDATE() → DATE('now')  — SQLite has no CURDATE()
    result = re.sub(r"\bCURDATE\s*\(\s*\)", "DATE('now')", result, flags=re.IGNORECASE)

    # ILIKE → LIKE (case-insensitive match for robustness)
    result = re.sub(r"\bILIKE\b", "LIKE", result, flags=re.IGNORECASE)

    # Remove ::type casts (e.g. "column::INTEGER" → "column")
    result = re.sub(r"::\s*\w+(\s*\[\s*\])?", "", result)

    # Remove RETURNING clauses — but capture column names so the cursor wrapper
    # can synthesize a result row from lastrowid (keeps callers using fetchone()
    # working without changes).
    returning_cols = []
    returning_match = re.search(
        r"\bRETURNING\s+((?:\w+\s*,\s*)*\w+)\s*",
        result, flags=re.IGNORECASE,
    )
    if returning_match:
        returning_cols = [c.strip() for c in returning_match.group(1).split(",")]
    result = re.sub(r"\bRETURNING\s+\w+(\s*,\s*\w+)*\s*", "", result, flags=re.IGNORECASE)

    # ADD COLUMN IF NOT EXISTS → ADD COLUMN
    result = re.sub(r"\bADD\s+COLUMN\s+IF\s+NOT\s+EXISTS\b", "ADD COLUMN", result, flags=re.IGNORECASE)

    # DO $$ ... END $$ blocks → extract ALTER TABLE ADD COLUMN statements for SQLite
    # PostgreSQL DO blocks typically conditionally add columns — we extract the
    # inner ALTER TABLE statements and convert them to standalone SQLite-friendly
    # ALTER TABLE ADD COLUMN (SQLite ignores duplicates automatically via error)
    do_match = re.search(
        r"\bDO\s+\$\$(.*?)END\s*\$\$",
        result, flags=re.IGNORECASE | re.DOTALL,
    )
    if do_match:
        do_body = do_match.group(1)
        # Extract ALTER TABLE ... ADD COLUMN statements from the DO block
        alter_stmts = re.findall(
            r"ALTER\s+TABLE\s+\w+\s+ADD\s+COLUMN\s+(?:IF\s+NOT\s+EXISTS\s+)?\w+\s+\w+[\w\s,\(\)]*?(?=;)",
            do_body, flags=re.IGNORECASE,
        )
        if alter_stmts:
            # Replace the DO block with the extracted ALTER statements
            # (SQLite will silently ignore ALTER TABLE ADD COLUMN if column exists,
            # similar to PostgreSQL's IF NOT EXISTS behavior)
            replacement = ";\n".join(alter_stmts) + ";"
            result = re.sub(
                r"\bDO\s+\$\$.*?END\s*\$\$",
                replacement,
                result, flags=re.IGNORECASE | re.DOTALL,
            )
        else:
            # No ALTER statements found — safe to no-op
            result = re.sub(
                r"\bDO\s+\$\$.*?END\s*\$\$",
                "SELECT 1",
                result, flags=re.IGNORECASE | re.DOTALL,
            )

    return result, returning_cols


# ---------------------------------------------------------------------------
# Translatable Connection/Cursor — sqlite3 subclasses with PG→SQLite translation
# ---------------------------------------------------------------------------


class _TranslatableCursor:
    """Wraps a real sqlite3.Cursor — translates SQL and converts Row→dict.

    We use a wrapper rather than a sqlite3.Cursor subclass because we need to
    convert sqlite3.Row to plain dict for JSON serialization (Flask jsonify).

    When a RETURNING clause is stripped from an INSERT/UPDATE, the cursor
    synthesises a result row from lastrowid so that callers using fetchone()
    continue to work without changes.
    """

    def __init__(self, raw: sqlite3.Cursor):
        self._cur = raw
        self._synthetic_row = None  # set when RETURNING was stripped

    def execute(self, query, parameters=None):
        translated, returning_cols = _translate_sql(str(query) if query else "")
        self._synthetic_row = None
        if parameters is None:
            result = self._cur.execute(translated)
        else:
            result = self._cur.execute(translated, parameters)
        # If RETURNING was stripped and this was an INSERT/UPDATE/DELETE,
        # synthesize a result row from lastrowid so fetchone() callers
        # (8 call sites: fast_analysis, quick_trade, credentials, billing,
        # polymarket, usdt_payment, analysis_memory, oauth) get an ID back.
        if returning_cols and self._cur.lastrowid:
            self._synthetic_row = {
                col: (self._cur.lastrowid if col.lower() == "id" else None)
                for col in returning_cols
            }
        return result

    def executemany(self, query, seq_of_parameters):
        translated, _ = _translate_sql(str(query) if query else "")
        self._synthetic_row = None
        return self._cur.executemany(translated, seq_of_parameters)

    def fetchone(self):
        if self._synthetic_row is not None:
            row = self._synthetic_row
            self._synthetic_row = None
            return row
        row = self._cur.fetchone()
        return dict(row) if row is not None else None

    def fetchmany(self, size=None):
        rows = self._cur.fetchmany(size) if size else self._cur.fetchmany()
        return [dict(r) for r in rows]

    def fetchall(self):
        return [dict(r) for r in self._cur.fetchall()]

    @property
    def rowcount(self):
        return self._cur.rowcount

    @property
    def lastrowid(self):
        return self._cur.lastrowid

    @property
    def description(self):
        return self._cur.description

    def close(self):
        return self._cur.close()

    def __iter__(self):
        for row in self._cur:
            yield dict(row)


class _TranslatableConnection(sqlite3.Connection):
    """sqlite3.Connection subclass that returns _TranslatableCursor objects.

    Being a true subclass (not a wrapper) means executescript(), commit(),
    rollback(), and all other connection-level operations work natively.
    """

    def cursor(self, factory=None):
        raw = super().cursor()
        return _TranslatableCursor(raw)

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


def _get_connection() -> _TranslatableConnection:
    """Get or create a thread-local SQLite connection with PG→SQLite translation."""
    conn = getattr(_local, "connection", None)
    if conn is None:
        _ensure_db_dir()
        conn = sqlite3.connect(
            _DB_PATH,
            check_same_thread=False,
            factory=_TranslatableConnection,
        )
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
            with open(norm, encoding="utf-8") as f:
                init_sql = f.read()
            logger.info(f"Loaded schema from {norm}")
            break

    if init_sql is None:
        # Fallback: embed the schema inline for PyInstaller bundles
        logger.warning("init_sqlite.sql not found on disk, using embedded schema")
        init_sql = _EMBEDDED_SCHEMA

    with get_db_connection() as db:
        db.executescript(init_sql)
        # Always apply the embedded schema too — it may contain additional
        # tables that the on-disk schema doesn't have (extended desktop tables).
        # IF NOT EXISTS makes this idempotent.
        if init_sql is not _EMBEDDED_SCHEMA:
            db.executescript(_EMBEDDED_SCHEMA)
        # Apply column migrations for existing databases that were created
        # before new columns were added to the schema (e.g., credits,
        # vip_expires_at on qd_users). ALTER TABLE ADD COLUMN in SQLite
        # silently errors if the column already exists, so we catch and
        # ignore duplicates.
        _run_column_migrations(db)

    logger.info("SQLite database initialized successfully")

    # Run seed data if available
    _run_seed_data()


def _run_column_migrations(db):
    """Add new columns to existing tables that were created before the columns
    existed in the schema. SQLite silently errors on duplicate columns, so
    we catch and ignore those errors.

    This handles the case where a user upgrades the app and their existing
    database is missing columns like qd_users.credits, qd_users.vip_expires_at,
    etc.
    """
    migrations = [
        # qd_users — columns added after initial schema
        ("qd_users", "credits", "REAL DEFAULT 0"),
        ("qd_users", "vip_expires_at", "TEXT"),
        ("qd_users", "vip_plan", "TEXT DEFAULT ''"),
        ("qd_users", "vip_is_lifetime", "INTEGER DEFAULT 0"),
        ("qd_users", "vip_monthly_credits_last_grant", "TEXT"),
        ("qd_users", "email_verified", "INTEGER DEFAULT 1"),
        ("qd_users", "token_version", "INTEGER DEFAULT 1"),
        ("qd_users", "timezone", "TEXT DEFAULT ''"),
        ("qd_users", "notification_settings", "TEXT DEFAULT '{}'"),
        ("qd_users", "chart_templates", "TEXT DEFAULT '[]'"),
        ("qd_users", "referred_by", "INTEGER"),
        ("qd_users", "last_login_at", "TEXT"),
        # qd_analysis_memory — columns added by DO$$ migration blocks
        ("qd_analysis_memory", "user_id", "INTEGER NOT NULL DEFAULT 1"),
        ("qd_analysis_memory", "raw_result", "TEXT DEFAULT '{}'"),
        ("qd_analysis_memory", "consensus_score", "REAL"),
        ("qd_analysis_memory", "consensus_abs", "REAL"),
        ("qd_analysis_memory", "agreement_ratio", "REAL"),
        ("qd_analysis_memory", "quality_multiplier", "REAL"),
        ("qd_analysis_memory", "actual_outcome", "TEXT DEFAULT ''"),
        ("qd_analysis_memory", "actual_return_pct", "REAL"),
    ]
    for table, column, col_type in migrations:
        try:
            db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
        except Exception:
            pass  # Column already exists — safe to ignore


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
            with open(norm, encoding="utf-8") as f:
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
"""
