"""
Narrative Intelligence Module

Generates rich, storytelling narratives for game analysis.
"""

from omega.narratives.narrative_engine import (
    NarrativeEngine,
    GameNarrative,
    TeamForm,
    Storyline,
    MatchupAnalysis,
    generate_narrative,
    generate_all_narratives
)

__all__ = [
    "NarrativeEngine",
    "GameNarrative", 
    "TeamForm",
    "Storyline",
    "MatchupAnalysis",
    "generate_narrative",
    "generate_all_narratives"
]
