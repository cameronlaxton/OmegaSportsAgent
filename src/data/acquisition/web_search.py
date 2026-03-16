"""
LLM-powered web search — the primary data acquisition path for slots
that direct APIs cannot serve.

Uses Anthropic's server-side web_search tool as the primary backend,
falling back to Perplexity if configured. Returns raw SearchResult
objects for extraction by the extractor layer.
"""

from __future__ import annotations

import logging
import os
from typing import List, Optional
from urllib.parse import urlparse

from agent.models import GatherSlot
from src.data.models.facts import SearchResult

logger = logging.getLogger("omega.data.acquisition.web_search")

# Sports-focused domains to prioritize in web search results
_SPORTS_DOMAINS = [
    "espn.com",
    "basketball-reference.com",
    "baseball-reference.com",
    "pro-football-reference.com",
    "hockey-reference.com",
    "covers.com",
    "vegasinsider.com",
    "actionnetwork.com",
    "oddshark.com",
    "rotowire.com",
    "cbssports.com",
    "nba.com",
    "nfl.com",
    "mlb.com",
    "nhl.com",
]


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

    Priority:
    1. Anthropic web_search tool (uses existing ANTHROPIC_API_KEY)
    2. Perplexity API (legacy fallback, if PERPLEXITY_API_KEY set)
    """
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
    if anthropic_key:
        results = _search_anthropic(query, anthropic_key)
        if results:
            return results

    perplexity_key = os.environ.get("PERPLEXITY_API_KEY")
    if perplexity_key:
        return _search_perplexity(query, perplexity_key)

    logger.warning("No search backend configured (set ANTHROPIC_API_KEY)")
    return []


def _search_anthropic(query: str, api_key: str) -> List[SearchResult]:
    """Search using Anthropic's server-side web_search tool.

    Uses Claude Haiku to keep costs low. The web_search tool is a server-side
    hosted tool that searches the web and returns results with citations.
    """
    import anthropic

    try:
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=2048,
            system=(
                "You are a sports data research assistant. "
                "Return factual, current sports statistics, odds, and betting lines. "
                "Include specific numbers (spreads, moneylines, totals, stats). "
                "Be precise and data-focused."
            ),
            tools=[
                {
                    "type": "web_search_20250305",
                    "name": "web_search",
                    "max_uses": 5,
                },
            ],
            messages=[{"role": "user", "content": query}],
        )

        results: List[SearchResult] = []

        for block in response.content:
            # Text blocks contain the synthesized search results
            if block.type == "text":
                # Extract citations if present
                citations = getattr(block, "citations", None) or []
                cited_urls: List[str] = []
                for cite in citations:
                    url = getattr(cite, "url", None)
                    if url:
                        cited_urls.append(url)

                # The text block is the main synthesized result
                if block.text.strip():
                    results.append(SearchResult(
                        url="anthropic://web_search",
                        title=f"Web Search: {query[:80]}",
                        snippet=block.text,
                        domain="anthropic.web_search",
                    ))

                # Add cited URLs as additional results for page fetching
                for url in cited_urls:
                    domain = _extract_domain(url)
                    results.append(SearchResult(
                        url=url,
                        title=f"Source: {domain}",
                        snippet="",
                        domain=domain,
                    ))

            # Web search result blocks (if the API returns them directly)
            elif block.type == "web_search_tool_result":
                search_results = getattr(block, "search_results", [])
                for sr in search_results:
                    url = getattr(sr, "url", "")
                    title = getattr(sr, "title", "")
                    snippet = getattr(sr, "page_snippet", "") or getattr(sr, "snippet", "")
                    domain = _extract_domain(url) if url else ""
                    if url:
                        results.append(SearchResult(
                            url=url,
                            title=title,
                            snippet=snippet,
                            domain=domain,
                        ))

        logger.info(
            "Anthropic web search returned %d results for: %s",
            len(results), query[:60],
        )
        return results

    except Exception as exc:
        logger.warning("Anthropic web search failed: %s", exc)
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
