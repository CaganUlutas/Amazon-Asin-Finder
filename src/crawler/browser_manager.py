"""
Playwright browser lifecycle manager.

Implements the Singleton pattern for browser instance management.
Handles browser launch, context creation, and graceful shutdown.
Blocks unnecessary resources (images, fonts, etc.) to minimize
bandwidth and memory usage.
"""

from __future__ import annotations

import asyncio
from typing import Optional

from playwright.async_api import (
    async_playwright,
    Browser,
    BrowserContext,
    Page,
    Playwright,
)

from src.utils.constants import (
    BROWSER_VIEWPORT_WIDTH,
    BROWSER_VIEWPORT_HEIGHT,
    MAX_CONCURRENT_PAGES,
    PAGE_TIMEOUT_MS,
)
from src.utils.logger import get_logger

import os
import sys

logger = get_logger(__name__)


def _setup_playwright_browsers_path():
    """Ensure Playwright finds installed Chromium binaries in PyInstaller EXE mode."""
    if "PLAYWRIGHT_BROWSERS_PATH" not in os.environ:
        if getattr(sys, "frozen", False):
            base_dir = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
            bundled_browsers = os.path.join(base_dir, "ms-playwright")
            local_browsers = os.path.join(os.path.dirname(sys.executable), "ms-playwright")
            user_browsers = os.path.expanduser("~\\AppData\\Local\\ms-playwright")

            if os.path.exists(bundled_browsers):
                os.environ["PLAYWRIGHT_BROWSERS_PATH"] = bundled_browsers
            elif os.path.exists(local_browsers):
                os.environ["PLAYWRIGHT_BROWSERS_PATH"] = local_browsers
            else:
                os.environ["PLAYWRIGHT_BROWSERS_PATH"] = user_browsers


_setup_playwright_browsers_path()


class BrowserManager:
    """
    Manages a single Playwright Chromium browser instance.

    Key responsibilities:
    - Launch/close the browser (singleton lifecycle)
    - Create isolated BrowserContexts for each task
    - Block unnecessary resources for performance
    - Provide a semaphore to limit concurrent pages

    Usage:
        manager = BrowserManager()
        await manager.launch()

        context = await manager.create_context()
        page = await context.new_page()
        # ... use the page ...
        await page.close()
        await context.close()

        await manager.shutdown()
    """

    def __init__(self):
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._semaphore = asyncio.Semaphore(MAX_CONCURRENT_PAGES)
        self._launched = False

    @property
    def is_launched(self) -> bool:
        """Check if the browser is currently running."""
        return self._launched and self._browser is not None

    @property
    def semaphore(self) -> asyncio.Semaphore:
        """Get the concurrency-limiting semaphore."""
        return self._semaphore

    async def launch(self) -> None:
        """
        Launch the Chromium browser in headless mode.

        Idempotent — safe to call multiple times.
        """
        if self._launched:
            logger.debug("Browser zaten çalışıyor.")
            return

        logger.info("Playwright tarayıcı başlatılıyor...")

        self._playwright = await async_playwright().start()

        self._browser = await self._playwright.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--no-sandbox",
                "--disable-gpu",
                "--disable-extensions",
                "--disable-infobars",
                "--disable-notifications",
                "--disable-popup-blocking",
            ],
        )

        self._launched = True
        logger.info("Tarayıcı başarıyla başlatıldı (headless mode).")

    async def create_context(self) -> BrowserContext:
        """
        Create a new isolated browser context.

        Each context has:
        - Its own cookies, localStorage, and cache
        - A realistic viewport and user agent
        - Resource blocking for images, fonts, and media

        Returns:
            A new BrowserContext instance.

        Raises:
            RuntimeError: If the browser hasn't been launched yet.
        """
        if not self.is_launched:
            raise RuntimeError(
                "Browser başlatılmamış. Önce launch() çağrılmalı."
            )

        context = await self._browser.new_context(
            viewport={
                "width": BROWSER_VIEWPORT_WIDTH,
                "height": BROWSER_VIEWPORT_HEIGHT,
            },
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            locale="en-US",
            timezone_id="America/New_York",
            java_script_enabled=True,
        )

        # Block unnecessary resource types to save bandwidth and memory
        await context.route(
            "**/*",
            lambda route: (
                route.abort()
                if route.request.resource_type
                in ("image", "stylesheet", "font", "media", "other")
                else route.continue_()
            ),
        )

        # Set default timeout for all pages in this context
        context.set_default_timeout(PAGE_TIMEOUT_MS)
        context.set_default_navigation_timeout(PAGE_TIMEOUT_MS)

        logger.debug("Yeni browser context oluşturuldu.")
        return context

    async def new_page(self, context: BrowserContext) -> Page:
        """
        Create a new page within a context, respecting the concurrency limit.

        This method acquires the semaphore before creating the page.
        The caller MUST release the semaphore when done with the page
        (typically by using `acquire_page` context manager instead).

        Args:
            context: The browser context to create the page in.

        Returns:
            A new Page instance.
        """
        await self._semaphore.acquire()
        try:
            page = await context.new_page()
            logger.debug("Yeni sayfa oluşturuldu.")
            return page
        except Exception:
            self._semaphore.release()
            raise

    def release_page(self) -> None:
        """Release the semaphore after a page is closed."""
        self._semaphore.release()

    async def shutdown(self) -> None:
        """
        Gracefully shut down the browser and Playwright.

        Closes all contexts and pages, then stops Playwright.
        """
        if self._browser is not None:
            try:
                await self._browser.close()
                logger.info("Tarayıcı kapatıldı.")
            except Exception as e:
                logger.warning("Tarayıcı kapatılırken hata: %s", e)
            self._browser = None

        if self._playwright is not None:
            try:
                await self._playwright.stop()
                logger.info("Playwright durduruldu.")
            except Exception as e:
                logger.warning("Playwright durdurulurken hata: %s", e)
            self._playwright = None

        self._launched = False
        logger.info("Browser manager kapatıldı.")

    async def restart(self) -> None:
        """Restart the browser (useful for memory leak prevention)."""
        logger.info("Tarayıcı yeniden başlatılıyor...")
        await self.shutdown()
        await self.launch()
