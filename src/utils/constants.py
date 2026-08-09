"""
Application-wide constants and configuration values.

This module defines all static configuration used across the application,
including Amazon domain settings, UI theme tokens, crawling parameters,
database paths, and selector mappings.
"""

import os
from pathlib import Path

# =============================================================================
# Application Metadata
# =============================================================================

APP_NAME = "Amazon ASIN Finder"
APP_VERSION = "1.1.1"
APP_AUTHOR = "ASIN Finder Team"

# =============================================================================
# Paths
# =============================================================================

# Base directory is two levels up from this file (src/utils/constants.py → project root)
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
LOG_DIR = BASE_DIR / "logs"
DB_PATH = DATA_DIR / "asin_finder.db"
EXPORT_DIR = BASE_DIR / "exports"

# Ensure directories exist at import time
for _dir in (DATA_DIR, LOG_DIR, EXPORT_DIR):
    _dir.mkdir(parents=True, exist_ok=True)

# =============================================================================
# Amazon Domain & URL Validation
# =============================================================================

AMAZON_BASE_URL = "https://www.amazon.com"
AMAZON_SEARCH_PATH = "/s"

# Pattern to validate Amazon.com search URLs
AMAZON_URL_PATTERN = r"^https?://(www\.)?amazon\.com/(s|b|.*/b)[/\?].*"

# Maximum number of search URLs per task
MAX_URLS_PER_TASK = 50
MIN_URLS_PER_TASK = 1

# =============================================================================
# Crawling Parameters
# =============================================================================

# Delay between page requests (seconds) — randomized within this range
REQUEST_DELAY_MIN = 1.0
REQUEST_DELAY_MAX = 3.0

# Maximum concurrent pages open in browser
MAX_CONCURRENT_PAGES = 3

# Browser viewport dimensions
BROWSER_VIEWPORT_WIDTH = 1920
BROWSER_VIEWPORT_HEIGHT = 1080

# Page navigation timeout (milliseconds)
PAGE_TIMEOUT_MS = 30_000

# Maximum pages to crawl per search URL (safety limit)
MAX_PAGES_PER_URL = 400

# =============================================================================
# Retry Configuration
# =============================================================================

class RetryConfig:
    """Configuration for retry behavior on different error types."""

    # Timeout errors
    TIMEOUT_MAX_RETRIES = 3
    TIMEOUT_BASE_DELAY = 2.0  # seconds

    # HTTP 429 (Too Many Requests)
    RATE_LIMIT_MAX_RETRIES = 5
    RATE_LIMIT_BASE_DELAY = 10.0  # seconds

    # HTTP 503 (Service Unavailable)
    SERVICE_UNAVAILABLE_MAX_RETRIES = 3
    SERVICE_UNAVAILABLE_BASE_DELAY = 5.0  # seconds

    # Network errors
    NETWORK_MAX_RETRIES = 3
    NETWORK_BASE_DELAY = 3.0  # seconds

    # Exponential backoff multiplier
    BACKOFF_MULTIPLIER = 2.0

    # Maximum delay cap (seconds)
    MAX_DELAY = 300.0

# =============================================================================
# Amazon Page CSS Selectors
# =============================================================================

