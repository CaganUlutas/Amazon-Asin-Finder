"""
Data models for the Amazon ASIN Finder application.

Defines immutable data structures using dataclasses for type safety
and clear domain modeling. These models are used across all layers
of the application.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class TaskStatusEnum(Enum):
    """Enumeration of possible task lifecycle states."""
    WAITING = "waiting"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class UrlStatusEnum(Enum):
    """Enumeration of possible URL processing states."""
    WAITING = "waiting"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class FilterModel:
    """
    Filter criteria for product selection.

    All fields are optional — None means "no filter applied" for that criterion.
    """
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    min_rating: Optional[float] = None
    max_rating: Optional[float] = None
    min_reviews: Optional[int] = None
    max_reviews: Optional[int] = None
    prime_only: bool = False
    exclude_sponsored: bool = False
    excluded_brands: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)

    def has_price_filter(self) -> bool:
        """Check if any price filter is active."""
        return self.min_price is not None or self.max_price is not None

    def has_rating_filter(self) -> bool:
        """Check if any rating filter is active."""
        return self.min_rating is not None or self.max_rating is not None

    def has_review_filter(self) -> bool:
        """Check if any review count filter is active."""
        return self.min_reviews is not None or self.max_reviews is not None

    def has_any_filter(self) -> bool:
        """Check if any filter criterion is active."""
        return (
            self.has_price_filter()
            or self.has_rating_filter()
            or self.has_review_filter()
            or self.prime_only
            or self.exclude_sponsored
            or len(self.excluded_brands) > 0
            or len(self.keywords) > 0
        )


@dataclass
class ProductData:
    """
    Raw product data extracted from an Amazon search result page.

    This represents a single product listing before filtering.
    """
    asin: str
    price: Optional[float] = None
    rating: Optional[float] = None
    review_count: Optional[int] = None
    is_sponsored: bool = False
    is_prime: bool = False
    brand: Optional[str] = None
    title: Optional[str] = None
    page_number: int = 0
    source_url: str = ""

    def __post_init__(self):
        """Validate ASIN format after initialization."""
        if self.asin:
            self.asin = self.asin.strip().upper()


@dataclass
class TaskUrlModel:
    """Represents a single search URL within a task."""
    id: Optional[int] = None
    task_id: str = ""
    url: str = ""
    page_count: int = 0
    processed_pages: int = 0
    status: UrlStatusEnum = UrlStatusEnum.WAITING

    @property
    def progress_percent(self) -> float:
        """Calculate progress percentage for this URL."""
        if self.page_count <= 0:
            return 0.0
        return min((self.processed_pages / self.page_count) * 100, 100.0)


@dataclass
class TaskModel:
    """
    Represents a crawling task with its full state.

    A task contains one or more search URLs and a set of filters.
    It tracks progress and produces a list of matching ASINs.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: TaskStatusEnum = TaskStatusEnum.WAITING
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    total_pages: int = 0
    processed_pages: int = 0
    total_products: int = 0
    matched_asins: int = 0
    error_message: Optional[str] = None
    urls: list[TaskUrlModel] = field(default_factory=list)
    filters: FilterModel = field(default_factory=FilterModel)
    asins: list[str] = field(default_factory=list)

    @property
    def progress_percent(self) -> float:
        """Calculate overall progress percentage."""
        if self.total_pages <= 0:
            return 0.0
        return min((self.processed_pages / self.total_pages) * 100, 100.0)

    @property
    def elapsed_seconds(self) -> float:
        """Calculate elapsed time in seconds since task started."""
        if self.started_at is None:
            return 0.0
        end = self.completed_at or datetime.now()
        return (end - self.started_at).total_seconds()

    @property
    def estimated_remaining_seconds(self) -> Optional[float]:
        """Estimate remaining time based on current progress rate."""
        if self.processed_pages <= 0 or self.started_at is None:
            return None
        elapsed = self.elapsed_seconds
        rate = self.processed_pages / elapsed  # pages per second
        remaining_pages = self.total_pages - self.processed_pages
        if rate <= 0:
            return None
        return remaining_pages / rate

    @property
    def display_name(self) -> str:
        """Generate a human-readable display name for the task."""
        if self.urls:
            first_url = self.urls[0].url
            name = self._extract_name_from_url(first_url)
            if name:
                suffix = f" (+{len(self.urls) - 1})" if len(self.urls) > 1 else ""
                return f"{name}{suffix}"
        return f"Task {self.id[:8]}"

    @staticmethod
    def _extract_name_from_url(url: str) -> str:
        """Extract search keyword or category slug from URL."""
        import urllib.parse
        try:
            parsed = urllib.parse.urlparse(url)
            params = urllib.parse.parse_qs(parsed.query)

            # 1. Search keyword 'k'
            if "k" in params and params["k"][0].strip():
                return params["k"][0].replace("+", " ").strip()

            # 2. Path slug (e.g. /bathroom-mirrors/b/...)
            path_parts = [p for p in parsed.path.split("/") if p]
            for i, part in enumerate(path_parts):
                if part in ("b", "s", "dp") and i > 0:
                    slug = path_parts[i - 1].replace("-", " ").replace("_", " ").strip()
                    if slug and slug.lower() not in ("s", "b", "gp", "browse"):
                        return slug.title()

            # 3. Category 'i' (e.g. i=photo)
            if "i" in params and params["i"][0].strip():
                cat = params["i"][0].replace("-", " ").replace("_", " ").strip()
                if cat.lower() != "aps":
                    return cat.title()

            # 4. Node parameter (e.g. node=13749901)
            if "node" in params and params["node"][0].strip():
                return f"Category Node {params['node'][0]}"

            # 5. First non-empty path segment fallback
            for part in path_parts:
                clean = part.replace("-", " ").replace("_", " ").strip()
                if clean and clean.lower() not in ("s", "b", "gp", "browse"):
                    return clean.title()
        except Exception:
            pass

        return ""

    @property
    def url_count(self) -> int:
        """Number of search URLs in this task."""
        return len(self.urls)


@dataclass
class CrawlProgress:
    """
    Progress update emitted during crawling.

    Used for real-time UI updates via Qt signals.
    """
    task_id: str
    url_index: int = 0
    current_page: int = 0
    total_pages: int = 0
    products_found: int = 0
    asins_matched: int = 0
    status: TaskStatusEnum = TaskStatusEnum.RUNNING
    message: str = ""


@dataclass
class LogEntry:
    """A single log entry for the UI log panel."""
    timestamp: datetime = field(default_factory=datetime.now)
    level: str = "INFO"
    source: str = ""
    message: str = ""

    @property
    def formatted(self) -> str:
        """Format log entry for display."""
        ts = self.timestamp.strftime("%H:%M:%S")
        return f"[{ts}] [{self.level}] {self.message}"
