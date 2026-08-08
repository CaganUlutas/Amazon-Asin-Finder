"""
Task sidebar widget.

Displays the list of crawling tasks with their status indicators
and progress information in the left panel.
"""

from __future__ import annotations

from PySide6.QtCore import Signal, Qt, QSize
from PySide6.QtGui import QColor, QPainter, QBrush, QPen, QFont
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QFrame,
    QAbstractItemView,
)

from src.core.models import TaskModel, TaskStatusEnum
from src.utils.constants import ThemeColors, UIDimensions


class TaskItemWidget(QWidget):
    """Custom widget for each task item in the sidebar list."""

    def __init__(self, task: TaskModel, parent=None):
        super().__init__(parent)
        self._task = task
        self._setup_ui()
        self.update_from_task(task)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(4)

        # Top row: name + status dot
        top_row = QHBoxLayout()
        top_row.setSpacing(8)

        self._status_dot = QLabel("●")
        self._status_dot.setFixedWidth(14)
        self._status_dot.setStyleSheet("font-size: 10px;")
        top_row.addWidget(self._status_dot)

        self._name_label = QLabel()
        self._name_label.setStyleSheet(
            "font-weight: 600; font-size: 13px; background: transparent;"
        )
        self._name_label.setWordWrap(True)
        top_row.addWidget(self._name_label, 1)

        layout.addLayout(top_row)

        # Bottom row: status text + progress
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(8)

        self._status_label = QLabel()
        self._status_label.setStyleSheet(
            "font-size: 11px; color: #8b949e; background: transparent;"
        )
        bottom_row.addWidget(self._status_label)

        bottom_row.addStretch()

        self._progress_label = QLabel()
        self._progress_label.setStyleSheet(
            "font-size: 11px; color: #8b949e; background: transparent;"
        )
        bottom_row.addWidget(self._progress_label)

        layout.addLayout(bottom_row)

    def update_from_task(self, task: TaskModel):
        """Update the widget display from a task model."""
        self._task = task

        # Display name
        self._name_label.setText(task.display_name)

        # Status dot color
        color_map = {
            TaskStatusEnum.WAITING: ThemeColors.WARNING,
            TaskStatusEnum.RUNNING: ThemeColors.ACCENT,
            TaskStatusEnum.COMPLETED: ThemeColors.SUCCESS,
            TaskStatusEnum.FAILED: ThemeColors.ERROR,
            TaskStatusEnum.CANCELLED: ThemeColors.TEXT_MUTED,
        }
        color = color_map.get(task.status, ThemeColors.TEXT_SECONDARY)
        self._status_dot.setStyleSheet(
            f"color: {color}; font-size: 10px; background: transparent;"
        )

        # Status text
        status_text_map = {
            TaskStatusEnum.WAITING: "Bekliyor",
            TaskStatusEnum.RUNNING: "Çalışıyor",
            TaskStatusEnum.COMPLETED: "Tamamlandı",
            TaskStatusEnum.FAILED: "Başarısız",
            TaskStatusEnum.CANCELLED: "İptal Edildi",
        }
        self._status_label.setText(status_text_map.get(task.status, ""))

        # Progress text
        if task.status == TaskStatusEnum.RUNNING:
            self._progress_label.setText(f"{task.progress_percent:.0f}%")
        elif task.status == TaskStatusEnum.COMPLETED:
            self._progress_label.setText(f"{task.matched_asins} ASIN")
        else:
            self._progress_label.setText("")

    @property
    def task_id(self) -> str:
        return self._task.id


class TaskSidebar(QWidget):
    """
    Left sidebar showing the list of crawling tasks.

    Emits signals when tasks are selected or actions are requested.
    """

    task_selected = Signal(str)  # task_id
    delete_requested = Signal(str)  # task_id

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sidebarFrame")
        self.setFixedWidth(UIDimensions.SIDEBAR_WIDTH)
        self._task_widgets: dict[str, TaskItemWidget] = {}
        self._setup_ui()

    def _setup_ui(self):
        main_frame = QFrame(self)
        main_frame.setObjectName("sidebarFrame")

        frame_layout = QVBoxLayout(self)
        frame_layout.setContentsMargins(0, 0, 0, 0)
        frame_layout.setSpacing(0)

        # Header
        header = QFrame()
        header.setStyleSheet(
            "background-color: #161b22; border-bottom: 1px solid #30363d;"
        )
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(16, 16, 16, 12)

        title = QLabel("Görevler")
        title.setStyleSheet(
            "font-size: 16px; font-weight: 700; color: #e6edf3; background: transparent;"
        )
        header_layout.addWidget(title)

        self._task_count = QLabel("0 görev")
        self._task_count.setStyleSheet(
            "font-size: 12px; color: #8b949e; background: transparent;"
        )
        header_layout.addWidget(self._task_count)

        frame_layout.addWidget(header)

        # Task list
        self._list_widget = QListWidget()
        self._list_widget.setSelectionMode(QAbstractItemView.SingleSelection)
        self._list_widget.setStyleSheet(
            """
            QListWidget {
                background-color: #161b22;
                border: none;
                border-radius: 0;
                padding: 4px 0;
            }
            QListWidget::item {
                border: none;
                border-radius: 0;
                padding: 0;
                margin: 0;
            }
            QListWidget::item:selected {
                background-color: #21262d;
            }
            QListWidget::item:hover:!selected {
                background-color: rgba(33, 38, 45, 0.5);
            }
            """
        )
        self._list_widget.currentItemChanged.connect(self._on_selection_changed)
        frame_layout.addWidget(self._list_widget, 1)

    def _on_selection_changed(self, current: QListWidgetItem, previous):
        """Handle task selection changes."""
        if current is None:
            return
        task_id = current.data(Qt.UserRole)
        if task_id:
            self.task_selected.emit(task_id)

    def add_task(self, task: TaskModel):
        """Add a new task to the sidebar list."""
        item = QListWidgetItem(self._list_widget)
        item.setData(Qt.UserRole, task.id)

        widget = TaskItemWidget(task)
        item.setSizeHint(QSize(UIDimensions.SIDEBAR_WIDTH - 20, 68))

        self._list_widget.addItem(item)
        self._list_widget.setItemWidget(item, widget)
        self._task_widgets[task.id] = widget

        # Select the new task
        self._list_widget.setCurrentItem(item)
        self._update_count()

    def update_task(self, task: TaskModel):
        """Update an existing task's display."""
        widget = self._task_widgets.get(task.id)
        if widget:
            widget.update_from_task(task)

    def remove_task(self, task_id: str):
        """Remove a task from the sidebar list."""
        for i in range(self._list_widget.count()):
            item = self._list_widget.item(i)
            if item.data(Qt.UserRole) == task_id:
                self._list_widget.takeItem(i)
                break
        self._task_widgets.pop(task_id, None)
        self._update_count()

    def get_selected_task_id(self) -> str | None:
        """Get the currently selected task ID."""
        current = self._list_widget.currentItem()
        if current:
            return current.data(Qt.UserRole)
        return None

    def _update_count(self):
        """Update the task count label."""
        count = self._list_widget.count()
        self._task_count.setText(f"{count} görev")
