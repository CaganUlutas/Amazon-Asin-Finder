"""
Filter panel widget.

Provides a form for configuring product filter criteria
including price, rating, reviews, Prime, and brand exclusions.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QDoubleSpinBox,
    QSpinBox,
    QCheckBox,
    QLineEdit,
    QFrame,
    QGroupBox,
)

from src.core.models import FilterModel
from src.utils.validators import FilterValidator


class FilterPanel(QWidget):
    """
    Filter configuration panel.

    Provides input fields for all filter criteria:
    - Price range (min/max)
    - Star rating range (min/max)
    - Review count range (min/max)
    - Prime-only toggle
    - Exclude sponsored toggle
    - Excluded brands (comma-separated)
    - Keywords (comma-separated)
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        # Title
        title = QLabel("Filtreler")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        # Filter card container
        card = QFrame()
        card.setObjectName("filterCard")
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(16)

        # Price range
        price_group = self._create_section("Fiyat Aralığı ($)")
        price_grid = QGridLayout()
        price_grid.setSpacing(8)

        price_grid.addWidget(QLabel("Min:"), 0, 0)
        self._min_price = QDoubleSpinBox()
        self._min_price.setRange(0, 999999.99)
        self._min_price.setDecimals(2)
        self._min_price.setSpecialValueText("—")
        self._min_price.setValue(0)
        self._min_price.setPrefix("$ ")
        price_grid.addWidget(self._min_price, 0, 1)

        price_grid.addWidget(QLabel("Max:"), 0, 2)
        self._max_price = QDoubleSpinBox()
        self._max_price.setRange(0, 999999.99)
        self._max_price.setDecimals(2)
        self._max_price.setSpecialValueText("—")
        self._max_price.setValue(0)
        self._max_price.setPrefix("$ ")
        price_grid.addWidget(self._max_price, 0, 3)

        price_group.layout().addLayout(price_grid)
        card_layout.addWidget(price_group)

        # Star rating range
        rating_group = self._create_section("Yıldız Puanı")
        rating_grid = QGridLayout()
        rating_grid.setSpacing(8)

        rating_grid.addWidget(QLabel("Min:"), 0, 0)
        self._min_rating = QDoubleSpinBox()
        self._min_rating.setRange(0, 5.0)
        self._min_rating.setDecimals(1)
        self._min_rating.setSingleStep(0.5)
        self._min_rating.setSpecialValueText("—")
        self._min_rating.setValue(0)
        self._min_rating.setSuffix(" ★")
        rating_grid.addWidget(self._min_rating, 0, 1)

        rating_grid.addWidget(QLabel("Max:"), 0, 2)
        self._max_rating = QDoubleSpinBox()
        self._max_rating.setRange(0, 5.0)
        self._max_rating.setDecimals(1)
        self._max_rating.setSingleStep(0.5)
        self._max_rating.setSpecialValueText("—")
        self._max_rating.setValue(0)
        self._max_rating.setSuffix(" ★")
        rating_grid.addWidget(self._max_rating, 0, 3)

        rating_group.layout().addLayout(rating_grid)
        card_layout.addWidget(rating_group)

        # Review count range
        review_group = self._create_section("Yorum Sayısı")
        review_grid = QGridLayout()
        review_grid.setSpacing(8)

        review_grid.addWidget(QLabel("Min:"), 0, 0)
        self._min_reviews = QSpinBox()
        self._min_reviews.setRange(0, 999999999)
        self._min_reviews.setSpecialValueText("—")
        self._min_reviews.setValue(0)
        review_grid.addWidget(self._min_reviews, 0, 1)

        review_grid.addWidget(QLabel("Max:"), 0, 2)
        self._max_reviews = QSpinBox()
        self._max_reviews.setRange(0, 999999999)
        self._max_reviews.setSpecialValueText("—")
        self._max_reviews.setValue(0)
        review_grid.addWidget(self._max_reviews, 0, 3)

        review_group.layout().addLayout(review_grid)
        card_layout.addWidget(review_group)

        # Checkboxes
        checkbox_layout = QHBoxLayout()
        checkbox_layout.setSpacing(24)

        self._prime_only = QCheckBox("Yalnızca Prime")
        checkbox_layout.addWidget(self._prime_only)

        self._exclude_sponsored = QCheckBox("Sponsorlu Hariç Tut")
        checkbox_layout.addWidget(self._exclude_sponsored)

        checkbox_layout.addStretch()
        card_layout.addLayout(checkbox_layout)

        # Excluded brands
        brands_label = QLabel("Hariç Tutulacak Markalar")
        brands_label.setObjectName("subtitleLabel")
        card_layout.addWidget(brands_label)

        self._excluded_brands = QLineEdit()
        self._excluded_brands.setPlaceholderText("Marka1, Marka2, Marka3 (virgülle ayırın)")
        card_layout.addWidget(self._excluded_brands)

        # Keywords
        keywords_label = QLabel("Anahtar Kelimeler (başlıkta arama)")
        keywords_label.setObjectName("subtitleLabel")
        card_layout.addWidget(keywords_label)

        self._keywords = QLineEdit()
        self._keywords.setPlaceholderText("kelime1, kelime2 (virgülle ayırın)")
        card_layout.addWidget(self._keywords)

        # Validation message
        self._validation_label = QLabel("")
        self._validation_label.setStyleSheet("color: #f85149; font-size: 12px;")
        self._validation_label.setWordWrap(True)
        self._validation_label.hide()
        card_layout.addWidget(self._validation_label)

        layout.addWidget(card)

    def _create_section(self, title: str) -> QFrame:
        """Create a labeled section frame."""
        frame = QFrame()
        frame_layout = QVBoxLayout(frame)
        frame_layout.setContentsMargins(0, 0, 0, 0)
        frame_layout.setSpacing(8)

        label = QLabel(title)
        label.setStyleSheet("font-weight: 600; font-size: 12px; color: #8b949e;")
        frame_layout.addWidget(label)

        return frame

    def get_filters(self) -> FilterModel:
        """
        Build a FilterModel from the current widget values.

        Returns:
            A FilterModel with the user's filter settings.
        """
        # Get price values (0 means "not set")
        min_price = self._min_price.value() if self._min_price.value() > 0 else None
        max_price = self._max_price.value() if self._max_price.value() > 0 else None

        # Get rating values (0 means "not set")
        min_rating = self._min_rating.value() if self._min_rating.value() > 0 else None
        max_rating = self._max_rating.value() if self._max_rating.value() > 0 else None

        # Get review values (0 means "not set")
        min_reviews = self._min_reviews.value() if self._min_reviews.value() > 0 else None
        max_reviews = self._max_reviews.value() if self._max_reviews.value() > 0 else None

        # Parse excluded brands
        brands_text = self._excluded_brands.text().strip()
        excluded_brands = (
            [b.strip() for b in brands_text.split(",") if b.strip()]
            if brands_text
            else []
        )

        # Parse keywords
        keywords_text = self._keywords.text().strip()
        keywords = (
            [k.strip() for k in keywords_text.split(",") if k.strip()]
            if keywords_text
            else []
        )

        return FilterModel(
            min_price=min_price,
            max_price=max_price,
            min_rating=min_rating,
            max_rating=max_rating,
            min_reviews=min_reviews,
            max_reviews=max_reviews,
            prime_only=self._prime_only.isChecked(),
            exclude_sponsored=self._exclude_sponsored.isChecked(),
            excluded_brands=excluded_brands,
            keywords=keywords,
        )

    def validate(self) -> tuple[bool, str]:
        """
        Validate filter values.

        Returns:
            A tuple of (is_valid, error_message).
        """
        errors = []

        min_price = self._min_price.value() if self._min_price.value() > 0 else None
        max_price = self._max_price.value() if self._max_price.value() > 0 else None
        valid, msg = FilterValidator.validate_price_range(min_price, max_price)
        if not valid:
            errors.append(msg)

        min_rating = self._min_rating.value() if self._min_rating.value() > 0 else None
        max_rating = self._max_rating.value() if self._max_rating.value() > 0 else None
        valid, msg = FilterValidator.validate_rating_range(min_rating, max_rating)
        if not valid:
            errors.append(msg)

        min_reviews = self._min_reviews.value() if self._min_reviews.value() > 0 else None
        max_reviews = self._max_reviews.value() if self._max_reviews.value() > 0 else None
        valid, msg = FilterValidator.validate_review_range(min_reviews, max_reviews)
        if not valid:
            errors.append(msg)

        if errors:
            self._validation_label.setText("\n".join(errors))
            self._validation_label.show()
            return False, "\n".join(errors)

        self._validation_label.hide()
        return True, ""

    def set_enabled(self, enabled: bool):
        """Enable or disable all filter inputs."""
        for widget in (
            self._min_price, self._max_price,
            self._min_rating, self._max_rating,
            self._min_reviews, self._max_reviews,
            self._prime_only, self._exclude_sponsored,
            self._excluded_brands, self._keywords,
        ):
            widget.setEnabled(enabled)

    def reset(self):
        """Reset all filters to default values."""
        self._min_price.setValue(0)
        self._max_price.setValue(0)
        self._min_rating.setValue(0)
        self._max_rating.setValue(0)
        self._min_reviews.setValue(0)
        self._max_reviews.setValue(0)
        self._prime_only.setChecked(False)
        self._exclude_sponsored.setChecked(False)
        self._excluded_brands.clear()
        self._keywords.clear()
        self._validation_label.hide()
