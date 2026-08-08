"""
Amazon ASIN Finder — Application Entry Point

Initializes the Qt application with the qasync event loop,
sets up all dependencies, and launches the main window.
"""

import sys
import asyncio

from PySide6.QtWidgets import QApplication
from qasync import QEventLoop, asyncSlot

from src.ui.styles.theme import Theme
from src.ui.main_window import MainWindow
from src.database.db_manager import DatabaseManager
from src.crawler.browser_manager import BrowserManager
from src.core.task_manager import TaskManager
from src.utils.logger import setup_logging, get_logger
from src.utils.constants import APP_NAME


def main():
    """Application entry point."""
    # Initialize logging first
    setup_logging()
    logger = get_logger("main")
    logger.info("=" * 60)
    logger.info("%s başlatılıyor...", APP_NAME)
    logger.info("=" * 60)

    # Create Qt application
    app = QApplication(sys.argv)

    # Apply dark theme
    Theme.apply(app)

    # Set up qasync event loop
    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)

    # Create dependency instances
    db_manager = DatabaseManager()
    browser_manager = BrowserManager()
    task_manager = TaskManager(db_manager, browser_manager)

    # Create and show main window
    window = MainWindow(db_manager, browser_manager, task_manager)
    window.show()

    # Run initialization after event loop starts
    async def init():
        try:
            await db_manager.initialize()
            await window.initialize()
            logger.info("Uygulama başarıyla başlatıldı.")
        except Exception as e:
            logger.error("Başlatma hatası: %s", str(e))

    asyncio.ensure_future(init())

    # Run the event loop
    try:
        with loop:
            try:
                loop.run_forever()
            finally:
                # Cleanup
                pending = asyncio.all_tasks(loop)
                for task in pending:
                    task.cancel()
                logger.info("Uygulama kapatıldı.")
    except KeyboardInterrupt:
        logger.info("Kullanıcı tarafından kapatıldı.")


if __name__ == "__main__":
    main()
