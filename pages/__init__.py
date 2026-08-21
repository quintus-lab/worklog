"""HTML page builders."""
from pages.history import page_history
from pages.index import page_index
from pages.layout import layout
from pages.login import page_login
from pages.settings import page_settings
from pages.week import page_week
from pages.common import (
    CATEGORIES,
    STATUSES,
    MAX_TITLE_LEN,
    MAX_DETAILS_LEN,
    safe_next_url,
    esc,
)

__all__ = [
    "layout",
    "page_login",
    "page_index",
    "page_history",
    "page_week",
    "page_settings",
    "CATEGORIES",
    "STATUSES",
    "MAX_TITLE_LEN",
    "MAX_DETAILS_LEN",
    "safe_next_url",
    "esc",
]
