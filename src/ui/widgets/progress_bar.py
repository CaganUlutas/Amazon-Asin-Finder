"""
Bottom progress bar widget.

Displays overall progress information including progress bar,
statistics, and elapsed/remaining time.
"""

from __future__ import annotations

from datetime import timedelta

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QLabel,
    QProgressBar,
    QFrame,
)

from src.utils.constants import ThemeColors


class BottomProgressBar(QWidget):
    """
    Bottom status bar with progress bar and statistics.

    Shows:
    - Overall progress bar
    - Pages processed
    - Products found
    - ASINs matched
    - Elapsed time
    - Estimated remaining time
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("bottomBar")
        self.setFixedHeight(56)
        self._setup_ui()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 0, 16, 0)
        main_layout.setSpacing(4)

        # Progress bar
        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        self._progress_bar.setFixedHeight(6)
        self._progress_bar.setTextVisible(False)
        main_layout.addWidget(self._progress_bar)

        # Stats row
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(24)

        # Stat items
        self._status_label = self._create_stat("Hazır")
        stats_layout.addWidget(self._status_label)

        separator = QLabel("│")
        separator.setStyleSheet("color: #30363d; background: transparent;")
        stats_layout.addWidget(separator)

        self._pages_label = self._create_stat("Sayfa: 0/0")
        stats_layout.addWidget(self._pages_label)

        self._products_label = self._create_stat("Eşsiz Ürün: 0")
        stats_layout.addWidget(self._products_label)

        self._asins_label = self._create_stat("ASIN: 0")
        stats_layout.addWidget(self._asins_label)

        stats_layout.addStretch()

        self._elapsed_label = self._create_stat("⏱ 00:00:00")
        stats_layout.addWidget(self._elapsed_label)

        self._eta_label = self._create_stat("ETA: —")
        stats_layout.addWidget(self._eta_label)

        main_layout.addLayout(stats_layout)

    def _create_stat(self, text: str) -> QLabel:
        """Create a styled stat label."""
        label = QLabel(text)
        label.setStyleSheet(
            "font-size: 12px; color: #8b949e; font-weight: 500; background: transparent;"
        )
        return label

    def update_progress(
        self,
        processed_pages: int = 0,
        total_pages: int = 0,
        total_products: int = 0,
        matched_asins: int = 0,
        elapsed_seconds: float = 0,
        eta_seconds: float | None = None,
        status_text: str = "",
    ):
        """
        Update all progress information.

        Args:
            processed_pages: Number of pages processed.
            total_pages: Total pages to process.
            total_products: Total products found.
            matched_asins: Number of ASINs matching filters.
            elapsed_seconds: Time elapsed in seconds.
            eta_seconds: Estimated remaining time in seconds.
            status_text: Status text to display.
        """
        # Progress bar
        if total_pages > 0:
            percent = min(int((processed_pages / total_pages) * 100), 100)
            self._progress_bar.setValue(percent)
        else:
            self._progress_bar.setValue(0)

        # Status
        if status_text:
            self._status_label.setText(status_text)

        # Stats
        self._pages_label.setText(f"Sayfa: {processed_pages}/{total_pages}")
        self._products_label.setText(f"Eşsiz Ürün: {matched_asins}")
        self._asins_label.setText(f"ASIN: {matched_asins}")

        # Elapsed time
        elapsed = str(timedelta(seconds=int(elapsed_seconds)))
        self._elapsed_label.setText(f"⏱ {elapsed}")

        # ETA
        if eta_seconds is not None and eta_seconds > 0:
            eta = str(timedelta(seconds=int(eta_seconds)))
            self._eta_label.setText(f"ETA: {eta}")
        else:
            self._eta_label.setText("ETA: —")

    def reset(self):
        """Reset all progress information to defaults."""
        self._progress_bar.setValue(0)
        self._status_label.setText("Hazır")
        self._pages_label.setText("Sayfa: 0/0")
        self._products_label.setText("Eşsiz Ürün: 0")
        self._asins_label.setText("ASIN: 0")
        self._elapsed_label.setText("⏱ 00:00:00")
        self._eta_label.setText("ETA: —")

    def set_running(self):
        """Set status to running."""
        self._status_label.setText("⚡ Taranıyor...")
        self._status_label.setStyleSheet(
            f"font-size: 12px; color: {ThemeColors.ACCENT}; "
            "font-weight: 600; background: transparent;"
        )

    def set_completed(self):
        """Set status to completed."""
        self._status_label.setText("✓ Tamamlandı")
        self._status_label.setStyleSheet(
            f"font-size: 12px; color: {ThemeColors.SUCCESS}; "
            "font-weight: 600; background: transparent;"
        )

    def set_failed(self):
        """Set status to failed."""
        self._status_label.setText("✗ Başarısız")
        self._status_label.setStyleSheet(
            f"font-size: 12px; color: {ThemeColors.ERROR}; "
            "font-weight: 600; background: transparent;"
        )

    def set_idle(self):
        """Reset to idle state."""
        self._status_label.setText("Hazır")
        self._status_label.setStyleSheet(
            "font-size: 12px; color: #8b949e; font-weight: 500; background: transparent;"
        )
