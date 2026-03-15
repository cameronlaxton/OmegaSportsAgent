"""
Intent Understanding — multi-dimensional classification of user prompts.

Produces a QueryUnderstanding that captures Subject, Goal, entities,
constraints, and tone along independent dimensions. Uses LLM function-calling
when available, with a heuristic fallback that works without any LLM.

The heuristic parser defaults wants_betting_advice=False unless the prompt
contains strong betting signals. Betting advice requires an affirmative
signal, not a default assumption.
"""

from __future__ import annotations

import logging
import re
from datetime import date
from typing import List, Optional, Tuple

from agent.models import (
    Entity,
    EntityRole,
    QueryUnderstanding,
    Subject,
    UserGoal,
)

logger = logging.getLogger("omega.agent.intent")

# ---------------------------------------------------------------------------
# League keyword mapping
# ---------------------------------------------------------------------------

LEAGUE_KEYWORDS = {
    "nba": "NBA", "basketball": "NBA", "hoops": "NBA",
    "wnba": "WNBA",
    "ncaab": "NCAAB", "college basketball": "NCAAB", "march madness": "NCAAB",
    "nfl": "NFL", "football": "NFL",
    "ncaaf": "NCAAF", "college football": "NCAAF", "cfb": "NCAAF",
    "mlb": "MLB", "baseball": "MLB",
    "nhl": "NHL", "hockey": "NHL",
    "mls": "MLS", "soccer": "EPL", "premier league": "EPL",
    "epl": "EPL", "la liga": "LA_LIGA", "bundesliga": "BUNDESLIGA",
    "serie a": "SERIE_A", "ligue 1": "LIGUE_1", "champions league": "CHAMPIONS_LEAGUE",
    "ufc": "UFC", "mma": "UFC", "boxing": "BOXING", "fight": "UFC",
    "atp": "ATP", "wta": "WTA", "tennis": "ATP",
    "pga": "PGA", "golf": "PGA", "lpga": "LPGA",
    "cs2": "CS2", "csgo": "CS2", "esports": "ESPORTS",
    "valorant": "VALORANT", "league of legends": "LOL", "lol": "LOL",
    "dota": "DOTA2",
}

# Betting intent signals — presence of these implies wants_betting_advice=True
BETTING_SIGNALS = {
    "should i bet", "is that a play", "is this a play", "worth a bet",
    "edge", "units", "stake", "wager", "bet on", "play this",
    "sharp", "value", "ev", "expected value", "kelly",
    "hammer", "lock", "parlay", "sgp", "same game",
    "how should i play", "what's the play", "any plays",
}

# Goal signals
GOAL_SIGNALS = {
    "decide": ["should i", "is it worth", "play this", "bet this", "is that a play"],
    "explain": ["why", "how come", "what happened", "explain"],
    "compare": ["compare", "versus", "vs", "which is better", "difference between"],
    "discuss": ["what do you think", "thoughts on", "opinion", "take on"],
    "summarize": ["catch me up", "summary", "what's happening", "recap", "rundown"],
    "learn": ["how does", "what is", "teach me", "explain how", "definition of"],
    "monitor": ["any value", "any edges", "what's on the board", "scan", "find me"],
}

# Subject signals
SUBJECT_SIGNALS_BANKROLL = {"bankroll", "aggressive", "conservative", "risk", "sizing", "how much", "units"}
SUBJECT_SIGNALS_PROP = {"over", "under", "points", "rebounds", "assists", "yards", "prop", "o/u"}
SUBJECT_SIGNALS_SLATE = {"slate", "all games", "tonight's games", "today's games", "full card", "board"}


# ---------------------------------------------------------------------------
# Heuristic parser (no LLM required)
# ---------------------------------------------------------------------------

def _detect_league(prompt_lower: str) -> Optional[str]:
    """Detect league from keywords in the prompt."""
    for keyword, league in LEAGUE_KEYWORDS.items():
        if keyword in prompt_lower:
            return league
    return None


