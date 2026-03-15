"""
Response Composer — assembles multi-package responses.

Receives:
    - The final AnswerPlan (possibly revised by the quality gate)
    - Computation results (simulation, edges, staking — if any)
    - Gathered facts with provenance
    - Data quality scores

Produces a structured response dict that:
1. Leads with what the user wanted
2. Includes all requested output packages
3. Discloses execution mode (native sim vs research)
4. Flags data quality issues where relevant
5. Never presents defaulted-input results as high-confidence
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from agent.models import (
    AnswerPlan,
    ExecutionMode,
    ExecutionResult,
    GatheredFact,
    OutputPackage,
    QueryUnderstanding,
)

if TYPE_CHECKING:
    from agent.llm_client import LLMClient

logger = logging.getLogger("omega.agent.response_composer")


def compose_response(
    understanding: QueryUnderstanding,
    plan: AnswerPlan,
    execution_result: ExecutionResult,
    facts: List[GatheredFact],
) -> Dict[str, Any]:
    """Assemble the final response from all lifecycle artifacts.

    Returns a structured dict with:
    - sections: ordered list of output sections
    - metadata: execution mode, data quality, provenance
    """
    sections: List[Dict[str, Any]] = []

    # -------------------------------------------------------------------
    # Clarification response — short-circuit
    # -------------------------------------------------------------------
    if plan.clarification_needed:
        return {
            "type": "clarification",
            "question": plan.clarification_question,
            "sections": [],
            "metadata": _build_metadata(plan, execution_result, facts),
        }

    # -------------------------------------------------------------------
    # Build sections for each output package in plan order
    # -------------------------------------------------------------------
    for package in plan.output_packages:
        section = _build_section(package, understanding, plan, execution_result, facts)
        if section:
            sections.append(section)

    return {
        "type": "answer",
        "sections": sections,
        "metadata": _build_metadata(plan, execution_result, facts),
    }


def _build_section(
    package: OutputPackage,
    understanding: QueryUnderstanding,
    plan: AnswerPlan,
    result: ExecutionResult,
    facts: List[GatheredFact],
) -> Optional[Dict[str, Any]]:
    """Build a single output section for a package."""

    builders = {
        OutputPackage.BET_CARD: _build_bet_card,
        OutputPackage.GAME_BREAKDOWN: _build_game_breakdown,
        OutputPackage.SCENARIO_ANALYSIS: _build_scenario_analysis,
        OutputPackage.KEY_FACTORS: _build_key_factors,
        OutputPackage.ALTERNATIVE_BETS: _build_alternative_bets,
        OutputPackage.BANKROLL_GUIDANCE: _build_bankroll_guidance,
        OutputPackage.NEWS_DIGEST: _build_news_digest,
        OutputPackage.RESEARCH_REPORT: _build_research_report,
        OutputPackage.PLAIN_EXPLANATION: _build_plain_explanation,
        OutputPackage.COMPACT_SUMMARY: _build_compact_summary,
        OutputPackage.LIMITED_CONTEXT_ANSWER: _build_limited_context,
    }

    builder = builders.get(package)
    if builder is None:
        logger.warning("No builder for output package: %s", package.value)
        return None

    return builder(understanding, plan, result, facts)


# ---------------------------------------------------------------------------
# Section builders — each returns a structured dict for that package type
# ---------------------------------------------------------------------------

def _build_bet_card(
    understanding: QueryUnderstanding,
    plan: AnswerPlan,
    result: ExecutionResult,
    facts: List[GatheredFact],
) -> Dict[str, Any]:
    """Build a bet card section from simulation edges."""
    return {
        "package": OutputPackage.BET_CARD.value,
        "title": "Bet Card",
        "edges": result.edges,
        "best_bet": result.best_bet,
        "data_completeness": result.data_completeness,
        "data_quality_score": result.data_quality_score,
        "requires_narrative": False,
    }


def _build_game_breakdown(
    understanding: QueryUnderstanding,
    plan: AnswerPlan,
    result: ExecutionResult,
    facts: List[GatheredFact],
) -> Dict[str, Any]:
    """Build a game breakdown section."""
    has_sim = result.simulation is not None
    return {
        "package": OutputPackage.GAME_BREAKDOWN.value,
        "title": "Game Breakdown",
        "simulation": result.simulation if has_sim else None,
        "sim_based": has_sim,
        "gathered_facts": _summarize_facts(facts),
        "requires_narrative": True,
    }


def _build_scenario_analysis(
    understanding: QueryUnderstanding,
    plan: AnswerPlan,
    result: ExecutionResult,
    facts: List[GatheredFact],
) -> Dict[str, Any]:
    return {
        "package": OutputPackage.SCENARIO_ANALYSIS.value,
        "title": "Scenario Analysis",
        "simulation": result.simulation,
        "gathered_facts": _summarize_facts(facts),
        "requires_narrative": True,
    }


def _build_key_factors(
    understanding: QueryUnderstanding,
    plan: AnswerPlan,
    result: ExecutionResult,
    facts: List[GatheredFact],
) -> Dict[str, Any]:
    """Key factors — always producible from gathered facts."""
    return {
        "package": OutputPackage.KEY_FACTORS.value,
        "title": "Key Factors",
        "gathered_facts": _summarize_facts(facts),
        "requires_narrative": True,
    }


def _build_alternative_bets(
    understanding: QueryUnderstanding,
    plan: AnswerPlan,
    result: ExecutionResult,
    facts: List[GatheredFact],
) -> Dict[str, Any]:
    return {
        "package": OutputPackage.ALTERNATIVE_BETS.value,
        "title": "Alternative Bets",
        "edges": [e for e in result.edges if e.get("is_alternative", False)],
        "requires_narrative": True,
    }


def _build_bankroll_guidance(
    understanding: QueryUnderstanding,
    plan: AnswerPlan,
    result: ExecutionResult,
    facts: List[GatheredFact],
) -> Dict[str, Any]:
    return {
        "package": OutputPackage.BANKROLL_GUIDANCE.value,
        "title": "Bankroll Guidance",
        "requires_narrative": True,
    }


def _build_news_digest(
    understanding: QueryUnderstanding,
    plan: AnswerPlan,
    result: ExecutionResult,
    facts: List[GatheredFact],
) -> Dict[str, Any]:
    injury_facts = [f for f in facts if f.slot.data_type == "injury" and f.filled]
    return {
        "package": OutputPackage.NEWS_DIGEST.value,
        "title": "News & Injuries",
        "injuries": _summarize_facts(injury_facts),
        "requires_narrative": True,
    }


def _build_research_report(
    understanding: QueryUnderstanding,
    plan: AnswerPlan,
    result: ExecutionResult,
    facts: List[GatheredFact],
) -> Dict[str, Any]:
    return {
        "package": OutputPackage.RESEARCH_REPORT.value,
        "title": "Research Analysis",
        "gathered_facts": _summarize_facts(facts),
        "source_count": sum(1 for f in facts if f.filled),
        "requires_narrative": True,
    }


def _build_plain_explanation(
    understanding: QueryUnderstanding,
    plan: AnswerPlan,
    result: ExecutionResult,
    facts: List[GatheredFact],
) -> Dict[str, Any]:
    return {
        "package": OutputPackage.PLAIN_EXPLANATION.value,
        "title": "Explanation",
        "requires_narrative": True,
    }


def _build_compact_summary(
    understanding: QueryUnderstanding,
    plan: AnswerPlan,
    result: ExecutionResult,
    facts: List[GatheredFact],
) -> Dict[str, Any]:
    return {
        "package": OutputPackage.COMPACT_SUMMARY.value,
        "title": "Summary",
        "simulation": result.simulation,
        "gathered_facts": _summarize_facts(facts),
        "requires_narrative": True,
    }


def _build_limited_context(
    understanding: QueryUnderstanding,
    plan: AnswerPlan,
    result: ExecutionResult,
    facts: List[GatheredFact],
) -> Dict[str, Any]:
    """Ultra-low-data response — explicitly narrows scope."""
    filled = [f for f in facts if f.filled]
    missing = [f for f in facts if not f.filled]
    return {
        "package": OutputPackage.LIMITED_CONTEXT_ANSWER.value,
        "title": "Limited Information Available",
        "available_facts": _summarize_facts(filled),
        "missing_data": [f.slot.key for f in missing],
        "data_quality_score": result.data_quality_score,
        "requires_narrative": True,
        "caveats": [
            "Limited data available for this query.",
            "Analysis is based on incomplete information.",
        ],
    }


# ---------------------------------------------------------------------------
# LLM-enhanced response composition
# ---------------------------------------------------------------------------

NARRATIVE_SYSTEM_PROMPT = """You are the response writer for OmegaSportsAgent, a quantitative sports analytics engine.

