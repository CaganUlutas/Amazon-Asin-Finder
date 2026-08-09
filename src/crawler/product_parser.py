"""
Amazon product data parser.

Extracts product information from Amazon search result page DOM elements.
Uses Playwright's element handle API for reliable data extraction.
"""

from __future__ import annotations

import re
from typing import Optional

from playwright.async_api import Page, ElementHandle

from src.core.models import ProductData
from src.utils.constants import AmazonSelectors
from src.utils.logger import get_logger

logger = get_logger(__name__)


class ProductParser:
    """
    Parses product data from Amazon search result page elements.

    Handles the various HTML structures Amazon uses for displaying
    product information including price, rating, review count, and badges.
    """

    @classmethod
    async def parse_search_results(
        cls, page: Page, source_url: str, page_number: int
    ) -> list[ProductData]:
        """
        Parse all product listings from a search results page.

        Args:
            page: The Playwright page with loaded search results.
            source_url: The original search URL (for tracking).
            page_number: The current page number.

        Returns:
            A list of ProductData objects extracted from the page.
        """
        products = []

        # Get all search result containers
        result_elements = await page.query_selector_all(
            AmazonSelectors.SEARCH_RESULT
        )

        logger.debug(
            "Sayfa %d: %d ürün elementi bulundu.", page_number, len(result_elements)
        )

        for element in result_elements:
            try:
                product = await cls._parse_single_product(
                    element, source_url, page_number
                )
                if product and product.asin:
                    products.append(product)
            except Exception as e:
                logger.warning(
                    "Ürün parse edilirken hata (sayfa %d): %s",
                    page_number,
                    str(e),
                )
                continue

        logger.info(
            "Sayfa %d: %d ürün başarıyla parse edildi.",
            page_number,
            len(products),
        )
        return products

    @classmethod
    async def _parse_single_product(
        cls,
        element: ElementHandle,
        source_url: str,
        page_number: int,
    ) -> Optional[ProductData]:
        """
        Parse a single product listing element.

        Args:
            element: The DOM element containing the product listing.
            source_url: The original search URL.
            page_number: The current page number.

        Returns:
            A ProductData object, or None if the element has no valid ASIN.
        """
        # Extract ASIN from data attribute
        asin = await element.get_attribute(AmazonSelectors.ASIN_ATTRIBUTE)
        if not asin or not asin.strip():
            return None

        asin = asin.strip()

        # Skip non-product entries (ads container, etc.)
        if len(asin) != 10:
            return None

        # Extract all product attributes
        price = await cls._extract_price(element)
        rating = await cls._extract_rating(element)
        review_count = await cls._extract_review_count(element)
        is_sponsored = await cls._check_sponsored(element)
        is_prime = await cls._check_prime(element)
        brand = await cls._extract_brand(element)
        title = await cls._extract_title(element)

        return ProductData(
            asin=asin,
            price=price,
            rating=rating,
            review_count=review_count,
            is_sponsored=is_sponsored,
            is_prime=is_prime,
            brand=brand,
            title=title,
            page_number=page_number,
            source_url=source_url,
        )

    @classmethod
    @staticmethod
    def _parse_price_string(text: str) -> Optional[float]:
        """Helper to reliably extract numeric float price from string."""
        if not text:
            return None
        text = text.strip()
        match = re.search(r"[\$\€\£\₺]?\s*([\d,]+\.?\d*)", text)
        if match:
            raw = match.group(1).replace(",", "")
            try:
                val = float(raw)
                return val if val > 0 else None
            except ValueError:
                pass
        return None

    @classmethod
    async def _extract_price(cls, element: ElementHandle) -> Optional[float]:
        """Extract the current actual selling price from the listing element."""
        # 1. Try .a-price:not(.a-text-price):not([data-a-strike="true"]) .a-offscreen (excludes strike-through original prices!)
        try:
            price_els = await element.query_selector_all('.a-price:not(.a-text-price):not([data-a-strike="true"])')
            for price_el in price_els:
                offscreen = await price_el.query_selector(".a-offscreen")
                if offscreen:
                    text = await offscreen.text_content()
                    val = cls._parse_price_string(text)
                    if val is not None:
                        return val
        except Exception:
            pass

        # 2. Try .a-price:not(.a-text-price):not([data-a-strike="true"]) whole and fraction elements
        try:
            price_els = await element.query_selector_all('.a-price:not(.a-text-price):not([data-a-strike="true"])')
            for price_el in price_els:
                whole_el = await price_el.query_selector(".a-price-whole")
                if whole_el:
                    whole_text = (await whole_el.text_content() or "").strip().rstrip(".,")
                    whole_text = re.sub(r"[^\d]", "", whole_text)
                    fraction_el = await price_el.query_selector(".a-price-fraction")
                    fraction_text = "00"
                    if fraction_el:
                        fraction_text = re.sub(r"[^\d]", "", await fraction_el.text_content() or "") or "00"
                    if whole_text:
                        return float(f"{whole_text}.{fraction_text}")
        except Exception:
            pass

        # 3. Fallback: .a-color-price
        try:
            price_el = await element.query_selector(".a-color-price")
            if price_el:
                text = await price_el.text_content()
                val = cls._parse_price_string(text)
                if val is not None:
                    return val
        except Exception:
            pass

        # 4. Fallback for "No featured offers" (Buy Box hidden)
        try:
            secondary_el = await element.query_selector('[data-cy="secondary-offer-recipe"]')
            if secondary_el:
                text = await secondary_el.inner_text()
                match = re.search(r"[\$\€\£\₺]\s*([\d,]+\.?\d*)", text)
                if match:
                    val = cls._parse_price_string(match.group(0))
                    if val is not None:
                        return val
        except Exception:
            pass

        return None

    @classmethod
    async def _extract_rating(cls, element: ElementHandle) -> Optional[float]:
        """Extract the star rating from the listing element."""
        try:
            selectors = [
                ".a-icon-star-small .a-icon-alt",
                ".a-icon-star .a-icon-alt",
                "i[class*='a-icon-star']",
                "span[aria-label*='out of 5 stars']",
                "span[aria-label*='stars']",
                "a[aria-label*='out of 5 stars']",
            ]
            for sel in selectors:
                rel = await element.query_selector(sel)
                if rel:
                    text = (await rel.get_attribute("aria-label")) or (await rel.text_content() or "")
                    match = re.search(r"([\d\.]+)\s*(?:out of|\/|stars)", text, re.IGNORECASE)
                    if match:
                        try:
                            val = float(match.group(1))
                            if 0.0 <= val <= 5.0:
                                return val
                        except ValueError:
                            pass
                    classes = (await rel.get_attribute("class")) or ""
                    match_class = re.search(r"a-star(?:-small)?-(\d)-(\d)", classes)
                    if match_class:
                        return float(f"{match_class.group(1)}.{match_class.group(2)}")
        except Exception:
            pass

        return None

    @classmethod
    async def _extract_review_count(
        cls, element: ElementHandle
    ) -> Optional[int]:
        """Extract the number of reviews from the listing element."""
        try:
            selectors = [
                'a[href*="customerReviews"] span',
                'a[href*="customerReviews"]',
                '.a-size-base.s-underline-text',
                '[data-cy="reviews-ratings-count"]',
                'span.a-size-base[aria-label*="ratings"]',
            ]
            for sel in selectors:
                rev_el = await element.query_selector(sel)
                if rev_el:
                    text = (await rev_el.text_content() or "") or (await rev_el.get_attribute("aria-label")) or ""
                    text = text.replace(",", "").strip()
                    k_match = re.search(r"([\d\.]+)\s*[kK]", text)
                    if k_match:
                        return int(float(k_match.group(1)) * 1000)
                    cleaned = re.sub(r"[^\d]", "", text)
                    if cleaned:
                        val = int(cleaned)
                        if val > 0:
                            return val
        except Exception:
            pass

        return None

    @classmethod
    async def _check_sponsored(cls, element: ElementHandle) -> bool:
        """Check if the product listing is a sponsored/ad result."""
        try:
            sponsored_el = await element.query_selector(
                AmazonSelectors.SPONSORED_LABEL
            )
            if sponsored_el:
                return True

            # Check for "Sponsored" text anywhere in the element
            full_text = await element.inner_text()
            if "Sponsored" in full_text or "sponsored" in full_text.lower():
                # Be more specific — check if it's near the top of the listing
                top_section = await element.query_selector(
                    ".a-row:first-child"
                )
                if top_section:
                    top_text = await top_section.inner_text()
                    if "sponsored" in top_text.lower():
                        return True
        except Exception:
            pass

        return False

    @classmethod
    async def _check_prime(cls, element: ElementHandle) -> bool:
        """Check if the product has a Prime badge."""
        try:
            # Check multiple Prime badge selectors
            for selector in (
                AmazonSelectors.PRIME_BADGE,
                AmazonSelectors.PRIME_BADGE_ALT,
                AmazonSelectors.PRIME_ICON,
            ):
                prime_el = await element.query_selector(selector)
                if prime_el:
                    return True
        except Exception:
            pass

        return False

    @classmethod
    async def _extract_brand(cls, element: ElementHandle) -> Optional[str]:
        """Extract the brand name from the listing element."""
        try:
            # Try the "by Brand" byline
            byline_el = await element.query_selector(
                ".a-row.a-size-base .a-size-base.a-color-secondary"
            )
            if byline_el:
                text = await byline_el.inner_text()
                return text.strip()

            # Try the brand link
            brand_el = await element.query_selector(
                'a[href*="brandtextbin"], .a-size-base-plus.a-color-base'
            )
            if brand_el:
                text = await brand_el.inner_text()
                return text.strip()
        except Exception:
            pass

        return None

    @classmethod
    async def _extract_title(cls, element: ElementHandle) -> Optional[str]:
        """Extract the product title from the listing element."""
        try:
            title_el = await element.query_selector(AmazonSelectors.BRAND)
            if title_el:
                text = await title_el.inner_text()
                return text.strip()
        except Exception:
            pass

        return None

    @classmethod
    async def check_no_results(cls, page: Page) -> bool:
        """Check if the page shows a 'no results' message."""
        try:
            no_results = await page.query_selector(AmazonSelectors.NO_RESULTS)
            return no_results is not None
        except Exception:
            return False

    @classmethod
    async def check_captcha(cls, page: Page) -> bool:
        """Check if Amazon is showing a CAPTCHA challenge."""
        try:
            captcha = await page.query_selector(AmazonSelectors.CAPTCHA_FORM)
            return captcha is not None
        except Exception:
            return False

    @classmethod
    async def get_total_pages(cls, page: Page) -> int:
        """
        Determine the total number of search result pages.

        Returns:
            The total page count, or 1 if pagination is not found.
        """
        try:
            # Check if there's any pagination at all
            pagination = await page.query_selector(
                AmazonSelectors.PAGINATION_STRIP
            )
            if pagination is None:
                return 1

            # Get all page number items (excluding next, previous, and ellipsis)
            items = await page.query_selector_all(
                ".s-pagination-item:not(.s-pagination-next):"
                "not(.s-pagination-previous):not(.s-pagination-ellipsis)"
            )
            
            if items:
                # The last item in the list will be the highest page number
                last_text = await items[-1].inner_text()
                cleaned = re.sub(r"[^\d]", "", last_text.strip())
                if cleaned:
                    return int(cleaned)

        except Exception as e:
            logger.warning("Toplam sayfa sayısı belirlenemedi: %s", e)

        return 1
