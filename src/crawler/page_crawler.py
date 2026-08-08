"""
Page crawler for Amazon search results.

Handles page navigation, pagination traversal, and coordinates
product extraction with the parser module. This is the main
crawling engine that processes individual search URLs.
"""

from __future__ import annotations

import asyncio
import random
from typing import Optional, AsyncGenerator

from playwright.async_api import BrowserContext, Page, TimeoutError as PlaywrightTimeout

from src.core.models import ProductData, CrawlProgress, TaskStatusEnum
from src.crawler.browser_manager import BrowserManager
from src.crawler.product_parser import ProductParser
from src.crawler.retry_handler import RetryHandler, RetryExhaustedError, ErrorType
from src.utils.constants import (
    REQUEST_DELAY_MIN,
    REQUEST_DELAY_MAX,
    MAX_PAGES_PER_URL,
    AmazonSelectors,
)
from src.utils.logger import get_logger

logger = get_logger(__name__)


class PageCrawler:
    """
    Crawls Amazon search result pages for a given URL.

    Responsibilities:
    - Navigate to search URLs
    - Handle pagination (next page traversal)
    - Extract products from each page using ProductParser
    - Respect rate limits with randomized delays
    - Detect and handle CAPTCHA/challenge pages
    - Report progress via async generator

    Usage:
        crawler = PageCrawler(browser_manager)
        async for progress in crawler.crawl_url(context, url, task_id):
            print(f"Page {progress.current_page}: {progress.products_found} products")
    """

    def __init__(self, browser_manager: BrowserManager):
        self._browser_manager = browser_manager
        self._retry_handler = RetryHandler()
        self._cancelled = False

    def cancel(self) -> None:
        """Signal the crawler to stop processing."""
        self._cancelled = True
        logger.info("Tarama iptal sinyali alındı.")

    def reset(self) -> None:
        """Reset the cancellation state."""
        self._cancelled = False

    async def crawl_url(
        self,
        context: BrowserContext,
        url: str,
        task_id: str,
        url_index: int = 0,
    ) -> AsyncGenerator[tuple[CrawlProgress, list[ProductData]], None]:
        """
        Crawl all pages of an Amazon search URL.

        Yields progress updates and product data for each page processed.

        Args:
            context: The browser context to use.
            url: The Amazon search URL to crawl.
            task_id: The parent task ID (for progress tracking).
            url_index: The index of this URL in the task's URL list.

        Yields:
            Tuples of (CrawlProgress, list[ProductData]) for each page.
        """
        self._cancelled = False
        page: Optional[Page] = None
        total_products = 0
        total_pages = 0

        try:
            # Acquire semaphore and create page
            await self._browser_manager.semaphore.acquire()

            try:
                page = await context.new_page()
            except Exception:
                self._browser_manager.release_page()
                raise

            logger.info("Tarama başlatılıyor: %s", url)

            # Navigate to the first page
            await self._navigate_to_page(page, url)

            # Check for CAPTCHA
            if await ProductParser.check_captcha(page):
                logger.warning("CAPTCHA tespit edildi: %s", url)
                yield (
                    CrawlProgress(
                        task_id=task_id,
                        url_index=url_index,
                        status=TaskStatusEnum.FAILED,
                        message="CAPTCHA tespit edildi. Lütfen daha sonra tekrar deneyin.",
                    ),
                    [],
                )
                return

            # Check for "no results"
            if await ProductParser.check_no_results(page):
                logger.info("Sonuç bulunamadı: %s", url)
                yield (
                    CrawlProgress(
                        task_id=task_id,
                        url_index=url_index,
                        current_page=0,
                        total_pages=0,
                        status=TaskStatusEnum.COMPLETED,
                        message="Arama sonucu bulunamadı.",
                    ),
                    [],
                )
                return

            # Determine total pages
            total_pages = await ProductParser.get_total_pages(page)
            total_pages = min(total_pages, MAX_PAGES_PER_URL)
            logger.info("Toplam %d sayfa tespit edildi: %s", total_pages, url)

            # Process each page
            current_page = 1
            while current_page <= total_pages and not self._cancelled:
                logger.info(
                    "Sayfa %d/%d işleniyor: %s",
                    current_page,
                    total_pages,
                    url,
                )

                # Parse products from current page
                products = await ProductParser.parse_search_results(
                    page, url, current_page
                )
                total_products += len(products)

                # Yield progress update with products
                yield (
                    CrawlProgress(
                        task_id=task_id,
                        url_index=url_index,
                        current_page=current_page,
                        total_pages=total_pages,
                        products_found=total_products,
                        status=TaskStatusEnum.RUNNING,
                        message=f"Sayfa {current_page}/{total_pages}: "
                        f"{len(products)} ürün bulundu.",
                    ),
                    products,
                )

                # Try to go to next page
                if current_page < total_pages:
                    success = await self._go_to_next_page(page)
                    if not success:
                        logger.info(
                            "Sonraki sayfa bulunamadı, tarama tamamlandı."
                        )
                        break

                    # Randomized delay between pages
                    delay = random.uniform(REQUEST_DELAY_MIN, REQUEST_DELAY_MAX)
                    logger.debug("Sonraki sayfa öncesi %.1fs bekleniyor...", delay)
                    await asyncio.sleep(delay)

                current_page += 1

            # Final completion progress
            status = (
                TaskStatusEnum.CANCELLED
                if self._cancelled
                else TaskStatusEnum.COMPLETED
            )
            yield (
                CrawlProgress(
                    task_id=task_id,
                    url_index=url_index,
                    current_page=current_page - 1,
                    total_pages=total_pages,
                    products_found=total_products,
                    status=status,
                    message=(
                        "Tarama iptal edildi."
                        if self._cancelled
                        else f"Tarama tamamlandı. Toplam {total_products} ürün."
                    ),
                ),
                [],
            )

        except RetryExhaustedError as e:
            logger.error("Tüm yeniden deneme hakları tükendi: %s", e)
            yield (
                CrawlProgress(
                    task_id=task_id,
                    url_index=url_index,
                    current_page=0,
                    total_pages=total_pages,
                    products_found=total_products,
                    status=TaskStatusEnum.FAILED,
                    message=f"Hata: {e}",
                ),
                [],
            )

        except Exception as e:
            logger.error("Tarama hatası: %s — %s", url, str(e))
            yield (
                CrawlProgress(
                    task_id=task_id,
                    url_index=url_index,
                    current_page=0,
                    total_pages=total_pages,
                    products_found=total_products,
                    status=TaskStatusEnum.FAILED,
                    message=f"Beklenmeyen hata: {str(e)}",
                ),
                [],
            )

        finally:
            # Clean up the page
            if page:
                try:
                    await page.close()
                except Exception:
                    pass
            self._browser_manager.release_page()

    async def _navigate_to_page(self, page: Page, url: str) -> None:
        """
        Navigate to a URL with retry logic.

        Args:
            page: The Playwright page instance.
            url: The URL to navigate to.
        """

        async def _do_navigate():
            await page.goto(url, wait_until="domcontentloaded")
            # Wait for search results to appear
            await page.wait_for_selector(
                AmazonSelectors.SEARCH_RESULT,
                timeout=15000,
            )

        await self._retry_handler.execute_with_retry(
            _do_navigate,
            on_retry=lambda attempt, delay, err_type: logger.info(
                "Navigasyon retry #%d (%.1fs bekleme, tip: %s)",
                attempt,
                delay,
                err_type.value,
            ),
        )

    async def _go_to_next_page(self, page: Page) -> bool:
        """
        Navigate to the next search results page.

        Args:
            page: The current Playwright page instance.

        Returns:
            True if navigation was successful, False if no next page.
        """

        async def _do_next_page() -> bool:
            # Find the "Next" pagination button
            next_button = await page.query_selector(AmazonSelectors.NEXT_PAGE)

            if next_button is None:
                return False

            # Check if the button is disabled
            is_disabled = await next_button.get_attribute("aria-disabled")
            if is_disabled == "true":
                return False

            # Click the next button
            await next_button.click()

            # Wait for the new page content to load
            await page.wait_for_selector(
                AmazonSelectors.SEARCH_RESULT,
                timeout=15000,
            )

            # Small wait for dynamic content
            await page.wait_for_load_state("domcontentloaded")

            return True

        try:
            return await self._retry_handler.execute_with_retry(
                _do_next_page,
                on_retry=lambda attempt, delay, err_type: logger.info(
                    "Sayfa geçişi retry #%d (%.1fs bekleme)", attempt, delay
                ),
            )
        except RetryExhaustedError:
            logger.warning("Sonraki sayfaya geçilemedi, tarama sonlandırılıyor.")
            return False
