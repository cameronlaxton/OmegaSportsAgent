"""
Retrieval Orchestrator — the main entry point for the search-first data pipeline.

Pipeline: cache → direct_api → web_search → extract → normalize → validate → fuse

This module replaces the old src/providers/ adapter pattern. It accepts GatherSlots
from the agent layer and returns GatheredFacts, honoring the same interface contract
defined in agent/models.py.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from agent.models import GatherSlot, GatheredFact, ProviderResult
from src.data.cache.db_cache import check_db_cache, store_to_db_cache
from src.data.cache.session_cache import SessionCache
from src.data.models.facts import FactBundle, SourceAttribution, SportsFact
from src.data.sources.source_config import get_confidence_for_tier, get_trust_tier

logger = logging.getLogger("omega.data.orchestration.retrieval")


def retrieve_facts(slots: List[GatherSlot]) -> List[GatheredFact]:
    """Fill gather slots via the search-first data pipeline.

    For each slot:
    1. Check session cache (in-memory LRU)
    2. Check DB cache (fact_snapshots via src/storage/fact_store)
    3. Try direct API (existing src/data/ modules — fast path)
    4. If direct API fails: web search → page fetch → extract
    5. Normalize extracted facts
    6. Validate (freshness, sanity, agreement)
    7. Fuse multi-source results
    8. Store to DB cache
    9. Return as GatheredFact

    Args:
        slots: List of GatherSlots from the requirement planner.

    Returns:
        List of GatheredFacts, one per input slot.
    """
    session_cache = SessionCache()
    results: List[GatheredFact] = []

    for slot in slots:
        fact = _fill_slot(slot, session_cache)
        results.append(fact)

    filled_count = sum(1 for f in results if f.filled)
    logger.info("Pipeline filled %d/%d slots", filled_count, len(slots))

    return results


def _fill_slot(slot: GatherSlot, session_cache: SessionCache) -> GatheredFact:
    """Fill a single gather slot through the pipeline stages."""

    # Stage 1: Session cache (in-memory, same query)
    cached_data = session_cache.get(slot.data_type, slot.entity, slot.league)
    if cached_data is not None:
        logger.debug("Session cache hit for slot %s", slot.key)
        return _data_to_gathered_fact(slot, cached_data, "session_cache", 0.9)

    # Stage 2: DB cache (persistent, TTL-governed)
    db_result = check_db_cache(slot)
    if db_result is not None:
        session_cache.put(slot.data_type, slot.entity, slot.league, db_result.data)
        return _provider_result_to_gathered_fact(slot, db_result)

    # Stage 3: Direct API (fast path to existing src/data/ modules)
    direct_result = _try_direct_api(slot)
    if direct_result is not None:
        session_cache.put(slot.data_type, slot.entity, slot.league, direct_result.data)
        _cache_result(slot, direct_result)
        return _provider_result_to_gathered_fact(slot, direct_result)

    # Stage 4: Web search → extract → normalize → validate → fuse
    search_result = _try_web_search_pipeline(slot)
    if search_result is not None:
        session_cache.put(slot.data_type, slot.entity, slot.league, search_result.data)
        _cache_result(slot, search_result)
        return _provider_result_to_gathered_fact(slot, search_result)

    # All sources exhausted
    logger.info("All sources exhausted for slot %s", slot.key)
    return GatheredFact(slot=slot, filled=False, quality_score=0.0)


def _try_direct_api(slot: GatherSlot) -> Optional[ProviderResult]:
    """Stage 3: Try existing API modules as fast path."""
    try:
        from src.data.acquisition.direct_api import try_direct_api
        return try_direct_api(slot)
    except Exception as exc:
        logger.debug("Direct API stage failed for slot %s: %s", slot.key, exc)
        return None


def _try_web_search_pipeline(slot: GatherSlot) -> Optional[ProviderResult]:
    """Stage 4: Web search → page fetch → extract → normalize → validate → fuse.

    This is the primary path for data not available via direct APIs.
    """
    try:
        # 4a. Search
        from src.data.acquisition.web_search import search_for_slot
        search_results = search_for_slot(slot)
        if not search_results:
            return None

        # 4b. Fetch pages and extract facts
        from src.data.acquisition.page_fetcher import fetch_page_text
        from src.data.extractors.base_extractor import get_extractor

        extractor = get_extractor(slot.data_type)
        if extractor is None:
            logger.debug("No extractor for data_type=%s", slot.data_type)
            return None

        all_facts: List[SportsFact] = []

        for sr in search_results:
            # Use snippet directly if available
            text = sr.snippet
            if not text and sr.url and not sr.url.startswith("perplexity://"):
                text = fetch_page_text(sr.url)

            if not text:
                continue

            trust_tier = get_trust_tier(sr.domain or sr.url)
            attribution = SourceAttribution(
                source_name=f"web_search:{sr.domain}" if sr.domain else "web_search",
                source_url=sr.url if not sr.url.startswith("perplexity://") else None,
                fetched_at=datetime.utcnow(),
                trust_tier=trust_tier,
                confidence=get_confidence_for_tier(trust_tier),
            )

            facts = extractor.extract(text, slot, attribution)
            all_facts.extend(facts)

        if not all_facts:
            return None

        # 4c. Normalize
        all_facts = _normalize_facts(all_facts, slot)

        # 4d. Validate
        all_facts = _validate_facts(all_facts, slot)

        if not all_facts:
            return None

        # 4e. Fuse
        bundle = FactBundle(
            slot_key=slot.key,
            data_type=slot.data_type,
            entity=slot.entity,
            league=slot.league,
            facts=all_facts,
        )

        from src.data.fusion.fact_fuser import fuse_facts
        from src.data.fusion.confidence_scorer import score_confidence

        fused_data = fuse_facts(bundle)
        confidence = score_confidence(bundle)

        if not fused_data:
            return None

        # Find the best source URL for attribution
        best_source = min(all_facts, key=lambda f: f.attribution.trust_tier)

        return ProviderResult(
            data=fused_data,
            source=best_source.attribution.source_name,
            source_url=best_source.attribution.source_url,
            fetched_at=datetime.utcnow(),
            confidence=confidence,
        )

    except Exception as exc:
        logger.debug("Web search pipeline failed for slot %s: %s", slot.key, exc)
        return None


def _normalize_facts(facts: List[SportsFact], slot: GatherSlot) -> List[SportsFact]:
    """Run normalization on extracted facts."""
    from src.data.normalizers.stat_normalizer import normalize_stat_value

    for fact in facts:
        if not fact.normalized:
            fact.value = normalize_stat_value(fact.key, fact.value, slot.league)
            fact.normalized = True

    return facts


def _validate_facts(facts: List[SportsFact], slot: GatherSlot) -> List[SportsFact]:
    """Run validation pipeline on facts."""
    from src.data.validators.freshness_validator import validate_freshness
    from src.data.validators.sanity_validator import validate_sanity

    # Freshness check
    facts = validate_freshness(facts, slot.data_type)

    # Sanity check
    facts = validate_sanity(facts)

    return facts


def _cache_result(slot: GatherSlot, result: ProviderResult) -> None:
    """Best-effort cache storage."""
    try:
        store_to_db_cache(slot, result, result.confidence)
    except Exception:
        pass


def _data_to_gathered_fact(
    slot: GatherSlot, data: Dict[str, Any], source: str, confidence: float
) -> GatheredFact:
    """Convert raw data dict to a GatheredFact."""
    return GatheredFact(
        slot=slot,
        result=ProviderResult(
            data=data,
            source=source,
            fetched_at=datetime.utcnow(),
            confidence=confidence,
        ),
        filled=True,
        quality_score=confidence,
    )


def _provider_result_to_gathered_fact(
    slot: GatherSlot, result: ProviderResult
) -> GatheredFact:
    """Convert a ProviderResult to a GatheredFact with quality scoring."""
    from agent.fact_gatherer import _score_result
    quality = _score_result(slot, result)
    return GatheredFact(
        slot=slot,
        result=result,
        filled=True,
        quality_score=quality,
    )
