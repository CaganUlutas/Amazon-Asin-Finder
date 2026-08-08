"""
UI Theme configuration.

Provides the dark theme color palette, font settings, and a method
to load and apply the QSS stylesheet to the application.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QFont, QColor, QPalette
from PySide6.QtWidgets import QApplication

from src.utils.constants import ThemeColors, UIDimensions


class Theme:
    """
    Application theme manager.

    Loads the dark theme QSS stylesheet and configures the Qt
    application palette for a consistent look across all widgets.
    """

    # Font families
    FONT_FAMILY = "Segoe UI, Inter, -apple-system, sans-serif"
    MONO_FONT_FAMILY = "Cascadia Code, Consolas, monospace"

    # Font sizes
    FONT_SIZE_XS = 11
    FONT_SIZE_SM = 12
    FONT_SIZE_MD = 13
    FONT_SIZE_LG = 15
    FONT_SIZE_XL = 18
    FONT_SIZE_XXL = 24

    @classmethod
    def apply(cls, app: QApplication) -> None:
        """
        Apply the dark theme to the entire application.

        This sets:
        - The Fusion style for cross-platform consistency
        - A dark QPalette
        - The QSS stylesheet from dark_theme.qss
        - The default font

        Args:
            app: The QApplication instance.
        """
        # Set Fusion style for consistent cross-platform look
        app.setStyle("Fusion")

        # Set default font
        font = QFont("Segoe UI", cls.FONT_SIZE_MD)
        app.setFont(font)

        # Apply dark palette
        cls._apply_palette(app)

        # Load and apply QSS stylesheet
        qss = cls._load_qss()
        if qss:
            app.setStyleSheet(qss)

    @classmethod
    def _apply_palette(cls, app: QApplication) -> None:
        """Configure a dark QPalette for the application."""
        palette = QPalette()

        # Window backgrounds
        palette.setColor(QPalette.Window, QColor(ThemeColors.BG_PRIMARY))
        palette.setColor(QPalette.WindowText, QColor(ThemeColors.TEXT_PRIMARY))
        palette.setColor(QPalette.Base, QColor(ThemeColors.BG_SECONDARY))
        palette.setColor(QPalette.AlternateBase, QColor(ThemeColors.BG_TERTIARY))

        # Text
        palette.setColor(QPalette.Text, QColor(ThemeColors.TEXT_PRIMARY))
        palette.setColor(QPalette.BrightText, QColor("#ffffff"))
        palette.setColor(QPalette.PlaceholderText, QColor(ThemeColors.TEXT_MUTED))

        # Buttons
        palette.setColor(QPalette.Button, QColor(ThemeColors.BG_TERTIARY))
        palette.setColor(QPalette.ButtonText, QColor(ThemeColors.TEXT_PRIMARY))

        # Highlights
        palette.setColor(QPalette.Highlight, QColor(ThemeColors.ACCENT))
        palette.setColor(QPalette.HighlightedText, QColor("#ffffff"))

        # Tooltips
        palette.setColor(QPalette.ToolTipBase, QColor(ThemeColors.BG_TERTIARY))
        palette.setColor(QPalette.ToolTipText, QColor(ThemeColors.TEXT_PRIMARY))

        # Links
        palette.setColor(QPalette.Link, QColor(ThemeColors.ACCENT))
        palette.setColor(QPalette.LinkVisited, QColor(ThemeColors.ACCENT_HOVER))

        # Disabled
        palette.setColor(
            QPalette.Disabled, QPalette.WindowText, QColor(ThemeColors.TEXT_MUTED)
        )
        palette.setColor(
            QPalette.Disabled, QPalette.Text, QColor(ThemeColors.TEXT_MUTED)
        )
        palette.setColor(
            QPalette.Disabled, QPalette.ButtonText, QColor(ThemeColors.TEXT_MUTED)
        )

        app.setPalette(palette)

    @classmethod
    def _load_qss(cls) -> str:
        """Load the QSS stylesheet from the styles directory."""
        qss_path = Path(__file__).parent / "dark_theme.qss"
        if qss_path.exists():
            return qss_path.read_text(encoding="utf-8")
        return ""
