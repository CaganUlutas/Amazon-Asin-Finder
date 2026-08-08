"""
Export manager for ASIN results.

Handles exporting filtered ASIN lists to TXT and CSV file formats.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional

from src.utils.constants import EXPORT_DIR, CSV_HEADER, TXT_LINE_SEPARATOR
from src.utils.logger import get_logger

logger = get_logger(__name__)


class ExportManager:
    """
    Exports ASIN lists to files in TXT or CSV format.

    TXT format: One ASIN per line, no header.
    CSV format: Single column with "ASIN" header.

    Usage:
        manager = ExportManager()
        path = manager.export_txt(asins, "my_results")
        path = manager.export_csv(asins, "my_results")
    """

    def __init__(self, export_dir: Optional[Path] = None):
        """
        Initialize the export manager.

        Args:
            export_dir: Directory to save exported files.
                       Defaults to the configured EXPORT_DIR.
        """
        self._export_dir = export_dir or EXPORT_DIR
        self._export_dir.mkdir(parents=True, exist_ok=True)

    def _generate_filename(self, prefix: str, extension: str) -> Path:
        """
        Generate a unique filename with timestamp.

        Args:
            prefix: The file name prefix.
            extension: The file extension (without dot).

        Returns:
            The full path to the export file.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{prefix}_{timestamp}.{extension}"
        return self._export_dir / filename

    def export_txt(
        self,
        asins: list[str],
        filename_prefix: str = "asins",
        filepath: Optional[Path] = None,
    ) -> Path:
        """
        Export ASINs to a plain text file (one per line).

        Args:
            asins: List of ASIN strings to export.
            filename_prefix: Prefix for the auto-generated filename.
            filepath: Optional explicit file path (overrides auto-generation).

        Returns:
            The path to the created file.
        """
        if filepath is None:
            filepath = self._generate_filename(filename_prefix, "txt")

        content = TXT_LINE_SEPARATOR.join(asins)

        filepath.parent.mkdir(parents=True, exist_ok=True)
        filepath.write_text(content, encoding="utf-8")

        logger.info(
            "TXT dışa aktarıldı: %s (%d ASIN)", filepath.name, len(asins)
        )
        return filepath

    def export_csv(
        self,
        asins: list[str],
        filename_prefix: str = "asins",
        filepath: Optional[Path] = None,
    ) -> Path:
        """
        Export ASINs to a CSV file with a single "ASIN" column.

        Args:
            asins: List of ASIN strings to export.
            filename_prefix: Prefix for the auto-generated filename.
            filepath: Optional explicit file path (overrides auto-generation).

        Returns:
            The path to the created file.
        """
        if filepath is None:
            filepath = self._generate_filename(filename_prefix, "csv")

        lines = [CSV_HEADER] + asins
        content = TXT_LINE_SEPARATOR.join(lines)

        filepath.parent.mkdir(parents=True, exist_ok=True)
        filepath.write_text(content, encoding="utf-8")

        logger.info(
            "CSV dışa aktarıldı: %s (%d ASIN)", filepath.name, len(asins)
        )
        return filepath
