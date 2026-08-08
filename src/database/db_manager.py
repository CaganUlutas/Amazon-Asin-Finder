"""
SQLite database connection manager.

Provides async database access using aiosqlite with connection pooling
and context manager support for safe resource cleanup.
"""

from __future__ import annotations

import aiosqlite
from pathlib import Path
from typing import Optional

from src.utils.constants import DB_PATH
from src.utils.logger import get_logger

logger = get_logger(__name__)


class DatabaseManager:
    """
    Manages SQLite database connections with async support.

    Uses a singleton-like pattern — one connection per application instance.
    All database operations go through this manager to ensure consistent
    connection handling and proper cleanup.

    Usage:
        db = DatabaseManager()
        await db.initialize()

        async with db.connection() as conn:
            cursor = await conn.execute("SELECT * FROM tasks")
            rows = await cursor.fetchall()

        await db.close()
    """

    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize the database manager.

        Args:
            db_path: Path to the SQLite database file.
                     Defaults to the configured DB_PATH.
        """
        self._db_path = db_path or DB_PATH
        self._connection: Optional[aiosqlite.Connection] = None
        self._initialized = False

    async def initialize(self) -> None:
        """
        Initialize the database connection and ensure schema exists.

        This method is idempotent — calling it multiple times is safe.
        """
        if self._initialized:
            return

        logger.info("Veritabanı başlatılıyor: %s", self._db_path)

        # Ensure parent directory exists
        self._db_path.parent.mkdir(parents=True, exist_ok=True)

        # Open connection
        self._connection = await aiosqlite.connect(str(self._db_path))

        # Enable WAL mode for better concurrent read performance
        await self._connection.execute("PRAGMA journal_mode=WAL")
        # Enable foreign keys
        await self._connection.execute("PRAGMA foreign_keys=ON")

        # Row factory for dict-like access
        self._connection.row_factory = aiosqlite.Row

        # Run migrations
        from src.database.migrations import run_migrations
        await run_migrations(self._connection)

        self._initialized = True
        logger.info("Veritabanı başarıyla başlatıldı.")

    async def get_connection(self) -> aiosqlite.Connection:
        """
        Get the active database connection.

        Returns:
            The aiosqlite Connection instance.

        Raises:
            RuntimeError: If the database has not been initialized.
        """
        if not self._initialized or self._connection is None:
            await self.initialize()
        return self._connection

    async def close(self) -> None:
        """Close the database connection and release resources."""
        if self._connection is not None:
            await self._connection.close()
            self._connection = None
            self._initialized = False
            logger.info("Veritabanı bağlantısı kapatıldı.")

    async def execute(self, sql: str, params: tuple = ()) -> aiosqlite.Cursor:
        """
        Execute a single SQL statement.

        Args:
            sql: The SQL query string.
            params: Query parameters.

        Returns:
            The cursor after execution.
        """
        conn = await self.get_connection()
        cursor = await conn.execute(sql, params)
        await conn.commit()
        return cursor

    async def execute_many(self, sql: str, params_list: list[tuple]) -> None:
        """
        Execute an SQL statement with multiple parameter sets.

        Args:
            sql: The SQL query string with placeholders.
            params_list: List of parameter tuples.
        """
        conn = await self.get_connection()
        await conn.executemany(sql, params_list)
        await conn.commit()

    async def fetch_one(self, sql: str, params: tuple = ()) -> Optional[aiosqlite.Row]:
        """
        Execute a query and return the first row.

        Args:
            sql: The SQL query string.
            params: Query parameters.

        Returns:
            The first row, or None if no results.
        """
        conn = await self.get_connection()
        cursor = await conn.execute(sql, params)
        return await cursor.fetchone()

    async def fetch_all(self, sql: str, params: tuple = ()) -> list[aiosqlite.Row]:
        """
        Execute a query and return all rows.

        Args:
            sql: The SQL query string.
            params: Query parameters.

        Returns:
            A list of all matching rows.
        """
        conn = await self.get_connection()
        cursor = await conn.execute(sql, params)
        return await cursor.fetchall()
