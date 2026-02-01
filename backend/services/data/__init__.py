"""Shared data utilities for NFL play-by-play data."""

from .loader import load_data, DATA_DIR
from .columns import (
    Category,
    CATEGORIES,
    CATEGORY_MAP,
    get_category_summary,
    get_columns_for_categories,
)
