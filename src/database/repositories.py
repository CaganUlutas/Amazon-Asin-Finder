"""
Database repositories for CRUD operations.

Provides a clean data access layer between the business logic
and the SQLite database. Each repository handles operations
for a specific domain entity.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Optional

from src.core.models import (
    TaskModel,
    TaskStatusEnum,
    TaskUrlModel,
    UrlStatusEnum,
    FilterModel,
)
from src.database.db_manager import DatabaseManager
from src.utils.logger import get_logger

logger = get_logger(__name__)


class TaskRepository:
    """
    Repository for Task CRUD operations.

    Handles persistence of tasks, their associated URLs, filters, and ASINs.
    """

    def __init__(self, db: DatabaseManager):
        self._db = db

    # =========================================================================
    # Task Operations
    # =========================================================================

    async def create_task(self, task: TaskModel) -> str:
        """
        Persist a new task with its URLs and filters.

        Args:
            task: The TaskModel to persist.

        Returns:
            The task ID.
        """
        conn = await self._db.get_connection()

        # Insert task
        await conn.execute(
            """
            INSERT INTO tasks (id, status, created_at, total_pages, processed_pages,
                               total_products, matched_asins)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                task.id,
                task.status.value,
                task.created_at.isoformat(),
                task.total_pages,
                task.processed_pages,
                task.total_products,
                task.matched_asins,
            ),
        )

        # Insert URLs
        for url_model in task.urls:
            await conn.execute(
                """
                INSERT INTO task_urls (task_id, url, page_count, processed_pages, status)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    task.id,
                    url_model.url,
                    url_model.page_count,
                    url_model.processed_pages,
                    url_model.status.value,
                ),
            )

        # Insert filters
        filters = task.filters
        await conn.execute(
            """
            INSERT INTO task_filters (task_id, min_price, max_price, min_rating,
                                      max_rating, min_reviews, max_reviews,
                                      prime_only, exclude_sponsored,
                                      excluded_brands, keywords)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                task.id,
                filters.min_price,
                filters.max_price,
                filters.min_rating,
                filters.max_rating,
                filters.min_reviews,
                filters.max_reviews,
                1 if filters.prime_only else 0,
                1 if filters.exclude_sponsored else 0,
                json.dumps(filters.excluded_brands),
                json.dumps(filters.keywords),
            ),
        )

        await conn.commit()
        logger.info("Görev oluşturuldu: %s", task.id)
        return task.id

    async def get_task(self, task_id: str) -> Optional[TaskModel]:
        """
        Retrieve a task by its ID, including URLs and filters.

        Args:
            task_id: The task UUID.

        Returns:
            The TaskModel, or None if not found.
        """
        row = await self._db.fetch_one(
            "SELECT * FROM tasks WHERE id = ?", (task_id,)
        )
        if row is None:
            return None

        task = self._row_to_task(row)

        # Load URLs
        url_rows = await self._db.fetch_all(
            "SELECT * FROM task_urls WHERE task_id = ? ORDER BY id", (task_id,)
        )
        task.urls = [self._row_to_url(r) for r in url_rows]

        # Load filters
        filter_row = await self._db.fetch_one(
            "SELECT * FROM task_filters WHERE task_id = ?", (task_id,)
        )
        if filter_row:
            task.filters = self._row_to_filter(filter_row)

        # Load ASINs
        asin_rows = await self._db.fetch_all(
            "SELECT asin FROM asins WHERE task_id = ? ORDER BY id", (task_id,)
        )
        task.asins = [r["asin"] for r in asin_rows]

        return task

    async def get_all_tasks(self) -> list[TaskModel]:
        """Retrieve all tasks ordered by creation date (newest first)."""
        rows = await self._db.fetch_all(
            "SELECT * FROM tasks ORDER BY created_at DESC"
        )
        tasks = []
        for row in rows:
            task = self._row_to_task(row)

            # Load URLs for each task
            url_rows = await self._db.fetch_all(
                "SELECT * FROM task_urls WHERE task_id = ? ORDER BY id",
                (task.id,),
            )
            task.urls = [self._row_to_url(r) for r in url_rows]

            # Load ASIN count
            asin_rows = await self._db.fetch_all(
                "SELECT asin FROM asins WHERE task_id = ?", (task.id,)
            )
            task.asins = [r["asin"] for r in asin_rows]

            tasks.append(task)

        return tasks

    async def update_task_status(
        self,
        task_id: str,
        status: TaskStatusEnum,
        error_message: Optional[str] = None,
    ) -> None:
        """Update a task's status and optionally set an error message."""
        updates = {"status": status.value}
        params = [status.value]

        if status == TaskStatusEnum.RUNNING:
            await self._db.execute(
                "UPDATE tasks SET status = ?, started_at = ? WHERE id = ?",
                (status.value, datetime.now().isoformat(), task_id),
            )
        elif status in (TaskStatusEnum.COMPLETED, TaskStatusEnum.FAILED, TaskStatusEnum.CANCELLED):
            await self._db.execute(
                "UPDATE tasks SET status = ?, completed_at = ?, error_message = ? WHERE id = ?",
                (status.value, datetime.now().isoformat(), error_message, task_id),
            )
        else:
            await self._db.execute(
                "UPDATE tasks SET status = ? WHERE id = ?",
                (status.value, task_id),
            )

    async def update_task_progress(
        self,
        task_id: str,
        processed_pages: int,
        total_pages: int,
        total_products: int,
        matched_asins: int,
    ) -> None:
        """Update a task's progress counters."""
        await self._db.execute(
            """
            UPDATE tasks
            SET processed_pages = ?, total_pages = ?,
                total_products = ?, matched_asins = ?
            WHERE id = ?
            """,
            (processed_pages, total_pages, total_products, matched_asins, task_id),
        )

    async def delete_task(self, task_id: str) -> None:
        """Delete a task and all its associated data (cascading)."""
        await self._db.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        logger.info("Görev silindi: %s", task_id)

    # =========================================================================
    # URL Operations
    # =========================================================================

    async def update_url_status(
        self, url_id: int, status: UrlStatusEnum, page_count: int = 0, processed_pages: int = 0
    ) -> None:
        """Update a task URL's status and progress."""
        await self._db.execute(
            """
            UPDATE task_urls
            SET status = ?, page_count = ?, processed_pages = ?
            WHERE id = ?
            """,
            (status.value, page_count, processed_pages, url_id),
        )

    async def update_url_progress(
        self, url_id: int, processed_pages: int
    ) -> None:
        """Update a task URL's processed page count."""
        await self._db.execute(
            "UPDATE task_urls SET processed_pages = ? WHERE id = ?",
            (processed_pages, url_id),
        )

    # =========================================================================
    # ASIN Operations
    # =========================================================================

    async def add_asins(
        self,
        task_id: str,
        asins: list[tuple[str, str, int]],
    ) -> None:
        """
        Bulk insert ASINs for a task.

        Args:
            task_id: The parent task ID.
            asins: List of (asin, source_url, page_number) tuples.
        """
        if not asins:
            return

        now = datetime.now().isoformat()
        params = [
            (task_id, asin, source_url, page_number, now)
            for asin, source_url, page_number in asins
        ]
        await self._db.execute_many(
            """
            INSERT INTO asins (task_id, asin, source_url, page_number, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            params,
        )

    async def get_asins_for_task(self, task_id: str) -> list[str]:
        """Get all unique ASINs for a task."""
        rows = await self._db.fetch_all(
            "SELECT DISTINCT asin FROM asins WHERE task_id = ? ORDER BY id",
            (task_id,),
        )
        return [row["asin"] for row in rows]

    async def get_asin_count(self, task_id: str) -> int:
        """Get the count of unique ASINs for a task."""
        row = await self._db.fetch_one(
            "SELECT COUNT(DISTINCT asin) as cnt FROM asins WHERE task_id = ?",
            (task_id,),
        )
        return row["cnt"] if row else 0

    # =========================================================================
    # Private Helpers — Row-to-Model Mapping
    # =========================================================================

    @staticmethod
    def _row_to_task(row) -> TaskModel:
        """Convert a database row to a TaskModel."""
        return TaskModel(
            id=row["id"],
            status=TaskStatusEnum(row["status"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            started_at=(
                datetime.fromisoformat(row["started_at"])
                if row["started_at"]
                else None
            ),
            completed_at=(
                datetime.fromisoformat(row["completed_at"])
                if row["completed_at"]
                else None
            ),
            total_pages=row["total_pages"],
            processed_pages=row["processed_pages"],
            total_products=row["total_products"],
            matched_asins=row["matched_asins"],
            error_message=row["error_message"],
        )

    @staticmethod
    def _row_to_url(row) -> TaskUrlModel:
        """Convert a database row to a TaskUrlModel."""
        return TaskUrlModel(
            id=row["id"],
            task_id=row["task_id"],
            url=row["url"],
            page_count=row["page_count"],
            processed_pages=row["processed_pages"],
            status=UrlStatusEnum(row["status"]),
        )

    @staticmethod
    def _row_to_filter(row) -> FilterModel:
        """Convert a database row to a FilterModel."""
        return FilterModel(
            min_price=row["min_price"],
            max_price=row["max_price"],
            min_rating=row["min_rating"],
            max_rating=row["max_rating"],
            min_reviews=row["min_reviews"],
            max_reviews=row["max_reviews"],
            prime_only=bool(row["prime_only"]),
            exclude_sponsored=bool(row["exclude_sponsored"]),
            excluded_brands=json.loads(row["excluded_brands"] or "[]"),
            keywords=json.loads(row["keywords"] or "[]"),
        )
