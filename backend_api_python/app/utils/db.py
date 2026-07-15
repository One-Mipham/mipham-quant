"""
Database Connection Utility — PostgreSQL / SQLite facade.

Provides unified interface for database operations. Switches between
PostgreSQL and SQLite backends based on DB_TYPE environment variable.
All symbols are re-exported so that 46+ callers can import from this
single module regardless of the active backend.

Usage:
    from app.utils.db import get_db_connection

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
        row = cursor.fetchone()

Configuration:
    DB_TYPE=postgresql|sqlite  (default: postgresql)
    DATABASE_URL=postgresql://user:password@host:port/dbname
"""

import os as _os

_db_type = _os.getenv("DB_TYPE", "postgresql").lower()

if _db_type == "sqlite":
    from app.utils.db_sqlite import (
        close_db_connection,
        get_db_connection,
        get_pg_connection,
        get_pg_connection_sync,
        init_database,
    )

    # Compatibility alias — some callers use the postgres naming
    get_db_connection_sync = get_pg_connection_sync  # type: ignore

    def get_db_type() -> str:
        return "sqlite"

    def is_postgres() -> bool:
        return False

else:
    from app.utils.db_postgres import (
        close_pool,
        get_pg_connection,
        get_pg_connection_sync,
    )

    # Compatibility aliases — most callers use the generic names
    get_db_connection = get_pg_connection  # type: ignore
    get_db_connection_sync = get_pg_connection_sync  # type: ignore

    def init_database():
        """PostgreSQL: schema is initialised by init.sql during Docker startup.
        This stub exists so callers can unconditionally call init_database()
        regardless of backend.
        """
        pass

    def close_db_connection():
        """Close all connection pool connections."""
        close_pool()

    def get_db_type() -> str:
        return "postgresql"

    def is_postgres() -> bool:
        return True
