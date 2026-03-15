"""
Base extractor — protocol and factory for LLM-assisted fact extraction.

Extractors convert raw text (from web search snippets, fetched pages, or API
responses) into structured SportsFact objects. Each extractor type provides
schema hints to guide the LLM and rule-based fallback parsing for common formats.
"""

from __future__ import annotations

import json
import logging
import os
import re
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional

from agent.models import GatherSlot
from src.data.models.facts import SourceAttribution, SportsFact

logger = logging.getLogger("omega.data.extractors.base")


class FactExtractor(ABC):
    """Base class for type-specific fact extractors."""

    @property
    @abstractmethod
    def data_type(self) -> str:
        """The data type this extractor handles (e.g., 'team_stat', 'odds')."""
        ...

    @abstractmethod
    def schema_hint(self, slot: GatherSlot) -> Dict[str, str]:
        """Return a schema hint mapping field names to expected types.

        This tells the LLM what fields to extract.
        Example: {"off_rating": "float", "def_rating": "float", "pace": "float"}
        """
        ...

    @abstractmethod
    def extract_rule_based(
        self, raw_text: str, slot: GatherSlot, attribution: SourceAttribution
    ) -> List[SportsFact]:
        """Try rule-based extraction for well-known formats.

        Returns extracted facts, or empty list if no patterns match.
        """
        ...

    def extract(
        self, raw_text: str, slot: GatherSlot, attribution: SourceAttribution
    ) -> List[SportsFact]:
        """Extract facts from raw text using rules first, then LLM.

        Args:
            raw_text: Text content to extract from.
            slot: The gather slot driving extraction.
            attribution: Source provenance metadata.

        Returns:
            List of extracted SportsFact objects.
        """
        if not raw_text or not raw_text.strip():
            return []

        # Try rule-based extraction first (fast, no API cost)
        facts = self.extract_rule_based(raw_text, slot, attribution)
        if facts:
            return facts

        # Fall back to LLM extraction
        return self._extract_with_llm(raw_text, slot, attribution)

    def _extract_with_llm(
        self, raw_text: str, slot: GatherSlot, attribution: SourceAttribution
    ) -> List[SportsFact]:
        """Use LLM to extract structured facts from raw text."""
        api_key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("OPENAI_API_KEY")
        if not api_key:
            logger.debug("No LLM API key configured for extraction")
            return []

        schema = self.schema_hint(slot)
        prompt = _build_extraction_prompt(slot, schema, raw_text)

        try:
            extracted = _call_llm_extract(prompt, api_key)
            if not extracted:
                return []

            facts = []
            for key, value in extracted.items():
                if key in schema and value is not None:
                    facts.append(SportsFact(
                        key=key,
                        value=_coerce_value(value, schema[key]),
                        data_type=self.data_type,
                        entity=slot.entity,
                        league=slot.league,
                        attribution=attribution,
                    ))
            return facts

        except Exception as exc:
            logger.debug("LLM extraction failed: %s", exc)
            return []


def get_extractor(data_type: str) -> Optional[FactExtractor]:
    """Factory: get the appropriate extractor for a data type."""
    from src.data.extractors.schedule_extractor import ScheduleExtractor
    from src.data.extractors.odds_extractor import OddsExtractor
    from src.data.extractors.stats_extractor import StatsExtractor
    from src.data.extractors.injury_extractor import InjuryExtractor
    from src.data.extractors.game_log_extractor import GameLogExtractor

    _EXTRACTORS: Dict[str, FactExtractor] = {
        "schedule": ScheduleExtractor(),
        "odds": OddsExtractor(),
        "team_stat": StatsExtractor(),
        "player_stat": StatsExtractor(),
        "injury": InjuryExtractor(),
        "player_game_log": GameLogExtractor(),
    }
    return _EXTRACTORS.get(data_type)


# ---------------------------------------------------------------------------
# LLM helpers
# ---------------------------------------------------------------------------

def _build_extraction_prompt(
    slot: GatherSlot, schema: Dict[str, str], raw_text: str
) -> str:
    """Build a structured extraction prompt for the LLM."""
    schema_str = json.dumps(schema, indent=2)
    # Truncate raw text to avoid token limits
    text_truncated = raw_text[:8000]

    return (
        f"Extract sports data from the following text.\n\n"
        f"Entity: {slot.entity}\n"
        f"League: {slot.league}\n"
        f"Data type: {slot.data_type}\n\n"
        f"Extract these fields (return JSON only, no explanation):\n"
        f"{schema_str}\n\n"
        f"Text to extract from:\n"
        f"{text_truncated}\n\n"
        f"Return a JSON object with the extracted values. "
        f"Use null for any field you cannot find. "
        f"Numbers should be numeric (not strings)."
    )


def _call_llm_extract(prompt: str, api_key: str) -> Optional[Dict[str, Any]]:
    """Call an LLM to extract structured data.

    Tries Anthropic first, then OpenAI.
    """
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
    if anthropic_key:
        return _call_anthropic(prompt, anthropic_key)

    openai_key = os.environ.get("OPENAI_API_KEY")
    if openai_key:
        return _call_openai(prompt, openai_key)

    return None


def _call_anthropic(prompt: str, api_key: str) -> Optional[Dict[str, Any]]:
    """Extract using Anthropic Claude API."""
    import httpx

    resp = httpx.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 1024,
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=15.0,
    )
    resp.raise_for_status()
    content = resp.json()["content"][0]["text"]
    return _parse_json_response(content)


def _call_openai(prompt: str, api_key: str) -> Optional[Dict[str, Any]]:
    """Extract using OpenAI API."""
    import httpx

    resp = httpx.post(
        "https://api.openai.com/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.0,
        },
        timeout=15.0,
    )
    resp.raise_for_status()
    content = resp.json()["choices"][0]["message"]["content"]
    return _parse_json_response(content)


def _parse_json_response(text: str) -> Optional[Dict[str, Any]]:
    """Parse a JSON response from an LLM, handling code blocks."""
    # Strip markdown code blocks if present
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*\n?", "", text)
        text = re.sub(r"\n?```\s*$", "", text)

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Try to find JSON object in the response
        match = re.search(r"\{[^{}]*\}", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
    return None


def _coerce_value(value: Any, expected_type: str) -> Any:
    """Coerce a value to the expected type."""
    if value is None:
        return None

    try:
        if expected_type == "float":
            return float(value)
        elif expected_type == "int":
            return int(value)
        elif expected_type == "str":
            return str(value)
        elif expected_type == "bool":
            return bool(value)
        elif expected_type == "list":
            return value if isinstance(value, list) else [value]
    except (ValueError, TypeError):
        pass

    return value
