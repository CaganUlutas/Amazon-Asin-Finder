"""
Input validation utilities.

Provides URL validation for Amazon.com search URLs and
ASIN format validation.
"""

from __future__ import annotations

import re
from urllib.parse import urlparse, parse_qs
from typing import Optional

from src.utils.constants import AMAZON_URL_PATTERN, MAX_URLS_PER_TASK, MIN_URLS_PER_TASK


class ValidationError(Exception):
    """Raised when input validation fails."""

    def __init__(self, message: str, field: Optional[str] = None):
        self.message = message
        self.field = field
        super().__init__(message)


class AmazonUrlValidator:
    """
    Validates Amazon.com search URLs.

    Ensures URLs are:
    - Valid HTTP/HTTPS URLs
    - From amazon.com domain only
    - Search result pages (containing /s? path)
    """

    # Compiled pattern for performance
    _URL_REGEX = re.compile(AMAZON_URL_PATTERN, re.IGNORECASE)

    # ASIN format: 10 alphanumeric characters, typically starting with 'B0'
    _ASIN_REGEX = re.compile(r"^[A-Z0-9]{10}$")

    @classmethod
    def validate_url(cls, url: str) -> tuple[bool, str]:
        """
        Validate a single Amazon search URL.

        Args:
            url: The URL string to validate.

        Returns:
            A tuple of (is_valid, error_message).
            If valid, error_message is an empty string.
        """
        if not url or not url.strip():
            return False, "URL boş olamaz."

        url = url.strip()

        # Basic URL structure check
        try:
            parsed = urlparse(url)
        except Exception:
            return False, "Geçersiz URL formatı."

        # Scheme check
        if parsed.scheme not in ("http", "https"):
            return False, "URL http:// veya https:// ile başlamalıdır."

        # Domain check — only amazon.com allowed
        hostname = parsed.hostname
        if hostname is None:
            return False, "URL'de domain bulunamadı."

        allowed_hosts = ("amazon.com", "www.amazon.com")
        if hostname.lower() not in allowed_hosts:
            return (
                False,
                f"Yalnızca amazon.com desteklenir. Girilen domain: {hostname}",
            )

        # Check path structure (search or category node)
        path = parsed.path
        if not (path.startswith("/s") or "/b/" in path or path.startswith("/b")):
            return False, "URL bir Amazon arama veya kategori (browse node) sayfası olmalıdır."

        # Regex pattern match for final validation
        if not cls._URL_REGEX.match(url):
            return False, "URL Amazon arama veya kategori formatına uymuyor."

        return True, ""

    @classmethod
    def validate_urls(cls, urls: list[str]) -> tuple[bool, list[str]]:
        """
        Validate a list of Amazon search URLs.

        Args:
            urls: List of URL strings to validate.

        Returns:
            A tuple of (all_valid, list_of_error_messages).
            If all valid, the error list is empty.
        """
        errors = []

        if not urls:
            errors.append("En az bir URL girilmelidir.")
            return False, errors

        # Remove empty strings and whitespace
        cleaned = [u.strip() for u in urls if u.strip()]

        if len(cleaned) < MIN_URLS_PER_TASK:
            errors.append(f"En az {MIN_URLS_PER_TASK} URL girilmelidir.")
            return False, errors

        if len(cleaned) > MAX_URLS_PER_TASK:
            errors.append(
                f"En fazla {MAX_URLS_PER_TASK} URL girilebilir. "
                f"Girilen: {len(cleaned)}"
            )
            return False, errors

        # Check for duplicates
        seen = set()
        for i, url in enumerate(cleaned):
            normalized = cls.normalize_url(url)
            if normalized in seen:
                errors.append(f"URL #{i + 1}: Tekrarlanan URL tespit edildi.")
            else:
                seen.add(normalized)

            is_valid, error = cls.validate_url(url)
            if not is_valid:
                errors.append(f"URL #{i + 1}: {error}")

        return len(errors) == 0, errors

    @classmethod
    def normalize_url(cls, url: str) -> str:
        """
        Normalize a URL for duplicate detection.

        Strips whitespace, lowercases scheme/host, removes trailing slashes.
        """
        url = url.strip()
        parsed = urlparse(url)
        # Reconstruct with lowercase scheme and host
        normalized = f"{parsed.scheme.lower()}://{parsed.hostname.lower()}"
        if parsed.path:
            normalized += parsed.path.rstrip("/")
        if parsed.query:
            normalized += f"?{parsed.query}"
        return normalized

    @classmethod
    def extract_search_keyword(cls, url: str) -> str:
        """
        Extract the search keyword from an Amazon search URL.

        Args:
            url: Amazon search URL.

        Returns:
            The search keyword, or empty string if not found.
        """
        try:
            parsed = urlparse(url)
            params = parse_qs(parsed.query)
            keyword = params.get("k", [""])[0]
            return keyword.replace("+", " ")
        except Exception:
            return ""

    @classmethod
    def validate_asin(cls, asin: str) -> bool:
        """
        Validate an ASIN code format.

        Args:
            asin: The ASIN string to validate.

        Returns:
            True if the ASIN format is valid.
        """
        if not asin:
            return False
        return bool(cls._ASIN_REGEX.match(asin.strip().upper()))


class FilterValidator:
    """Validates filter input values."""

    @staticmethod
    def validate_price_range(
        min_price: Optional[float], max_price: Optional[float]
    ) -> tuple[bool, str]:
        """Validate price range values."""
        if min_price is not None and min_price < 0:
            return False, "Minimum fiyat negatif olamaz."
        if max_price is not None and max_price < 0:
            return False, "Maksimum fiyat negatif olamaz."
        if (
            min_price is not None
            and max_price is not None
            and min_price > max_price
        ):
            return False, "Minimum fiyat, maksimum fiyattan büyük olamaz."
        return True, ""

    @staticmethod
    def validate_rating_range(
        min_rating: Optional[float], max_rating: Optional[float]
    ) -> tuple[bool, str]:
        """Validate star rating range values."""
        if min_rating is not None and (min_rating < 0 or min_rating > 5):
            return False, "Minimum puan 0-5 arasında olmalıdır."
        if max_rating is not None and (max_rating < 0 or max_rating > 5):
            return False, "Maksimum puan 0-5 arasında olmalıdır."
        if (
            min_rating is not None
            and max_rating is not None
            and min_rating > max_rating
        ):
            return False, "Minimum puan, maksimum puandan büyük olamaz."
        return True, ""

    @staticmethod
    def validate_review_range(
        min_reviews: Optional[int], max_reviews: Optional[int]
    ) -> tuple[bool, str]:
        """Validate review count range values."""
        if min_reviews is not None and min_reviews < 0:
            return False, "Minimum yorum sayısı negatif olamaz."
        if max_reviews is not None and max_reviews < 0:
            return False, "Maksimum yorum sayısı negatif olamaz."
        if (
            min_reviews is not None
            and max_reviews is not None
            and min_reviews > max_reviews
        ):
            return False, "Minimum yorum sayısı, maksimumdan büyük olamaz."
        return True, ""
