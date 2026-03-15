"""Acquisition layer — how we get raw content (direct APIs, web search, page fetching)."""

from src.data.acquisition.direct_api import try_direct_api
from src.data.acquisition.web_search import search_for_slot
from src.data.acquisition.page_fetcher import fetch_page_text

__all__ = [
    "try_direct_api",
    "search_for_slot",
    "fetch_page_text",
]
