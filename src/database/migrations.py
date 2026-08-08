"""
Database schema migrations.

Handles creation and versioned updates of the SQLite database schema.
Uses a simple version tracking table to manage migration state.
"""

from __future__ import annotations

import aiosqlite

from src.utils.logger import get_logger

logger = get_logger(__name__)

# Current schema version
CURRENT_VERSION = 1

# =============================================================================
# Migration Scripts (ordered by version)
# =============================================================================

MIGRATIONS: dict[int, list[str]] = {
    1: [
        # Tasks table — top-level task container
        """
        CREATE TABLE IF NOT EXISTS tasks (
            id TEXT PRIMARY KEY,
            status TEXT NOT NULL DEFAULT 'waiting'
                CHECK(status IN ('waiting', 'running', 'completed', 'failed', 'cancelled')),
            created_at TEXT NOT NULL,
            started_at TEXT,
            completed_at TEXT,
            total_pages INTEGER NOT NULL DEFAULT 0,
            processed_pages INTEGER NOT NULL DEFAULT 0,
            total_products INTEGER NOT NULL DEFAULT 0,
            matched_asins INTEGER NOT NULL DEFAULT 0,
            error_message TEXT
        )
        """,

        # Task URLs — search URLs belonging to a task
        """
        CREATE TABLE IF NOT EXISTS task_urls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id TEXT NOT NULL,
            url TEXT NOT NULL,
            page_count INTEGER NOT NULL DEFAULT 0,
            processed_pages INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'waiting'
                CHECK(status IN ('waiting', 'running', 'completed', 'failed')),
            FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE
        )
        """,

        # Task filters — filter criteria for a task
        """
        CREATE TABLE IF NOT EXISTS task_filters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id TEXT NOT NULL UNIQUE,
            min_price REAL,
            max_price REAL,
            min_rating REAL,
            max_rating REAL,
            min_reviews INTEGER,
            max_reviews INTEGER,
            prime_only INTEGER NOT NULL DEFAULT 0,
            exclude_sponsored INTEGER NOT NULL DEFAULT 0,
            excluded_brands TEXT DEFAULT '[]',
            keywords TEXT DEFAULT '[]',
            FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE
        )
        """,

        # ASINs — collected ASIN results
        """
        CREATE TABLE IF NOT EXISTS asins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id TEXT NOT NULL,
            asin TEXT NOT NULL,
            source_url TEXT,
            page_number INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE
        )
        """,

        # Indexes for common queries
        "CREATE INDEX IF NOT EXISTS idx_task_urls_task_id ON task_urls(task_id)",
        "CREATE INDEX IF NOT EXISTS idx_asins_task_id ON asins(task_id)",
        "CREATE INDEX IF NOT EXISTS idx_asins_asin ON asins(asin)",
        "CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)",

        # Schema version tracking table
        """
        CREATE TABLE IF NOT EXISTS schema_version (
            version INTEGER PRIMARY KEY,
            applied_at TEXT NOT NULL
        )
        """,
    ],
}


async def get_current_version(conn: aiosqlite.Connection) -> int:
    """
    Get the current schema version from the database.

    Returns 0 if the schema_version table doesn't exist yet.
    """
    try:
        cursor = await conn.execute(
            "SELECT MAX(version) FROM schema_version"
        )
        row = await cursor.fetchone()
        return row[0] if row and row[0] is not None else 0
    except aiosqlite.OperationalError:
        # Table doesn't exist yet
        return 0


async def run_migrations(conn: aiosqlite.Connection) -> None:
    """
    Run all pending database migrations.

    Compares the current schema version with available migrations
    and applies any that haven't been run yet.
    """
    current_version = await get_current_version(conn)
    logger.info("Mevcut veritabanı şema versiyonu: %d", current_version)

    if current_version >= CURRENT_VERSION:
        logger.info("Veritabanı şeması güncel.")
        return

    for version in range(current_version + 1, CURRENT_VERSION + 1):
        if version not in MIGRATIONS:
            logger.warning("Migration v%d bulunamadı, atlanıyor.", version)
            continue

        logger.info("Migration v%d uygulanıyor...", version)

        for sql in MIGRATIONS[version]:
            await conn.execute(sql)

        # Record the migration
        from datetime import datetime
        await conn.execute(
            "INSERT OR REPLACE INTO schema_version (version, applied_at) VALUES (?, ?)",
            (version, datetime.now().isoformat()),
        )

        await conn.commit()
        logger.info("Migration v%d başarıyla uygulandı.", version)

    logger.info("Tüm migration'lar tamamlandı. Güncel versiyon: %d", CURRENT_VERSION)
