"""
Log panel widget.

Displays real-time application log entries in the right sidebar
with color-coded log levels and auto-scrolling.
"""

from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QTextCharFormat, QColor, QFont
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QTextEdit,
    QPushButton,
    QFrame,
)

from src.utils.constants import ThemeColors, UIDimensions
from src.utils.logger import UILogHandler


class LogPanel(QWidget):
    """
    Right sidebar panel for displaying real-time log entries.

    Features:
    - Color-coded log levels (INFO, WARNING, ERROR, DEBUG)
    - Auto-scrolling to latest entries
    - Clear button
    - Monospace font for readability
    - Max line limit to prevent memory issues
    """

    MAX_LOG_LINES = 5000

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(UIDimensions.LOG_PANEL_WIDTH)
        self._setup_ui()
        self._register_log_handler()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        header = QFrame()
        header.setStyleSheet(
            "background-color: #161b22; border-bottom: 1px solid #30363d;"
        )
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(16, 12, 16, 12)

        title = QLabel("Log")
        title.setStyleSheet(
            "font-size: 14px; font-weight: 700; color: #e6edf3; background: transparent;"
        )
        header_layout.addWidget(title)

        header_layout.addStretch()

        clear_btn = QPushButton("Temizle")
        clear_btn.setFixedHeight(28)
        clear_btn.setStyleSheet(
            """
            QPushButton {
                background: transparent;
                border: 1px solid #30363d;
                border-radius: 4px;
                color: #8b949e;
                font-size: 11px;
                padding: 2px 12px;
            }
            QPushButton:hover {
                background-color: #21262d;
                color: #e6edf3;
            }
            """
        )
        clear_btn.clicked.connect(self._clear)
        header_layout.addWidget(clear_btn)

        layout.addWidget(header)

        # Log text area
        self._log_text = QTextEdit()
        self._log_text.setReadOnly(True)
        self._log_text.setStyleSheet(
            """
            QTextEdit {
                background-color: #0d1117;
                border: none;
                border-radius: 0;
                padding: 8px;
                font-family: "Cascadia Code", "Consolas", monospace;
                font-size: 11px;
                line-height: 1.5;
            }
            """
        )
        layout.addWidget(self._log_text, 1)

    def _register_log_handler(self):
        """Register the UI log handler callback."""
        UILogHandler.set_callback(self._on_log_message)

    @Slot(str, str, str)
    def _on_log_message(self, timestamp: str, level: str, message: str):
        """
        Handle incoming log messages.

        Args:
            timestamp: Formatted time string (HH:MM:SS).
            level: Log level (INFO, WARNING, ERROR, DEBUG).
            message: The log message text.
        """
        # Color mapping for log levels
        color_map = {
            "DEBUG": "#6e7681",
            "INFO": "#8b949e",
            "WARNING": "#d29922",
            "ERROR": "#f85149",
            "CRITICAL": "#ff6e6a",
        }
        color = color_map.get(level, "#8b949e")

        # Format the log entry with HTML
        html = (
            f'<span style="color: #6e7681;">[{timestamp}]</span> '
            f'<span style="color: {color}; font-weight: 600;">[{level}]</span> '
            f'<span style="color: #e6edf3;">{message}</span>'
        )

        self._log_text.append(html)

        # Auto-scroll to bottom
        scrollbar = self._log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

        # Limit log lines to prevent memory issues
        document = self._log_text.document()
        if document.blockCount() > self.MAX_LOG_LINES:
            cursor = self._log_text.textCursor()
            cursor.movePosition(cursor.Start)
            cursor.movePosition(cursor.Down, cursor.KeepAnchor, 500)
            cursor.removeSelectedText()

    def _clear(self):
        """Clear all log entries."""
        self._log_text.clear()

    def append_log(self, level: str, message: str):
        """
        Manually append a log entry.

        Args:
            level: Log level string.
            message: The log message.
        """
        timestamp = datetime.now().strftime("%H:%M:%S")
        self._on_log_message(timestamp, level, message)

    def cleanup(self):
        """Clean up the log handler on shutdown."""
        UILogHandler.clear_callback()
