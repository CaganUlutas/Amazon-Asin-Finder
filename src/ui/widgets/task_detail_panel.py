"""
Task detail panel widget.

Displays the details of a selected task including:
- URL input and filter configuration (for new tasks)
- Progress statistics (for running/completed tasks)
- ASIN results list
- Export buttons
"""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QScrollArea,
    QPlainTextEdit,
    QStackedWidget,
    QFileDialog,
    QGridLayout,
)

from src.core.models import TaskModel, TaskStatusEnum
from src.core.export_manager import ExportManager
from src.ui.widgets.url_input import UrlInputWidget
from src.ui.widgets.filter_panel import FilterPanel
from src.utils.constants import ThemeColors


class TaskDetailPanel(QWidget):
    """
    Central panel showing task details.

    Has two modes:
    1. Setup mode: URL input + filters + start button (for new tasks)
    2. Results mode: progress stats + ASIN list + export buttons (running/completed)

    Emits signals for task creation and control.
    """

    # Signal: user wants to start a new task with (urls, filters)
    start_task_requested = Signal(list, object)  # urls, FilterModel
    cancel_task_requested = Signal(str)  # task_id
    delete_task_requested = Signal(str)  # task_id

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_task: Optional[TaskModel] = None
        self._export_manager = ExportManager()
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        # Stacked widget for setup/results modes
        self._stack = QStackedWidget()

        # =====================================================================
        # Page 0: Setup Mode (URL input + Filters)
        # =====================================================================
        setup_page = QWidget()
        setup_layout = QVBoxLayout(setup_page)
        setup_layout.setContentsMargins(0, 0, 0, 0)
        setup_layout.setSpacing(16)

        # Scrollable area for setup content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(
            "QScrollArea { border: none; background: transparent; }"
        )

        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 0, 8, 0)
        scroll_layout.setSpacing(20)

        # URL Input
        self._url_input = UrlInputWidget()
        scroll_layout.addWidget(self._url_input)

        # Filters
        self._filter_panel = FilterPanel()
        scroll_layout.addWidget(self._filter_panel)

        scroll_layout.addStretch()
        scroll.setWidget(scroll_content)
        setup_layout.addWidget(scroll, 1)

        # Start button
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self._start_btn = QPushButton("  ▶  Taramayı Başlat")
        self._start_btn.setObjectName("primaryButton")
        self._start_btn.setMinimumHeight(44)
        self._start_btn.setMinimumWidth(200)
        self._start_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #0078d4;
                border: none;
                border-radius: 8px;
                color: white;
                font-size: 14px;
                font-weight: 600;
                padding: 12px 32px;
            }
            QPushButton:hover {
                background-color: #1a8fff;
            }
            QPushButton:pressed {
                background-color: #005a9e;
            }
            QPushButton:disabled {
                background-color: #21262d;
                color: #6e7681;
            }
            """
        )
        self._start_btn.clicked.connect(self._on_start_clicked)
        btn_layout.addWidget(self._start_btn)
        btn_layout.addStretch()
        setup_layout.addLayout(btn_layout)

        self._stack.addWidget(setup_page)

        # =====================================================================
        # Page 1: Results Mode (Stats + ASINs)
        # =====================================================================
        results_page = QWidget()
        results_layout = QVBoxLayout(results_page)
        results_layout.setContentsMargins(0, 0, 0, 0)
        results_layout.setSpacing(16)

        # Task info header
        task_header = QHBoxLayout()

        self._task_name_label = QLabel("Görev")
        self._task_name_label.setStyleSheet(
            "font-size: 18px; font-weight: 700; color: #e6edf3;"
        )
        task_header.addWidget(self._task_name_label)

        task_header.addStretch()

        self._task_status_label = QLabel("Bekliyor")
        self._task_status_label.setStyleSheet(
            "font-size: 13px; font-weight: 600; padding: 4px 12px; "
            "border-radius: 12px; background-color: #21262d;"
        )
        task_header.addWidget(self._task_status_label)

        results_layout.addLayout(task_header)

        # Stats grid
        stats_card = QFrame()
        stats_card.setObjectName("cardFrame")
        stats_grid = QGridLayout(stats_card)
        stats_grid.setContentsMargins(16, 16, 16, 16)
        stats_grid.setSpacing(12)

        self._stat_labels = {}
        stat_items = [
            ("pages", "İşlenen Sayfa", "0 / 0"),
            ("products", "Toplanan Eşsiz Ürün", "0"),
            ("asins", "Eşleşen ASIN", "0"),
            ("elapsed", "Geçen Süre", "00:00:00"),
            ("eta", "Tahmini Kalan", "—"),
            ("urls", "URL Sayısı", "0"),
        ]

        for i, (key, label_text, default_value) in enumerate(stat_items):
            row, col = divmod(i, 3)

            label = QLabel(label_text)
            label.setStyleSheet(
                "font-size: 11px; color: #8b949e; font-weight: 600; "
                "text-transform: uppercase; background: transparent;"
            )
            stats_grid.addWidget(label, row * 2, col)

            value_label = QLabel(default_value)
            value_label.setStyleSheet(
                "font-size: 20px; font-weight: 700; color: #e6edf3; background: transparent;"
            )
            stats_grid.addWidget(value_label, row * 2 + 1, col)
            self._stat_labels[key] = value_label

        results_layout.addWidget(stats_card)

        # ASIN results section
        asin_header = QHBoxLayout()
        asin_title = QLabel("ASIN Sonuçları")
        asin_title.setObjectName("sectionTitle")
        asin_header.addWidget(asin_title)

        asin_header.addStretch()

        self._asin_count_label = QLabel("0 ASIN")
        self._asin_count_label.setStyleSheet("color: #8b949e; font-size: 12px;")
        asin_header.addWidget(self._asin_count_label)

        results_layout.addLayout(asin_header)

        # ASIN text display
        self._asin_display = QPlainTextEdit()
        self._asin_display.setReadOnly(True)
        self._asin_display.setPlaceholderText(
            "Filtreye uyan ASIN kodları burada görüntülenecek..."
        )
        self._asin_display.setStyleSheet(
            """
            QPlainTextEdit {
                font-family: "Cascadia Code", "Consolas", monospace;
                font-size: 13px;
                line-height: 1.6;
                letter-spacing: 0.5px;
            }
            """
        )
        results_layout.addWidget(self._asin_display, 1)

        # Action buttons
        action_layout = QHBoxLayout()
        action_layout.setSpacing(8)

        self._cancel_btn = QPushButton("İptal Et")
        self._cancel_btn.setObjectName("dangerButton")
        self._cancel_btn.clicked.connect(self._on_cancel_clicked)
        action_layout.addWidget(self._cancel_btn)

        self._delete_btn = QPushButton("Sil")
        self._delete_btn.clicked.connect(self._on_delete_clicked)
        action_layout.addWidget(self._delete_btn)

        action_layout.addStretch()

        self._export_txt_btn = QPushButton("TXT Olarak Kaydet")
        self._export_txt_btn.setObjectName("successButton")
        self._export_txt_btn.clicked.connect(lambda: self._on_export("txt"))
        action_layout.addWidget(self._export_txt_btn)

        self._export_csv_btn = QPushButton("CSV Olarak Kaydet")
        self._export_csv_btn.setObjectName("successButton")
        self._export_csv_btn.clicked.connect(lambda: self._on_export("csv"))
        action_layout.addWidget(self._export_csv_btn)

        results_layout.addLayout(action_layout)

        self._stack.addWidget(results_page)

        # =====================================================================
        # Page 2: Empty State
        # =====================================================================
        empty_page = QWidget()
        empty_layout = QVBoxLayout(empty_page)
        empty_layout.addStretch()

        empty_icon = QLabel("📋")
        empty_icon.setAlignment(Qt.AlignCenter)
        empty_icon.setStyleSheet("font-size: 48px; background: transparent;")
        empty_layout.addWidget(empty_icon)

        empty_text = QLabel("Görev seçin veya yeni bir tarama başlatın")
        empty_text.setAlignment(Qt.AlignCenter)
        empty_text.setStyleSheet(
            "font-size: 15px; color: #8b949e; background: transparent;"
        )
        empty_layout.addWidget(empty_text)

        empty_layout.addStretch()

        self._stack.addWidget(empty_page)

        # Start with empty state
        self._stack.setCurrentIndex(2)
        layout.addWidget(self._stack)

    def show_setup_mode(self):
        """Switch to setup mode for creating a new task."""
        self._current_task = None
        self._url_input.reset()
        self._url_input.set_enabled(True)
        self._filter_panel.set_enabled(True)
        self._start_btn.setEnabled(True)
        self._start_btn.setText("  ▶  Taramayı Başlat")
        self._stack.setCurrentIndex(0)

    def show_task_details(self, task: TaskModel):
        """Switch to results mode showing a specific task."""
        self._current_task = task
        self._asin_display.clear()
        if task.asins:
            self._asin_display.setPlainText("\n".join(task.asins))
            self._asin_count_label.setText(f"{len(task.asins)} ASIN")
        else:
            self._asin_count_label.setText("0 ASIN")
        self._update_task_display(task)
        self._stack.setCurrentIndex(1)

    def show_empty_state(self):
        """Show the empty state placeholder."""
        self._current_task = None
        self._stack.setCurrentIndex(2)

    def update_task(self, task: TaskModel):
        """Update the displayed task information."""
        if self._current_task and self._current_task.id == task.id:
            self._update_task_display(task)

    def add_asins(self, task_id: str, asins: list[str]):
        """Add newly found ASINs to the display."""
        if self._current_task and self._current_task.id == task_id:
            for a in asins:
                if a not in self._current_task.asins:
                    self._current_task.asins.append(a)

            current_text = self._asin_display.toPlainText().strip()
            new_text = "\n".join(asins)
            if current_text:
                self._asin_display.setPlainText(f"{current_text}\n{new_text}")
            else:
                self._asin_display.setPlainText(new_text)

            # Update count
            lines = [x for x in self._asin_display.toPlainText().strip().split("\n") if x]
            self._asin_count_label.setText(f"{len(lines)} ASIN")

    def _update_task_display(self, task: TaskModel):
        """Update all display elements with task data."""
        self._task_name_label.setText(task.display_name)

        # Status badge
        status_styles = {
            TaskStatusEnum.WAITING: (
                "Bekliyor", f"color: {ThemeColors.WARNING}; background-color: rgba(210, 153, 34, 0.15);"
            ),
            TaskStatusEnum.RUNNING: (
                "Çalışıyor", f"color: {ThemeColors.ACCENT}; background-color: rgba(0, 120, 212, 0.15);"
            ),
            TaskStatusEnum.COMPLETED: (
                "Tamamlandı", f"color: {ThemeColors.SUCCESS}; background-color: rgba(46, 160, 67, 0.15);"
            ),
            TaskStatusEnum.FAILED: (
                "Başarısız", f"color: {ThemeColors.ERROR}; background-color: rgba(248, 81, 73, 0.15);"
            ),
            TaskStatusEnum.CANCELLED: (
                "İptal Edildi", f"color: {ThemeColors.TEXT_MUTED}; background-color: rgba(110, 118, 129, 0.15);"
            ),
        }
        text, style = status_styles.get(
            task.status, ("Bilinmeyen", "color: #8b949e;")
        )
        self._task_status_label.setText(f"  {text}  ")
        self._task_status_label.setStyleSheet(
            f"{style} font-size: 12px; font-weight: 600; padding: 4px 12px; "
            "border-radius: 12px;"
        )

        # Stats
        self._stat_labels["pages"].setText(
            f"{task.processed_pages} / {task.total_pages}"
        )
        self._stat_labels["products"].setText(str(task.matched_asins))
        self._stat_labels["asins"].setText(str(task.matched_asins))
        self._stat_labels["urls"].setText(str(task.url_count))

        # Elapsed time
        elapsed = task.elapsed_seconds
        self._stat_labels["elapsed"].setText(
            str(timedelta(seconds=int(elapsed)))
        )

        # ETA
        eta = task.estimated_remaining_seconds
        if eta is not None:
            self._stat_labels["eta"].setText(
                str(timedelta(seconds=int(eta)))
            )
        else:
            self._stat_labels["eta"].setText("—")

        # Button states
        is_running = task.status == TaskStatusEnum.RUNNING
        is_done = task.status in (
            TaskStatusEnum.COMPLETED,
            TaskStatusEnum.FAILED,
            TaskStatusEnum.CANCELLED,
        )
        self._cancel_btn.setVisible(is_running)
        self._delete_btn.setVisible(is_done or task.status == TaskStatusEnum.WAITING)
        self._export_txt_btn.setVisible(is_done and task.matched_asins > 0)
        self._export_csv_btn.setVisible(is_done and task.matched_asins > 0)

        # Load ASINs for current task
        if task.asins:
            self._asin_display.setPlainText("\n".join(task.asins))
            self._asin_count_label.setText(f"{len(task.asins)} ASIN")

    def _on_start_clicked(self):
        """Handle start button click."""
        # Validate URLs
        urls_valid, urls = self._url_input.validate()
        if not urls_valid:
            return

        # Validate filters
        filters_valid, _ = self._filter_panel.validate()
        if not filters_valid:
            return

        # Get filter model
        filters = self._filter_panel.get_filters()

        # Disable inputs
        self._url_input.set_enabled(False)
        self._filter_panel.set_enabled(False)
        self._start_btn.setEnabled(False)
        self._start_btn.setText("  ⏳  Başlatılıyor...")

        # Emit signal
        self.start_task_requested.emit(urls, filters)

    def _on_cancel_clicked(self):
        """Handle cancel button click."""
        if self._current_task:
            self.cancel_task_requested.emit(self._current_task.id)

    def _on_delete_clicked(self):
        """Handle delete button click."""
        if self._current_task:
            self.delete_task_requested.emit(self._current_task.id)

    def _on_export(self, format_type: str):
        """Handle export button clicks."""
        if not self._current_task:
            return

        asins_text = self._asin_display.toPlainText().strip()
        if not asins_text:
            return

        asins = [a.strip() for a in asins_text.split("\n") if a.strip()]

        # File dialog
        if format_type == "txt":
            file_filter = "Text Files (*.txt)"
            default_name = f"asins_{self._current_task.id[:8]}.txt"
        else:
            file_filter = "CSV Files (*.csv)"
            default_name = f"asins_{self._current_task.id[:8]}.csv"

        filepath, _ = QFileDialog.getSaveFileName(
            self, "ASIN Listesini Kaydet", default_name, file_filter
        )

        if filepath:
            path = Path(filepath)
            if format_type == "txt":
                self._export_manager.export_txt(asins, filepath=path)
            else:
                self._export_manager.export_csv(asins, filepath=path)
