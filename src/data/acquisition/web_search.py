"""
LLM-powered web search — the primary data acquisition path for slots
that direct APIs cannot serve.

Uses configurable search backends (Perplexity, SerpAPI, or any search API).
Returns raw SearchResult objects for extraction by the extractor layer.
"""

from __future__ import annotations

import logging
import os
from typing import List, Optional
from urllib.parse import urlparse

from agent.models import GatherSlot
from src.data.models.facts import SearchResult

logger = logging.getLogger("omega.data.acquisition.web_search")


def search_for_slot(slot: GatherSlot, queries: Optional[List[str]] = None) -> List[SearchResult]:
    """Execute web searches for a gather slot.

    Args:
        slot: The gather slot that needs data.
        queries: Pre-planned search queries. If None, generates them automatically.

    Returns:
        List of SearchResult objects with URL, title, snippet, and domain.
    """
    if queries is None:
        from src.data.orchestration.search_planner import plan_searches
        queries = plan_searches(slot)

    if not queries:
        return []

    results: List[SearchResult] = []
    for query in queries:
        try:
            batch = _execute_search(query)
            results.extend(batch)
        except Exception as exc:
            logger.debug("Search failed for query '%s': %s", query, exc)

    # Deduplicate by URL
    seen_urls: set = set()
    unique: List[SearchResult] = []
    for r in results:
        if r.url not in seen_urls:
            seen_urls.add(r.url)
            unique.append(r)

    logger.debug("Web search returned %d unique results for slot %s", len(unique), slot.key)
    return unique


def _execute_search(query: str) -> List[SearchResult]:
    """Execute a single search query via the configured search backend.

    Currently supports:
    - Perplexity API (if PERPLEXITY_API_KEY is set)
    - Returns empty list if no search backend is configured

    This is the extensibility point for adding SerpAPI, Brave, etc.
    """
    perplexity_key = os.environ.get("PERPLEXITY_API_KEY")
    if perplexity_key:
        return _search_perplexity(query, perplexity_key)

    logger.debug("No search backend configured (set PERPLEXITY_API_KEY)")
    return []


def _search_perplexity(query: str, api_key: str) -> List[SearchResult]:
    """Search using Perplexity API and extract structured results."""
    import httpx

    try:
        resp = httpx.post(
            "https://api.perplexity.ai/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "sonar",
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are a sports data research assistant. "
                            "Return factual, current sports statistics and information. "
                            "Always cite your sources with URLs."
                        ),
                    },
                    {"role": "user", "content": query},
                ],
            },
            timeout=15.0,
        )
        resp.raise_for_status()
        data = resp.json()

        # Extract citations from Perplexity response
        citations = data.get("citations", [])
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")

        results: List[SearchResult] = []

        # Create a result for the main response content
        if content:
            results.append(SearchResult(
                url="perplexity://search",
                title=f"Perplexity: {query[:80]}",
                snippet=content,
                domain="perplexity.ai",
            ))

        # Add citation URLs as additional results
        for url in citations:
            domain = _extract_domain(url)
            results.append(SearchResult(
                url=url,
                title=f"Source: {domain}",
                snippet="",  # Would need page fetch to get content
                domain=domain,
            ))

        return results

    except Exception as exc:
        logger.debug("Perplexity search failed: %s", exc)
        return []


def _extract_domain(url: str) -> str:
    """Extract the domain from a URL."""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc
        if domain.startswith("www."):
            domain = domain[4:]
        return domain
    except Exception:
        return ""