Given structured data from a simulation or research pipeline, write a concise, insightful narrative paragraph for the user. Rules:
- Be quantitative: cite specific numbers (probabilities, edges, scores).
- Be transparent: note data quality issues or missing data.
- Match the user's tone (analytical, conversational, or brief).
- Never fabricate data — only use what is provided in the structured data.
- Keep it to 2-4 sentences unless the data warrants more.
- If data quality is low, caveat your conclusions.
"""


def compose_response_with_llm(
    understanding: QueryUnderstanding,
    plan: AnswerPlan,
    execution_result: ExecutionResult,
    facts: List[GatheredFact],
    llm_client: "LLMClient",
) -> Dict[str, Any]:
    """Compose response with LLM-generated narratives for each section.

    Calls the base ``compose_response()`` first, then enriches sections
    that have ``requires_narrative: True`` with a natural-language paragraph.
    Falls back to the plain structured response if LLM generation fails.
    """
    response = compose_response(understanding, plan, execution_result, facts)

    if response.get("type") != "answer":
        return response

    for section in response.get("sections", []):
        if not section.get("requires_narrative"):
            continue

        # Build a focused prompt for this section
        section_data = {k: v for k, v in section.items() if k not in ("requires_narrative", "narrative")}
        prompt = (
            f"User query: {understanding.raw_prompt}\n"
            f"Desired tone: {understanding.tone}\n"
            f"Section type: {section.get('package', 'unknown')}\n"
            f"Section data:\n{json.dumps(section_data, indent=2, default=str)}"
        )

        narrative = llm_client.generate_text(
            system=NARRATIVE_SYSTEM_PROMPT,
            prompt=prompt,
            max_tokens=512,
        )
        if narrative:
            section["narrative"] = narrative

    return response


# ---------------------------------------------------------------------------
# Metadata
# ---------------------------------------------------------------------------

def _build_metadata(
    plan: AnswerPlan,
    result: ExecutionResult,
    facts: List[GatheredFact],
) -> Dict[str, Any]:
    """Build response metadata for transparency."""
    sources = set()
    for fact in facts:
        if fact.filled and fact.result:
            sources.add(fact.result.source)

    return {
        "execution_mode": result.mode.value,
        "simulation_ran": result.simulation is not None,
        "data_quality_score": result.data_quality_score,
        "data_completeness": result.data_completeness,
        "sources_used": sorted(sources),
        "total_slots": len(facts),
        "filled_slots": sum(1 for f in facts if f.filled),
        "packages_included": [p.value for p in plan.output_packages],
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _summarize_facts(facts: List[GatheredFact]) -> List[Dict[str, Any]]:
    """Summarize gathered facts for inclusion in response sections."""
    summaries = []
    for fact in facts:
        if not fact.filled or not fact.result:
            continue
        summaries.append({
            "key": fact.slot.key,
            "data": fact.result.data,
            "source": fact.result.source,
            "confidence": fact.result.confidence,
        })
    return summaries
