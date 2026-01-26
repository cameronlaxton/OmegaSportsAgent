"""
Entity Resolution Service

Maps messy scraper names ("G. Antetokounmpo", "L. James") to canonical UUIDs.
Uses a multi-tier resolution strategy:
1. Exact match on canonical name
2. Exact match on aliases JSONB
3. Fuzzy match (Levenshtein distance)
4. Log warning if low confidence

This is the "Rosetta Stone" that prevents duplicate entities across data sources.
"""

import logging
from typing import Optional
from dataclasses import dataclass
from difflib import SequenceMatcher

from sqlalchemy import select, func, and_
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


@dataclass
class ResolvedEntity:
    """Result of entity resolution."""
    canonical_id: str
    canonical_name: str
    match_type: str  # "exact", "alias", "canonical", "fuzzy", "fuzzy_alias"
    confidence: float  # 0.0 - 1.0
    source_alias: str  # The original scraped name


class EntityResolver:
    """
    Resolves scraped entity names to canonical database UUIDs.

    Resolution Priority:
    1. Exact name match -> confidence 1.0
    2. Exact alias match -> confidence 1.0
    3. Fuzzy name match (>0.85 similarity) -> confidence = similarity
    4. Fuzzy alias match (>0.85 similarity) -> confidence = similarity * 0.95
    5. No match -> returns None, logs warning

    Usage:
        resolver = EntityResolver(session)
        player_id = resolver.resolve_player("G. Antetokounmpo", team="MIL", sport="NBA")
    """

    # Minimum similarity threshold for fuzzy matching
    FUZZY_THRESHOLD = 0.85

    # Penalty applied to alias fuzzy matches (slightly less confident)
    ALIAS_FUZZY_PENALTY = 0.95

    def __init__(self, session: Session):
        self.session = session

    def _calculate_similarity(self, name1: str, name2: str) -> float:
        """Calculate Levenshtein-based similarity ratio between two names."""
        # Normalize: lowercase, strip whitespace
        n1 = name1.lower().strip()
        n2 = name2.lower().strip()
        return SequenceMatcher(None, n1, n2).ratio()

    def _normalize_name(self, name: str) -> str:
        """Normalize a name for comparison."""
        return name.lower().strip()

    def resolve_player(
        self,
        name: str,
        team: Optional[str] = None,
        sport: Optional[str] = None
    ) -> Optional[str]:
        """
        Resolve a scraped player name to a canonical UUID.

        Args:
            name: The scraped player name (e.g., "G. Antetokounmpo")
            team: Optional team abbreviation to narrow search (e.g., "MIL")
            sport: Optional sport to narrow search (e.g., "NBA")

        Returns:
            The canonical player UUID, or None if no match found.
        """
        result = self._resolve_player_full(name, team, sport)
        if result:
            return result.canonical_id
        return None

    def _resolve_player_full(
        self,
        name: str,
        team: Optional[str] = None,
        sport: Optional[str] = None
    ) -> Optional[ResolvedEntity]:
        """
        Full resolution with match details.

        Returns ResolvedEntity with match type and confidence.
        """
        # Import here to avoid circular imports
        from src.db.schema import Player, Team, CanonicalName

        normalized_name = self._normalize_name(name)

        # Build base query with optional team/sport filters
        # Use single join to avoid duplicate join errors
        query = select(Player)

        if team or sport:
            query = query.join(Team)
            filters = []
            if team:
                filters.append(func.lower(Team.abbrev) == team.lower())
            if sport:
                filters.append(func.lower(Team.league_id) == sport.lower())
            if filters:
                query = query.where(and_(*filters))

        players = self.session.execute(query).scalars().all()

        # --- TIER 1: Exact name match ---
        for player in players:
            if self._normalize_name(player.name) == normalized_name:
                logger.debug(f"Exact match: '{name}' -> {player.id}")
                return ResolvedEntity(
                    canonical_id=player.id,
                    canonical_name=player.name,
                    match_type="exact",
                    confidence=1.0,
                    source_alias=name
                )

        # --- TIER 2: Exact alias match ---
        for player in players:
            aliases = player.aliases or []
            for alias in aliases:
                if self._normalize_name(alias) == normalized_name:
                    logger.debug(f"Alias match: '{name}' -> {player.id} (alias: {alias})")
                    return ResolvedEntity(
                        canonical_id=player.id,
                        canonical_name=player.name,
                        match_type="alias",
                        confidence=1.0,
                        source_alias=name
                    )

        # --- TIER 3: Check canonical_names table ---
        # Use scalars().first() to avoid MultipleResultsFound, order by confidence desc
        canonical_query = (
            select(CanonicalName)
            .where(
                CanonicalName.entity_type == "player",
                func.lower(CanonicalName.alias) == normalized_name
            )
            .order_by(CanonicalName.confidence.desc())
        )
        canonical_match = self.session.execute(canonical_query).scalars().first()
        if canonical_match:
            logger.debug(f"Canonical name match: '{name}' -> {canonical_match.canonical_id}")
            return ResolvedEntity(
                canonical_id=canonical_match.canonical_id,
                canonical_name=name,  # We don't have the canonical name here
                match_type="canonical",
                confidence=canonical_match.confidence,
                source_alias=name
            )

        # --- TIER 4: Fuzzy name match ---
        best_match = None
        best_similarity = 0.0

        for player in players:
            similarity = self._calculate_similarity(name, player.name)
            if similarity > best_similarity and similarity >= self.FUZZY_THRESHOLD:
                best_similarity = similarity
                best_match = ResolvedEntity(
                    canonical_id=player.id,
                    canonical_name=player.name,
                    match_type="fuzzy",
                    confidence=similarity,
                    source_alias=name
                )

        if best_match:
            logger.info(
                f"Fuzzy match: '{name}' -> {best_match.canonical_id} "
                f"(confidence: {best_match.confidence:.2f})"
            )
            return best_match

        # --- TIER 5: Fuzzy alias match ---
        for player in players:
            aliases = player.aliases or []
            for alias in aliases:
                similarity = self._calculate_similarity(name, alias)
                adjusted_similarity = similarity * self.ALIAS_FUZZY_PENALTY
                if adjusted_similarity > best_similarity and similarity >= self.FUZZY_THRESHOLD:
                    best_similarity = adjusted_similarity
                    best_match = ResolvedEntity(
                        canonical_id=player.id,
                        canonical_name=player.name,
                        match_type="fuzzy_alias",
                        confidence=adjusted_similarity,
                        source_alias=name
                    )

        if best_match:
            logger.info(
                f"Fuzzy alias match: '{name}' -> {best_match.canonical_id} "
                f"(confidence: {best_match.confidence:.2f})"
            )
            return best_match

        # --- NO MATCH ---
        logger.warning(
            f"Entity resolution failed: '{name}' "
            f"(team={team}, sport={sport}) - no match found"
        )
        return None

    def resolve_team(
        self,
        name: str,
        sport: Optional[str] = None
    ) -> Optional[str]:
        """
        Resolve a scraped team name to a canonical UUID.

        Args:
            name: The scraped team name (e.g., "LA Lakers", "Lakers")
            sport: Optional sport to narrow search (e.g., "NBA")

        Returns:
            The canonical team UUID, or None if no match found.
        """
        from src.db.schema import Team

        normalized_name = self._normalize_name(name)

        # Build query
        query = select(Team)
        if sport:
            query = query.where(func.lower(Team.league_id) == sport.lower())

        teams = self.session.execute(query).scalars().all()

        # --- TIER 1: Exact full_name match ---
        for team in teams:
            if self._normalize_name(team.full_name) == normalized_name:
                return team.id

        # --- TIER 2: Exact abbreviation match ---
        for team in teams:
            if team.abbrev and self._normalize_name(team.abbrev) == normalized_name:
                return team.id

        # --- TIER 3: Exact alias match ---
        for team in teams:
            aliases = team.aliases or []
            for alias in aliases:
                if self._normalize_name(alias) == normalized_name:
                    return team.id

        # --- TIER 4: Fuzzy match ---
        best_match_id = None
        best_similarity = 0.0

        for team in teams:
            # Check full name
            similarity = self._calculate_similarity(name, team.full_name)
            if similarity > best_similarity and similarity >= self.FUZZY_THRESHOLD:
                best_similarity = similarity
                best_match_id = team.id

            # Check aliases
            for alias in (team.aliases or []):
                similarity = self._calculate_similarity(name, alias)
                if similarity > best_similarity and similarity >= self.FUZZY_THRESHOLD:
                    best_similarity = similarity
                    best_match_id = team.id

        if best_match_id:
            logger.info(f"Fuzzy team match: '{name}' -> {best_match_id} (confidence: {best_similarity:.2f})")
            return best_match_id

        logger.warning(f"Team resolution failed: '{name}' (sport={sport}) - no match found")
        return None

    def add_alias(
        self,
        entity_type: str,
        canonical_id: str,
        alias: str,
        source: str = "auto",
        confidence: float = 1.0
    ) -> None:
        """
        Register a new alias for an entity.

        Args:
            entity_type: "player" or "team"
            canonical_id: The canonical UUID
            alias: The new alias to register
            source: Where this alias came from (e.g., "espn", "balldontlie")
            confidence: Confidence score (1.0 = exact, <1.0 = fuzzy)
        """
        from src.db.schema import CanonicalName

        # Normalize alias for case-insensitive matching
        normalized_alias = alias.lower().strip()

        # Check if alias already exists (case-insensitive)
        # Use scalars().first() to avoid MultipleResultsFound
        existing = self.session.execute(
            select(CanonicalName)
            .where(
                CanonicalName.entity_type == entity_type,
                func.lower(CanonicalName.alias) == normalized_alias
            )
            .order_by(CanonicalName.confidence.desc())
        ).scalars().first()

        if existing:
            # Update confidence if higher
            if confidence > existing.confidence:
                existing.confidence = confidence
                existing.source = source
                logger.info(f"Updated alias confidence: '{alias}' -> {canonical_id} ({confidence})")
        else:
            # Create new mapping
            new_mapping = CanonicalName(
                entity_type=entity_type,
                canonical_id=canonical_id,
                alias=alias,
                source=source,
                confidence=confidence
            )
            self.session.add(new_mapping)
            logger.info(f"Added new alias: '{alias}' -> {canonical_id} (source: {source})")

        self.session.commit()


# --- CONVENIENCE FUNCTIONS ---

def resolve_player(name: str, team: str, sport: str, session: Session) -> Optional[str]:
    """
    Convenience function to resolve a player name.

    Args:
        name: Scraped player name
        team: Team abbreviation
        sport: Sport code ("NBA", "NFL", etc.)
        session: SQLAlchemy session

    Returns:
        Canonical player UUID or None
    """
    resolver = EntityResolver(session)
    return resolver.resolve_player(name, team=team, sport=sport)


def resolve_team(name: str, sport: str, session: Session) -> Optional[str]:
    """
    Convenience function to resolve a team name.

    Args:
        name: Scraped team name
        sport: Sport code ("NBA", "NFL", etc.)
        session: SQLAlchemy session

    Returns:
        Canonical team UUID or None
    """
    resolver = EntityResolver(session)
    return resolver.resolve_team(name, sport=sport)
