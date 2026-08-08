"""
Main application window.

Assembles all UI components into a three-panel layout:
- Left: Task sidebar
- Center: Task detail panel (setup/results)
- Right: Log panel
- Bottom: Progress bar
"""

from __future__ import annotations

import asyncio
from typing import Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QIcon, QCloseEvent
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QSplitter,
    QFrame,
    QMessageBox,
)

from qasync import asyncSlot

from src.core.models import TaskModel, TaskStatusEnum, FilterModel
from src.core.task_manager import TaskManager
from src.crawler.browser_manager import BrowserManager
from src.database.db_manager import DatabaseManager
from src.ui.widgets.task_sidebar import TaskSidebar
from src.ui.widgets.task_detail_panel import TaskDetailPanel
from src.ui.widgets.log_panel import LogPanel
from src.ui.widgets.progress_bar import BottomProgressBar
from src.utils.constants import APP_NAME, APP_VERSION, UIDimensions
from src.utils.logger import get_logger

logger = get_logger(__name__)


class MainWindow(QMainWindow):
    """
    Main application window.

    Layout:
    ┌──────────┬─────────────────────┬────────────┐
    │          │                     │            │
    │  Task    │   Task Detail       │   Log      │
    │  Sidebar │   Panel             │   Panel    │
    │          │                     │            │
    ├──────────┴─────────────────────┴────────────┤
    │              Progress Bar                    │
    └──────────────────────────────────────────────┘
    """

    def __init__(
        self,
        db_manager: DatabaseManager,
        browser_manager: BrowserManager,
        task_manager: TaskManager,
    ):
        super().__init__()
        self._db = db_manager
        self._browser = browser_manager
        self._task_manager = task_manager
        self._progress_timer = QTimer()
        self._current_task: Optional[TaskModel] = None

        self._setup_window()
        self._setup_ui()
        self._connect_signals()
        self._start_progress_timer()

    def _setup_window(self):
        """Configure the main window properties."""
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        self.setMinimumSize(
            UIDimensions.WINDOW_MIN_WIDTH,
            UIDimensions.WINDOW_MIN_HEIGHT,
        )
        self.resize(
            UIDimensions.WINDOW_DEFAULT_WIDTH,
            UIDimensions.WINDOW_DEFAULT_HEIGHT,
        )

    def _setup_ui(self):
        """Build the complete UI layout."""
        # Central widget
        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Top area: three-panel layout
        content_layout = QHBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # Left sidebar
        self._sidebar = TaskSidebar()
        content_layout.addWidget(self._sidebar)

        # Center panel (with separator frame)
        center_container = QFrame()
        center_container.setObjectName("centerFrame")
        center_layout = QVBoxLayout(center_container)
        center_layout.setContentsMargins(0, 0, 0, 0)

        # Top toolbar in center
        toolbar = QFrame()
        toolbar.setStyleSheet(
            "background-color: #161b22; border-bottom: 1px solid #30363d;"
        )
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(24, 10, 24, 10)

        from PySide6.QtWidgets import QPushButton

        self._new_task_btn = QPushButton("  +  Yeni Görev")
        self._new_task_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #238636;
                border: none;
                border-radius: 6px;
                color: white;
                font-size: 13px;
                font-weight: 600;
                padding: 8px 20px;
            }
            QPushButton:hover {
                background-color: #2ea043;
            }
            QPushButton:pressed {
                background-color: #1a7f37;
            }
            """
        )
        self._new_task_btn.clicked.connect(self._on_new_task)
        toolbar_layout.addWidget(self._new_task_btn)

        toolbar_layout.addStretch()

        center_layout.addWidget(toolbar)

        # Task detail panel
        self._detail_panel = TaskDetailPanel()
        center_layout.addWidget(self._detail_panel, 1)

        content_layout.addWidget(center_container, 1)

        # Right log panel
        self._log_panel = LogPanel()
        content_layout.addWidget(self._log_panel)

        main_layout.addLayout(content_layout, 1)

        # Bottom progress bar
        self._progress_bar = BottomProgressBar()
        main_layout.addWidget(self._progress_bar)

    def _connect_signals(self):
        """Connect all signals between components."""
        # Sidebar
        self._sidebar.task_selected.connect(self._on_task_selected)

        # Detail panel
        self._detail_panel.start_task_requested.connect(self._on_start_task)
        self._detail_panel.cancel_task_requested.connect(self._on_cancel_task)
        self._detail_panel.delete_task_requested.connect(self._on_delete_task)

        # Task manager signals
        signals = self._task_manager.signals
        signals.task_created.connect(self._on_task_created)
        signals.task_status_changed.connect(self._on_task_status_changed)
        signals.task_progress.connect(self._on_task_progress)
        signals.asins_found.connect(self._on_asins_found)
        signals.task_error.connect(self._on_task_error)

    def _start_progress_timer(self):
        """Start a timer to update elapsed time display."""
        self._progress_timer.setInterval(1000)  # 1 second
        self._progress_timer.timeout.connect(self._update_elapsed_time)
        self._progress_timer.start()

    # =========================================================================
    # Event Handlers
    # =========================================================================

    def _on_new_task(self):
        """Handle 'New Task' button click."""
        self._detail_panel.show_setup_mode()

    @asyncSlot(str)
    async def _on_task_selected(self, task_id: str):
        """Handle task selection in the sidebar."""
        task = await self._task_manager.get_task(task_id)
        if task:
            self._current_task = task
            self._detail_panel.show_task_details(task)
            self._update_progress_bar(task)

    @asyncSlot(list, object)
    async def _on_start_task(self, urls: list[str], filters: FilterModel):
        """Handle start task request from the detail panel."""
        try:
            task_id = await self._task_manager.create_task(urls, filters)
            # Start the task
            asyncio.ensure_future(self._task_manager.start_task(task_id))
        except Exception as e:
            logger.error("Görev başlatılamadı: %s", str(e))
            self._detail_panel.show_setup_mode()

    @asyncSlot(str)
    async def _on_cancel_task(self, task_id: str):
        """Handle cancel task request."""
        await self._task_manager.cancel_task(task_id)

    @asyncSlot(str)
    async def _on_delete_task(self, task_id: str):
        """Handle delete task request."""
        await self._task_manager.delete_task(task_id)
        self._sidebar.remove_task(task_id)
        self._detail_panel.show_empty_state()
        self._progress_bar.reset()

    @asyncSlot(str)
    async def _on_task_created(self, task_id: str):
        """Handle task created signal from task manager."""
        task = await self._task_manager.get_task(task_id)
        if task:
            self._current_task = task
            self._sidebar.add_task(task)
            self._detail_panel.show_task_details(task)

    @asyncSlot(str, str)
    async def _on_task_status_changed(self, task_id: str, status: str):
        """Handle task status change signal."""
        task = await self._task_manager.get_task(task_id)
        if task:
            self._sidebar.update_task(task)
            if self._current_task and self._current_task.id == task_id:
                self._current_task = task
                self._detail_panel.update_task(task)
                self._update_progress_bar(task)

                # Update bottom bar status
                if status == TaskStatusEnum.RUNNING.value:
                    self._progress_bar.set_running()
                elif status == TaskStatusEnum.COMPLETED.value:
                    self._progress_bar.set_completed()
                elif status == TaskStatusEnum.FAILED.value:
                    self._progress_bar.set_failed()

    @asyncSlot(str, int, int, int, int)
    async def _on_task_progress(
        self,
        task_id: str,
        processed_pages: int,
        total_pages: int,
        total_products: int,
        matched_asins: int,
    ):
        """Handle task progress update signal."""
        task = await self._task_manager.get_task(task_id)
        if task:
            self._sidebar.update_task(task)
            if self._current_task and self._current_task.id == task_id:
                self._current_task = task
                self._detail_panel.update_task(task)
                self._update_progress_bar(task)

    def _on_asins_found(self, task_id: str, asins: list[str]):
        """Handle new ASINs found signal."""
        self._detail_panel.add_asins(task_id, asins)

    def _on_task_error(self, task_id: str, error_message: str):
        """Handle task error signal."""
        logger.error("Görev hatası [%s]: %s", task_id[:8], error_message)

    def _update_elapsed_time(self):
        """Timer callback to update elapsed time display."""
        if self._current_task and self._current_task.status == TaskStatusEnum.RUNNING:
            self._update_progress_bar(self._current_task)

    def _update_progress_bar(self, task: TaskModel):
        """Update the bottom progress bar with task data."""
        self._progress_bar.update_progress(
            processed_pages=task.processed_pages,
            total_pages=task.total_pages,
            total_products=task.total_products,
            matched_asins=task.matched_asins,
            elapsed_seconds=task.elapsed_seconds,
            eta_seconds=task.estimated_remaining_seconds,
        )

    # =========================================================================
    # Lifecycle
    # =========================================================================

    @asyncSlot()
    async def _load_existing_tasks(self):
        """Load existing tasks from the database on startup."""
        try:
            tasks = await self._task_manager.get_all_tasks()
            for task in tasks:
                self._sidebar.add_task(task)
            if tasks:
                logger.info("%d mevcut görev yüklendi.", len(tasks))
        except Exception as e:
            logger.error("Mevcut görevler yüklenirken hata: %s", str(e))

    async def initialize(self):
        """Initialize the window after event loop is running."""
        await self._load_existing_tasks()
        self._log_panel.append_log("INFO", f"{APP_NAME} v{APP_VERSION} başlatıldı.")

    def closeEvent(self, event: QCloseEvent):
        """Handle window close — clean up resources."""
        # Schedule cleanup
        asyncio.ensure_future(self._cleanup())
        event.accept()

    async def _cleanup(self):
        """Clean up all resources before exit."""
        logger.info("Uygulama kapatılıyor...")
        self._progress_timer.stop()
        self._log_panel.cleanup()
        await self._task_manager.cleanup()
        await self._browser.shutdown()
        await self._db.close()
        logger.info("Tüm kaynaklar temizlendi.")