def _extract_teams(prompt: str) -> Tuple[Optional[str], Optional[str]]:
    """Extract two team names from 'X vs Y' or 'X at Y' patterns."""
    patterns = [
        r"(.+?)\s+(?:vs\.?|versus|v\.?)\s+(.+)",
        r"(.+?)\s+(?:at|@)\s+(.+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, prompt, re.IGNORECASE)
        if match:
            away = match.group(1).strip().rstrip("?.,!")
            home = match.group(2).strip().rstrip("?.,!")
            # Clean up: remove trailing league keywords
            for kw in LEAGUE_KEYWORDS:
                away = re.sub(rf"\s+{re.escape(kw)}$", "", away, flags=re.IGNORECASE)
                home = re.sub(rf"\s+{re.escape(kw)}$", "", home, flags=re.IGNORECASE)
            return home, away
    return None, None


def _detect_goal(prompt_lower: str) -> UserGoal:
    """Detect the user's goal from signal phrases."""
    for goal, signals in GOAL_SIGNALS.items():
        for signal in signals:
            if signal in prompt_lower:
                return UserGoal(goal)
    return UserGoal.ANALYZE  # default


def _detect_betting_intent(prompt_lower: str) -> bool:
    """Returns True only if there are strong betting signals in the prompt."""
    return any(signal in prompt_lower for signal in BETTING_SIGNALS)


def _detect_subjects(prompt_lower: str, home: Optional[str], away: Optional[str],
                     has_prop_signals: bool, has_slate_signals: bool,
                     has_bankroll_signals: bool, league: Optional[str]) -> List[Subject]:
    """Determine which subjects the prompt covers."""
    subjects = []

    if has_bankroll_signals:
        subjects.append(Subject.BANKROLL)

    if has_prop_signals:
        subjects.append(Subject.PLAYER_PROP)
    elif has_slate_signals:
        subjects.append(Subject.SLATE)
    elif home and away:
        subjects.append(Subject.GAME)
    elif league:
        # Single team mentioned or just a league reference
        subjects.append(Subject.GAME)

    # If no specific subject detected, infer from context
    if not subjects:
        if league:
            subjects.append(Subject.GENERAL_SPORTS)
        else:
            subjects.append(Subject.GENERAL_SPORTS)

    return subjects


def _extract_prop_details(prompt_lower: str) -> Tuple[Optional[str], Optional[float]]:
    """Extract prop type and line from prompt."""
    # Pattern: "over 25.5 points" or "under 7.5 rebounds"
    prop_pattern = r"(?:over|under)\s+([\d.]+)\s+(\w+)"
    match = re.search(prop_pattern, prompt_lower)
    if match:
        line = float(match.group(1))
        stat = match.group(2).rstrip("s")  # "points" → "point"
        stat_map = {
            "point": "pts", "rebound": "reb", "assist": "ast",
            "three": "3pm", "steal": "stl", "block": "blk",
            "yard": "pass_yds", "reception": "receptions",
            "touchdown": "td", "goal": "goals", "ace": "aces",
            "kill": "kills", "save": "saves", "shot": "shots",
        }
        return stat_map.get(stat, stat), line

    # Pattern: "LeBron 25.5 points" or "player_name o25.5 pts"
    line_pattern = r"[uo]?([\d.]+)\s*(?:pts|points|reb|rebounds|ast|assists|yds|yards)"
    match = re.search(line_pattern, prompt_lower)
    if match:
        return None, float(match.group(1))

    return None, None


def _detect_tone(prompt_lower: str) -> str:
    """Infer desired response tone."""
    if any(w in prompt_lower for w in ("quick", "brief", "short", "tldr", "tl;dr")):
        return "brief"
    if any(w in prompt_lower for w in ("think", "opinion", "feel", "vibe")):
        return "conversational"
    return "analytical"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse_heuristic(prompt: str) -> QueryUnderstanding:
    """Parse a user prompt into a QueryUnderstanding using heuristics only.

    This is the fallback path when no LLM is available. It works well for
    common patterns but misses nuance on ambiguous or complex prompts.
    """
    prompt_lower = prompt.lower().strip()

    league = _detect_league(prompt_lower)
    home, away = _extract_teams(prompt)
    goal = _detect_goal(prompt_lower)
    wants_betting = _detect_betting_intent(prompt_lower)
    tone = _detect_tone(prompt_lower)

    has_prop_signals = any(s in prompt_lower for s in SUBJECT_SIGNALS_PROP)
    has_slate_signals = any(s in prompt_lower for s in SUBJECT_SIGNALS_SLATE)
    has_bankroll_signals = any(s in prompt_lower for s in SUBJECT_SIGNALS_BANKROLL)

    subjects = _detect_subjects(
        prompt_lower, home, away, has_prop_signals,
        has_slate_signals, has_bankroll_signals, league,
    )

    # Build entities
    entities: List[Entity] = []
    if home:
        entities.append(Entity(name=home, role=EntityRole.HOME))
    if away:
        entities.append(Entity(name=away, role=EntityRole.AWAY))

    # Extract prop details
    prop_type, prop_line = None, None
    if has_prop_signals:
        prop_type, prop_line = _extract_prop_details(prompt_lower)

    # Detect explicit constraints
    constraints: List[str] = []
    if "no bet" in prompt_lower or "not looking for bet" in prompt_lower:
        constraints.append("no_bets")
        wants_betting = False
    if "just analysis" in prompt_lower or "just key factors" in prompt_lower:
        constraints.append("analysis_only")
        wants_betting = False

    wants_explanation = goal in (UserGoal.EXPLAIN, UserGoal.LEARN)
    wants_alternatives = "alternative" in prompt_lower or "other" in prompt_lower

    return QueryUnderstanding(
        subjects=subjects,
        league=league,
        entities=entities,
        markets=[],
        prop_type=prop_type,
        prop_line=prop_line,
        date=date.today().isoformat(),
        goal=goal,
        wants_betting_advice=wants_betting,
        wants_explanation=wants_explanation,
        wants_alternatives=wants_alternatives,
        tone=tone,
        explicit_constraints=constraints,
        raw_prompt=prompt,
    )


def understand(prompt: str, llm_available: bool = False) -> QueryUnderstanding:
    """Top-level entry point for intent understanding.

    Uses LLM function-calling when available, otherwise falls back to
    heuristic parsing. Both paths produce the same QueryUnderstanding type.

    Args:
        prompt: Raw user input string.
        llm_available: Whether an LLM is configured and reachable.

    Returns:
        QueryUnderstanding with all four dimensions classified.
    """
    if llm_available:
        # TODO: Implement LLM-based intent classification via function-calling.
        # The LLM receives the prompt + a tool schema matching QueryUnderstanding
        # fields, and returns a structured classification.
        # For now, fall through to heuristic.
        pass

    return parse_heuristic(prompt)
