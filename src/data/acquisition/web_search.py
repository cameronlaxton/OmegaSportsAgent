"""
LLM-powered web search — the primary data acquisition path for slots
that direct APIs cannot serve.

Uses Perplexity Sonar as the primary backend (structured JSON output),
falling back to Anthropic web_search tool if Perplexity is unavailable.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, List, Optional
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
            batch = _execute_search(query, slot)
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


def _execute_search(query: str, slot: Optional[GatherSlot] = None) -> List[SearchResult]:
    """Execute a single search query via the configured search backend.

    Priority:
    1. Perplexity Sonar structured (returns JSON matching extractor schema)
    2. Anthropic web_search tool (fallback, returns prose)
    """
    perplexity_key = os.environ.get("PERPLEXITY_API_KEY")
    if perplexity_key and slot is not None:
        results = _search_perplexity_structured(query, perplexity_key, slot)
        if results:
            return results

    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
    if anthropic_key:
        results = _search_anthropic(query, anthropic_key)
        if results:
            return results

    logger.warning("No search backend configured (set PERPLEXITY_API_KEY or ANTHROPIC_API_KEY)")
    return []


# ---------------------------------------------------------------------------
# Perplexity Sonar — structured JSON search (primary)
# ---------------------------------------------------------------------------

def _get_schema_for_slot(slot: GatherSlot) -> Dict[str, str]:
    """Get the extractor schema for a slot type to embed in the Perplexity prompt."""
    from src.data.extractors.base_extractor import get_extractor

    extractor = get_extractor(slot.data_type)
    if extractor is not None:
        return extractor.schema_hint(slot)

    # Fallback generic schema
    return {"data": "str"}


def _build_perplexity_system_prompt(slot: GatherSlot, schema: Dict[str, str]) -> str:
    """Build a system prompt that tells Perplexity to return structured JSON."""
    schema_json = json.dumps(schema, indent=2)
    data_type = slot.data_type
    entity = slot.entity
    league = slot.league.upper()

    # Type-specific instructions for better data quality
    type_instructions = {
        "odds": (
            f"Search for current betting odds for {entity} in {league}. "
            "Find moneyline, point spread, and over/under totals from major sportsbooks "
            "(DraftKings, FanDuel, BetMGM, Caesars, etc.). "
            "Use American odds format (e.g., -110, +150). "
            "Spreads should be numeric (e.g., -3.5, +7). "
            "Totals should be the over/under number (e.g., 224.5)."
        ),
        "team_stat": (
            f"Search for current {league} season statistics for {entity}. "
            "Find offensive rating, defensive rating, pace, shooting percentages, "
            "rebounds, assists, turnovers per game, and win-loss record. "
            "Use the current season stats."
        ),
        "player_stat": (
            f"Search for current {league} season statistics for {entity}. "
            "Find points, rebounds, assists, steals, blocks per game, "
            "shooting percentages, and games played this season."
        ),
        "player_game_log": (
            f"Search for recent game logs for {entity} in {league}. "
            "Find the last 5-10 games with points, rebounds, assists, and minutes. "
            "Calculate averages if possible."
        ),
        "injury": (
            f"Search for the current {league} injury report for {entity}. "
            "Find all injured or questionable players, their injury type, "
            "and their status (out, doubtful, questionable, probable, day-to-day)."
        ),
        "schedule": (
            f"Search for today's {league} schedule involving {entity}. "
            "Find the opponent, game time, venue, and home/away designation."
        ),
    }

    instruction = type_instructions.get(data_type, (
        f"Search for current {data_type} data for {entity} in {league}."
    ))

    return (
        f"You are a sports data retrieval agent. Your ONLY job is to search the web "
        f"and return structured data.\n\n"
        f"{instruction}\n\n"
        f"Return ONLY a valid JSON object with these fields:\n"
        f"{schema_json}\n\n"
        f"RULES:\n"
        f"- Return ONLY the JSON object, no explanation or markdown\n"
        f"- Use null for any field you cannot find\n"
        f"- Numbers must be numeric (not strings)\n"
        f"- Use the most recent data available\n"
        f"- If multiple sources disagree, use the consensus or most reputable source"
    )


def _search_perplexity_structured(
    query: str, api_key: str, slot: GatherSlot
) -> List[SearchResult]:
    """Search using Perplexity Sonar and request structured JSON output.

    The key innovation: instead of getting prose and parsing it, we ask
    Perplexity to return data in the exact schema our extractors expect.
    This eliminates the lossy search→extract two-step.
    """
    import httpx

    schema = _get_schema_for_slot(slot)
    system_prompt = _build_perplexity_system_prompt(slot, schema)

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
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": query},
                ],
                "temperature": 0.0,
            },
            timeout=20.0,
        )
        resp.raise_for_status()
        data = resp.json()

        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        citations = data.get("citations", [])

        if not content:
            logger.warning("Perplexity returned empty content for: %s", query[:60])
            return []

        # Try to parse as JSON — this is the structured path
        parsed_json = _try_parse_json(content)

        results: List[SearchResult] = []

        if parsed_json is not None:
            # SUCCESS: Perplexity returned structured JSON
            # Store the JSON string in snippet, tagged with special domain
            logger.info(
                "Perplexity structured search succeeded for slot %s (%s): %d fields",
                slot.key, slot.data_type, len(parsed_json),
            )
            results.append(SearchResult(
                url="perplexity://structured",
                title=f"Perplexity Structured: {slot.data_type} for {slot.entity}",
                snippet=json.dumps(parsed_json),
                domain="perplexity.structured",
            ))
        else:
            # Perplexity returned prose instead of JSON — still usable by extractors
            logger.info(
                "Perplexity returned prose (not JSON) for slot %s, falling back to extraction",
                slot.key,
            )
            results.append(SearchResult(
                url="perplexity://search",
                title=f"Perplexity: {query[:80]}",
                snippet=content,
                domain="perplexity.ai",
            ))

        # Add citation URLs as additional results for potential page fetching
        for url in citations:
            domain = _extract_domain(url)
            results.append(SearchResult(
                url=url,
                title=f"Source: {domain}",
                snippet="",
                domain=domain,
            ))

        return results

    except Exception as exc:
        logger.warning("Perplexity structured search failed: %s", exc)
        return []


def _try_parse_json(text: str) -> Optional[Dict[str, Any]]:
    """Try to parse JSON from Perplexity response, handling markdown code blocks."""
    import re

    text = text.strip()

    # Strip markdown code blocks if present
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*\n?", "", text)
        text = re.sub(r"\n?```\s*$", "", text)
        text = text.strip()

    try:
        result = json.loads(text)
        if isinstance(result, dict):
            return result
    except json.JSONDecodeError:
        pass

    # Try to find a JSON object in the response
    match = re.search(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", text, re.DOTALL)
    if match:
        try:
            result = json.loads(match.group())
            if isinstance(result, dict):
                return result
        except json.JSONDecodeError:
            pass

    return None


# ---------------------------------------------------------------------------
# Anthropic web_search tool (fallback)
# ---------------------------------------------------------------------------

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
