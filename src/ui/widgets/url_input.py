"""
URL input widget.

Provides a multi-line text area for entering Amazon search URLs
with validation feedback and URL count display.
"""

from __future__ import annotations

from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QFrame,
)

from src.utils.constants import MAX_URLS_PER_TASK
from src.utils.validators import AmazonUrlValidator


class UrlInputWidget(QWidget):
    """
    Widget for entering Amazon search URLs.

    Features:
    - Multi-line text area (one URL per line)
    - Real-time URL count and validation feedback
    - Clear and paste buttons
    - Validation on demand
    """

    # Signal emitted with validated URLs when user confirms
    urls_submitted = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Header
        header_layout = QHBoxLayout()
        title_label = QLabel("Amazon Arama URL'leri")
        title_label.setObjectName("sectionTitle")
        header_layout.addWidget(title_label)

        header_layout.addStretch()

        self._url_count_label = QLabel("0 URL")
        self._url_count_label.setObjectName("subtitleLabel")
        header_layout.addWidget(self._url_count_label)

        layout.addLayout(header_layout)

        # Subtitle
        subtitle = QLabel(
            f"Her satıra bir Amazon.com arama URL'si girin (maks. {MAX_URLS_PER_TASK})"
        )
        subtitle.setObjectName("subtitleLabel")
        layout.addWidget(subtitle)

        # Text area
        self._text_edit = QPlainTextEdit()
        self._text_edit.setPlaceholderText(
            "https://www.amazon.com/s?k=gaming+mouse\n"
            "https://www.amazon.com/s?k=usb+hub\n"
            "..."
        )
        self._text_edit.setMinimumHeight(100)
        self._text_edit.setMaximumHeight(160)
        layout.addWidget(self._text_edit)

        # Validation message
        self._validation_label = QLabel("")
        self._validation_label.setWordWrap(True)
        self._validation_label.setStyleSheet("color: #f85149; font-size: 12px;")
        self._validation_label.hide()
        layout.addWidget(self._validation_label)

        # Button row
        button_layout = QHBoxLayout()
        button_layout.setSpacing(8)

        self._clear_btn = QPushButton("Temizle")
        self._clear_btn.setFixedWidth(80)
        button_layout.addWidget(self._clear_btn)

        button_layout.addStretch()

        layout.addLayout(button_layout)

    def _connect_signals(self):
        self._text_edit.textChanged.connect(self._on_text_changed)
        self._clear_btn.clicked.connect(self._clear)

    def _on_text_changed(self):
        """Update URL count when text changes."""
        urls = self.get_urls()
        count = len(urls)
        self._url_count_label.setText(f"{count} URL")

        # Change color based on count
        if count > MAX_URLS_PER_TASK:
            self._url_count_label.setStyleSheet("color: #f85149;")
        elif count > 0:
            self._url_count_label.setStyleSheet("color: #2ea043;")
        else:
            self._url_count_label.setStyleSheet("color: #8b949e;")

        # Clear validation errors on edit
        self._validation_label.hide()

    def _clear(self):
        """Clear the text area."""
        self._text_edit.clear()
        self._validation_label.hide()

    def get_urls(self) -> list[str]:
        """Get the list of non-empty URLs from the text area."""
        text = self._text_edit.toPlainText()
        lines = text.strip().split("\n")
        return [line.strip() for line in lines if line.strip()]

    def validate(self) -> tuple[bool, list[str]]:
        """
        Validate all entered URLs.

        Returns:
            A tuple of (is_valid, error_messages).
        """
        urls = self.get_urls()
        is_valid, errors = AmazonUrlValidator.validate_urls(urls)

        if not is_valid:
            self._validation_label.setText("\n".join(errors))
            self._validation_label.show()
        else:
            self._validation_label.hide()

        return is_valid, urls

    def set_enabled(self, enabled: bool):
        """Enable or disable the input widget."""
        self._text_edit.setEnabled(enabled)
        self._clear_btn.setEnabled(enabled)

    def reset(self):
        """Reset and clear the URL text area."""
        self._clear()
