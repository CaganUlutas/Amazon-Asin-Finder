"""
Task manager — orchestrates crawling tasks.

Coordinates the browser manager, page crawler, filter engine,
and database repository. Emits Qt signals for real-time UI updates.
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Optional

from PySide6.QtCore import QObject, Signal

from src.core.filter_engine import FilterEngine, deduplicate_asins
from src.core.models import (
    TaskModel,
    TaskStatusEnum,
    TaskUrlModel,
    UrlStatusEnum,
    FilterModel,
    CrawlProgress,
    ProductData,
)
from src.crawler.browser_manager import BrowserManager
from src.crawler.page_crawler import PageCrawler
from src.database.db_manager import DatabaseManager
from src.database.repositories import TaskRepository
from src.utils.logger import get_logger
from src.utils.url_utils import split_url_by_price

logger = get_logger(__name__)


class TaskSignals(QObject):
    """
    Qt signals emitted by the task manager for UI updates.

    All signals are emitted on the main thread via the qasync event loop.
    """

    # Emitted when a task is created
    task_created = Signal(str)  # task_id

    # Emitted when a task's status changes
    task_status_changed = Signal(str, str)  # task_id, new_status

    # Emitted on progress updates (per page processed)
    task_progress = Signal(str, int, int, int, int)  # task_id, processed_pages, total_pages, total_products, matched_asins

    # Emitted when new ASINs are found
    asins_found = Signal(str, list)  # task_id, list[str]

    # Emitted for log messages
    log_message = Signal(str, str, str)  # timestamp, level, message

    # Emitted when all tasks complete
    all_tasks_completed = Signal()

    # Emitted on error
    task_error = Signal(str, str)  # task_id, error_message


class TaskManager:
    """
    Manages the lifecycle of crawling tasks.

    Responsibilities:
    - Create, start, cancel, and delete tasks
    - Orchestrate the crawling pipeline (crawl → parse → filter → store)
    - Maintain task state in the database
    - Emit signals for UI synchronization

    Usage:
        manager = TaskManager(db_manager, browser_manager)
        signals = manager.signals

        task_id = await manager.create_task(urls, filters)
        await manager.start_task(task_id)
    """

    def __init__(
        self,
        db_manager: DatabaseManager,
        browser_manager: BrowserManager,
    ):
        self._db = db_manager
        self._browser = browser_manager
        self._repo = TaskRepository(db_manager)
        self._signals = TaskSignals()
        self._active_crawlers: dict[str, PageCrawler] = {}
        self._tasks: dict[str, TaskModel] = {}

    @property
    def signals(self) -> TaskSignals:
        """Get the Qt signals object for connecting to the UI."""
        return self._signals

    # =========================================================================
    # Task Lifecycle
    # =========================================================================

    async def create_task(
        self, urls: list[str], filters: FilterModel
    ) -> str:
        """
        Create a new crawling task.

        Args:
            urls: List of Amazon search URLs to crawl.
            filters: The filter criteria to apply.

        Returns:
            The ID of the newly created task.
        """
        # Build task model
        task = TaskModel(
            status=TaskStatusEnum.WAITING,
            filters=filters,
        )

        # Create URL models by splitting them for Smart Crawl
        for raw_url in urls:
            split_urls = split_url_by_price(raw_url.strip())
            for url in split_urls:
                task.urls.append(
                    TaskUrlModel(
                        task_id=task.id,
                        url=url,
                        status=UrlStatusEnum.WAITING,
                    )
                )

        # Persist to database
        await self._repo.create_task(task)

        # Cache in memory
        self._tasks[task.id] = task

        # Notify UI
        self._signals.task_created.emit(task.id)
        logger.info(
            "Görev oluşturuldu: %s (%d URL)", task.id[:8], len(urls)
        )

        return task.id

    async def start_task(self, task_id: str) -> None:
        """
        Start processing a task.

        Launches the crawling pipeline for all URLs in the task.

        Args:
            task_id: The task to start.
        """
        task = await self._get_task(task_id)
        if task is None:
            logger.error("Görev bulunamadı: %s", task_id)
            return

        if task.status != TaskStatusEnum.WAITING:
            logger.warning(
                "Görev zaten çalışıyor veya tamamlanmış: %s", task_id[:8]
            )
            return

        # Update status to running
        task.status = TaskStatusEnum.RUNNING
        task.started_at = datetime.now()
        await self._repo.update_task_status(task_id, TaskStatusEnum.RUNNING)
        self._signals.task_status_changed.emit(task_id, TaskStatusEnum.RUNNING.value)

        logger.info("Görev başlatıldı: %s", task_id[:8])

        try:
            await self._process_task(task)
        except Exception as e:
            logger.error("Görev işlenirken hata: %s — %s", task_id[:8], str(e))
            task.status = TaskStatusEnum.FAILED
            task.error_message = str(e)
            await self._repo.update_task_status(
                task_id, TaskStatusEnum.FAILED, str(e)
            )
            self._signals.task_status_changed.emit(
                task_id, TaskStatusEnum.FAILED.value
            )
            self._signals.task_error.emit(task_id, str(e))

    async def cancel_task(self, task_id: str) -> None:
        """Cancel a running task."""
        crawler = self._active_crawlers.get(task_id)
        if crawler:
            crawler.cancel()

        task = self._tasks.get(task_id)
        if task and task.status == TaskStatusEnum.RUNNING:
            task.status = TaskStatusEnum.CANCELLED
            await self._repo.update_task_status(
                task_id, TaskStatusEnum.CANCELLED
            )
            self._signals.task_status_changed.emit(
                task_id, TaskStatusEnum.CANCELLED.value
            )
            logger.info("Görev iptal edildi: %s", task_id[:8])

    async def delete_task(self, task_id: str) -> None:
        """Delete a task and all its data."""
        # Cancel if running
        if task_id in self._active_crawlers:
            await self.cancel_task(task_id)

        await self._repo.delete_task(task_id)
        self._tasks.pop(task_id, None)
        self._active_crawlers.pop(task_id, None)

        logger.info("Görev silindi: %s", task_id[:8])

    async def get_task(self, task_id: str) -> Optional[TaskModel]:
        """Get a task by ID (from cache or database)."""
        return await self._get_task(task_id)

    async def get_all_tasks(self) -> list[TaskModel]:
        """Get all tasks from the database."""
        tasks = await self._repo.get_all_tasks()
        # Update cache
        for task in tasks:
            self._tasks[task.id] = task
        return tasks

    async def get_task_asins(self, task_id: str) -> list[str]:
        """Get all ASINs for a completed task."""
        return await self._repo.get_asins_for_task(task_id)

    # =========================================================================
    # Task Processing Pipeline
    # =========================================================================

    async def _process_task(self, task: TaskModel) -> None:
        """
        Main task processing pipeline.

        For each URL in the task:
        1. Create a page crawler
        2. Crawl all pages
        3. Apply filters to extracted products
        4. Store matching ASINs
        5. Update progress
        """
        # Ensure browser is launched
        if not self._browser.is_launched:
            await self._browser.launch()

        # Create browser context for this task
        context = await self._browser.create_context()
        crawler = PageCrawler(self._browser)
        self._active_crawlers[task.id] = crawler

        # Initialize filter engine
        filter_engine = FilterEngine(task.filters)

        all_asins: list[str] = []
        total_products = 0
        total_processed_pages = 0
        total_pages = 0

        try:
            for url_index, url_model in enumerate(task.urls):
                if task.status == TaskStatusEnum.CANCELLED:
                    break

                # Update URL status
                url_model.status = UrlStatusEnum.RUNNING

                logger.info(
                    "URL %d/%d işleniyor: %s",
                    url_index + 1,
                    len(task.urls),
                    url_model.url,
                )

                # Crawl this URL
                async for progress, products in crawler.crawl_url(
                    context, url_model.url, task.id, url_index
                ):
                    # Update total pages on first progress
                    if progress.total_pages > 0 and url_model.page_count == 0:
                        url_model.page_count = progress.total_pages
                        total_pages += progress.total_pages
                        task.total_pages = total_pages

                    # Update processed pages
                    url_model.processed_pages = progress.current_page
                    total_processed_pages = sum(
                        u.processed_pages for u in task.urls
                    )
                    task.processed_pages = total_processed_pages

                    # Apply filters to new products
                    if products:
                        total_products += len(products)
                        task.total_products = total_products

                        filtered = filter_engine.apply(products)
                        new_asins = [p.asin for p in filtered]

                        if new_asins:
                            # Deduplicate against existing ASINs
                            existing = set(all_asins)
                            truly_new = [
                                a for a in new_asins if a not in existing
                            ]

                            if truly_new:
                                all_asins.extend(truly_new)
                                task.asins = list(all_asins)

                                # Store in database if task is still active
                                if task.id in self._tasks and task.status != TaskStatusEnum.CANCELLED:
                                    asin_tuples = [
                                        (a, url_model.url, progress.current_page)
                                        for a in truly_new
                                    ]
                                    try:
                                        await self._repo.add_asins(task.id, asin_tuples)
                                    except Exception as e:
                                        logger.debug("ASIN kaydedilemedi (görev silinmiş olabilir): %s", e)

                                # Notify UI
                                self._signals.asins_found.emit(
                                    task.id, truly_new
                                )

                        task.matched_asins = len(all_asins)

                    if task.id not in self._tasks or task.status == TaskStatusEnum.CANCELLED:
                        break

                    # Update progress in database
                    try:
                        await self._repo.update_task_progress(
                            task.id,
                            task.processed_pages,
                            task.total_pages,
                            task.total_products,
                            task.matched_asins,
                        )
                    except Exception:
                        pass

                    # Emit progress signal
                    self._signals.task_progress.emit(
                        task.id,
                        task.processed_pages,
                        task.total_pages,
                        task.total_products,
                        task.matched_asins,
                    )

                    # Handle URL-level completion/failure
                    if progress.status in (
                        TaskStatusEnum.COMPLETED,
                        TaskStatusEnum.FAILED,
                    ):
                        url_model.status = (
                            UrlStatusEnum.COMPLETED
                            if progress.status == TaskStatusEnum.COMPLETED
                            else UrlStatusEnum.FAILED
                        )

            # Task completed
            if task.status != TaskStatusEnum.CANCELLED:
                task.status = TaskStatusEnum.COMPLETED
                task.completed_at = datetime.now()
                task.asins = deduplicate_asins(all_asins)

                await self._repo.update_task_status(
                    task.id, TaskStatusEnum.COMPLETED
                )
                self._signals.task_status_changed.emit(
                    task.id, TaskStatusEnum.COMPLETED.value
                )

                logger.info(
                    "Görev tamamlandı: %s — %d ASIN bulundu.",
                    task.id[:8],
                    len(task.asins),
                )

        except Exception as e:
            raise
        finally:
            # Cleanup
            self._active_crawlers.pop(task.id, None)
            try:
                await context.close()
            except Exception:
                pass

    # =========================================================================
    # Batch Operations
    # =========================================================================

    async def start_all_waiting(self) -> None:
        """Start all tasks that are in 'waiting' status, sequentially."""
        tasks = await self.get_all_tasks()
        waiting = [t for t in tasks if t.status == TaskStatusEnum.WAITING]

        if not waiting:
            logger.info("Bekleyen görev yok.")
            return

        logger.info("%d bekleyen görev başlatılıyor...", len(waiting))

        for task in waiting:
            if task.status == TaskStatusEnum.WAITING:
                await self.start_task(task.id)

        self._signals.all_tasks_completed.emit()

    async def cancel_all(self) -> None:
        """Cancel all running tasks."""
        for task_id, crawler in list(self._active_crawlers.items()):
            await self.cancel_task(task_id)

    # =========================================================================
    # Helpers
    # =========================================================================

    async def _get_task(self, task_id: str) -> Optional[TaskModel]:
        """Get task from cache or database."""
        if task_id in self._tasks:
            return self._tasks[task_id]
        task = await self._repo.get_task(task_id)
        if task:
            self._tasks[task.id] = task
        return task

    async def cleanup(self) -> None:
        """Clean up resources on application shutdown."""
        await self.cancel_all()
        logger.info("Task manager temizlendi.")
    async def cleanup(self) -> None:
        """Clean up resources on application shutdown."""
        await self.cancel_all()
        logger.info("Task manager temizlendi.")
