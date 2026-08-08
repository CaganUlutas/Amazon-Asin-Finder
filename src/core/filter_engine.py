"""
Product filter engine.

Applies user-defined filter criteria to product data extracted
from Amazon search results. Supports filtering by price, rating,
review count, Prime status, sponsored exclusion, brand exclusion,
and keyword matching.
"""

from __future__ import annotations

from typing import Optional

from src.core.models import FilterModel, ProductData
from src.utils.logger import get_logger

logger = get_logger(__name__)


class FilterEngine:
    """
    Applies filter criteria to a list of products.

    Each filter criterion is applied independently. A product must
    pass ALL active filters to be included in the results.

    Usage:
        engine = FilterEngine(filter_model)
        matching = engine.apply(products)
        asins = [p.asin for p in matching]
    """

    def __init__(self, filters: FilterModel):
        """
        Initialize with the filter criteria to apply.

        Args:
            filters: The FilterModel containing all active criteria.
        """
        self._filters = filters

    def apply(self, products: list[ProductData]) -> list[ProductData]:
        """
        Apply all active filters to a list of products.

        Args:
            products: The raw products from the parser.

        Returns:
            A list of products that pass ALL filter criteria.
        """
        if not self._filters.has_any_filter():
            logger.debug("Filtre aktif değil, tüm ürünler dahil ediliyor.")
            return products

        filtered = []
        for product in products:
            if self._passes_all_filters(product):
                filtered.append(product)

        logger.info(
            "Filtreleme tamamlandı: %d/%d ürün filtreye uydu.",
            len(filtered),
            len(products),
        )
        return filtered

    def _passes_all_filters(self, product: ProductData) -> bool:
        """Check if a product passes ALL active filter criteria."""
        checks = [
            self._check_price(product),
            self._check_rating(product),
            self._check_reviews(product),
            self._check_prime(product),
            self._check_sponsored(product),
            self._check_brand(product),
            self._check_keywords(product),
        ]
        return all(checks)

    def _check_price(self, product: ProductData) -> bool:
        """Check if the product's price falls within the filter range."""
        if not self._filters.has_price_filter():
            return True

        if product.price is None:
            return False

        if self._filters.min_price is not None:
            if product.price < self._filters.min_price:
                return False

        if self._filters.max_price is not None:
            if product.price > self._filters.max_price:
                return False

        return True

    def _check_rating(self, product: ProductData) -> bool:
        """Check if the product's star rating falls within the filter range."""
        if not self._filters.has_rating_filter():
            return True

        if product.rating is None:
            return False

        if self._filters.min_rating is not None:
            if product.rating < self._filters.min_rating:
                return False

        if self._filters.max_rating is not None:
            if product.rating > self._filters.max_rating:
                return False

        return True

    def _check_reviews(self, product: ProductData) -> bool:
        """Check if the product's review count falls within the filter range."""
        if not self._filters.has_review_filter():
            return True

        if product.review_count is None:
            return False

        if self._filters.min_reviews is not None:
            if product.review_count < self._filters.min_reviews:
                return False

        if self._filters.max_reviews is not None:
            if product.review_count > self._filters.max_reviews:
                return False

        return True

    def _check_prime(self, product: ProductData) -> bool:
        """Check if the product meets the Prime-only filter requirement."""
        if not self._filters.prime_only:
            return True
        return product.is_prime

    def _check_sponsored(self, product: ProductData) -> bool:
        """Check if the product should be excluded as a sponsored listing."""
        if not self._filters.exclude_sponsored:
            return True
        return not product.is_sponsored

    def _check_brand(self, product: ProductData) -> bool:
        """Check if the product's brand is in the exclusion list."""
        if not self._filters.excluded_brands:
            return True

        excluded_lower = [b.lower().strip() for b in self._filters.excluded_brands if b.strip()]
        if not excluded_lower:
            return True

        if product.brand:
            p_brand = product.brand.lower().strip()
            if any(eb in p_brand for eb in excluded_lower):
                return False

        if product.title:
            p_title = product.title.lower().strip()
            if any(eb in p_title for eb in excluded_lower):
                return False

        return True

    def _check_keywords(self, product: ProductData) -> bool:
        """
        Check if the product title contains any of the filter keywords.

        If keywords are specified, the product title must contain at least
        one of the keywords to pass the filter.
        """
        if not self._filters.keywords:
            return True

        if product.title is None:
            return False

        title_lower = product.title.lower()
        return any(
            keyword.lower().strip() in title_lower
            for keyword in self._filters.keywords
        )


def deduplicate_asins(asins: list[str]) -> list[str]:
    """
    Remove duplicate ASINs while preserving order.

    Args:
        asins: List of ASIN strings (may contain duplicates).

    Returns:
        A deduplicated list preserving the first occurrence order.
    """
    seen = set()
    unique = []
    for asin in asins:
        asin_upper = asin.strip().upper()
        if asin_upper and asin_upper not in seen:
            seen.add(asin_upper)
            unique.append(asin_upper)
    return unique
