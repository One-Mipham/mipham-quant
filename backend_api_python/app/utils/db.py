"""
Database Connection Utility - PostgreSQL Only

Provides unified interface for PostgreSQL database operations.

Usage:
    from app.utils.db import get_db_connection

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
        row = cursor.fetchone()
        conn.commit()

Configuration:
    DATABASE_URL=postgresql://user:password@host:port/dbname
"""

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