class AmazonSelectors:
    """
    CSS selectors for extracting data from Amazon search result pages.

    These are kept as configurable constants so they can be updated easily
    when Amazon changes their page structure.
    """

    # Search result container — each product listing
    SEARCH_RESULT = '[data-component-type="s-search-result"]'

    # ASIN attribute on the result container
    ASIN_ATTRIBUTE = "data-asin"

    # Price selectors
    PRICE_WHOLE = ".a-price .a-price-whole"
    PRICE_FRACTION = ".a-price .a-price-fraction"
    PRICE_SYMBOL = ".a-price .a-price-symbol"

    # Rating (star count)
    RATING = '[data-cy="reviews-ratings-count"]'
    RATING_ALT = ".a-icon-star-small .a-icon-alt"

    # Review count
    REVIEW_COUNT = '[data-cy="reviews-ratings-count"]'
    REVIEW_COUNT_ALT = ".a-size-base.s-underline-text"

    # Sponsored label
    SPONSORED_LABEL = ".puis-sponsored-label-text"
    SPONSORED_LABEL_ALT = 'span:has-text("Sponsored")'

    # Prime badge
    PRIME_BADGE = '[data-cy="prime-badge"]'
    PRIME_BADGE_ALT = ".s-prime"
    PRIME_ICON = ".a-icon-prime"

    # Brand / product title
    BRAND = "h2 .a-text-normal"
    BRAND_BYLINE = ".a-row.a-size-base > .a-size-base"

    # Pagination
    NEXT_PAGE = ".s-pagination-next"
    PAGINATION_STRIP = ".s-pagination-strip"
    CURRENT_PAGE = ".s-pagination-selected"
    LAST_PAGE = ".s-pagination-item:not(.s-pagination-next):not(.s-pagination-previous):last-child"

    # No results indicator
    NO_RESULTS = '[data-component-type="s-no-result"]'

    # CAPTCHA / challenge detection
    CAPTCHA_FORM = "#captchacharacters"
    CHALLENGE_PAGE = ".a-last"

# =============================================================================
# Task Status Enumeration
# =============================================================================

class TaskStatus:
    """Task lifecycle status constants."""
    WAITING = "waiting"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

# =============================================================================
# Filter Defaults
# =============================================================================

class FilterDefaults:
    """Default values for filter fields."""
    MIN_PRICE = 0.0
    MAX_PRICE = 999999.99
    MIN_RATING = 0.0
    MAX_RATING = 5.0
    MIN_REVIEWS = 0
    MAX_REVIEWS = 999999999
    PRIME_ONLY = False
    EXCLUDE_SPONSORED = False

# =============================================================================
# Export Settings
# =============================================================================

CSV_HEADER = "ASIN"
CSV_DELIMITER = ","
TXT_LINE_SEPARATOR = "\n"

# =============================================================================
# UI Theme Tokens
# =============================================================================

class ThemeColors:
    """Color palette tokens for the dark theme UI."""
    BG_PRIMARY = "#0d1117"
    BG_SECONDARY = "#161b22"
    BG_TERTIARY = "#21262d"
    BG_INPUT = "#0d1117"

    ACCENT = "#0078d4"
    ACCENT_HOVER = "#1a8fff"
    ACCENT_PRESSED = "#005a9e"

    SUCCESS = "#2ea043"
    SUCCESS_HOVER = "#3fb950"
    WARNING = "#d29922"
    WARNING_HOVER = "#e3b341"
    ERROR = "#f85149"
    ERROR_HOVER = "#ff6e6a"

    TEXT_PRIMARY = "#e6edf3"
    TEXT_SECONDARY = "#8b949e"
    TEXT_MUTED = "#6e7681"

    BORDER = "#30363d"
    BORDER_ACTIVE = "#58a6ff"

    SCROLLBAR_BG = "#161b22"
    SCROLLBAR_HANDLE = "#30363d"
    SCROLLBAR_HANDLE_HOVER = "#484f58"

# =============================================================================
# UI Dimensions
# =============================================================================

class UIDimensions:
    """Fixed dimensions for UI layout."""
    WINDOW_MIN_WIDTH = 1280
    WINDOW_MIN_HEIGHT = 720
    WINDOW_DEFAULT_WIDTH = 1440
    WINDOW_DEFAULT_HEIGHT = 900

    SIDEBAR_WIDTH = 280
    LOG_PANEL_WIDTH = 320

    BORDER_RADIUS = 8
    BORDER_RADIUS_SM = 4

    SPACING_XS = 4
    SPACING_SM = 8
    SPACING_MD = 12
    SPACING_LG = 16
    SPACING_XL = 24

# =============================================================================
# Logging
# =============================================================================

LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
LOG_MAX_BYTES = 10 * 1024 * 1024  # 10 MB
LOG_BACKUP_COUNT = 5
