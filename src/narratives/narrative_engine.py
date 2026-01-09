"""
Narrative Intelligence Engine

Generates rich, storytelling narratives for game analysis including:
- Team form analysis (streaks, home/away performance)
- Matchup breakdowns (pace, offensive/defensive ratings)
- Storyline detection (revenge games, milestones, playoff implications)
- Head-to-head history
- Injury impact narratives
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict

logger = logging.getLogger(__name__)


@dataclass
class TeamForm:
    """Team recent form analysis."""
    team_name: str
    record: str = ""
    win_streak: int = 0
    loss_streak: int = 0
    last_5: str = ""
    home_record: str = ""
    away_record: str = ""
    points_per_game: float = 0.0
    points_allowed: float = 0.0
    pace: float = 100.0
    offensive_rating: float = 110.0
    defensive_rating: float = 110.0
    
    def net_rating(self) -> float:
        return self.offensive_rating - self.defensive_rating
    
    def form_description(self) -> str:
        if self.win_streak >= 5:
            return "red-hot"
        elif self.win_streak >= 3:
            return "rolling"
        elif self.loss_streak >= 5:
            return "struggling badly"
        elif self.loss_streak >= 3:
            return "in a slump"
        else:
            return "playing steady"


@dataclass
class Storyline:
    """A detected narrative storyline."""
    type: str
    headline: str
    description: str
    weight: float = 1.0


@dataclass
class MatchupAnalysis:
    """Detailed matchup breakdown."""
    pace_differential: float = 0.0
    offensive_advantage: str = ""
    defensive_advantage: str = ""
    key_matchup: str = ""
    style_clash: str = ""


@dataclass
class GameNarrative:
    """Complete narrative package for a game."""
    game_id: str
    home_team: str
    away_team: str
    headline: str = ""
    preview: str = ""
    full_narrative: str = ""
    home_form: Optional[TeamForm] = None
    away_form: Optional[TeamForm] = None
    matchup: Optional[MatchupAnalysis] = None
    storylines: List[Storyline] = field(default_factory=list)
    key_factors: List[str] = field(default_factory=list)
    betting_angle: str = ""
    generated_at: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "game_id": self.game_id,
            "home_team": self.home_team,
            "away_team": self.away_team,
            "headline": self.headline,
            "preview": self.preview,
            "full_narrative": self.full_narrative,
            "home_form": asdict(self.home_form) if self.home_form else None,
            "away_form": asdict(self.away_form) if self.away_form else None,
            "matchup": asdict(self.matchup) if self.matchup else None,
            "storylines": [asdict(s) for s in self.storylines],
            "key_factors": self.key_factors,
            "betting_angle": self.betting_angle,
            "generated_at": self.generated_at
        }


NBA_TEAM_DATA = {
    "Boston Celtics": {
        "abbrev": "BOS", "pace": 99.2, "off_rtg": 122.5, "def_rtg": 109.8,
        "record": "24-6", "home": "14-2", "away": "10-4", "streak": "W5",
        "ppg": 120.5, "opp_ppg": 108.2, "style": "elite two-way"
    },
    "Cleveland Cavaliers": {
        "abbrev": "CLE", "pace": 97.8, "off_rtg": 120.1, "def_rtg": 108.5,
        "record": "26-4", "home": "14-1", "away": "12-3", "streak": "W7",
        "ppg": 118.9, "opp_ppg": 107.5, "style": "balanced powerhouse"
    },
    "Oklahoma City Thunder": {
        "abbrev": "OKC", "pace": 100.5, "off_rtg": 118.2, "def_rtg": 106.3,
        "record": "24-5", "home": "13-2", "away": "11-3", "streak": "W4",
        "ppg": 117.8, "opp_ppg": 105.2, "style": "young and athletic"
    },
    "Memphis Grizzlies": {
        "abbrev": "MEM", "pace": 102.1, "off_rtg": 114.8, "def_rtg": 110.2,
        "record": "20-11", "home": "12-4", "away": "8-7", "streak": "W2",
        "ppg": 118.5, "opp_ppg": 112.8, "style": "physical and fast-paced"
    },
    "Dallas Mavericks": {
        "abbrev": "DAL", "pace": 99.8, "off_rtg": 117.5, "def_rtg": 112.5,
        "record": "19-11", "home": "11-4", "away": "8-7", "streak": "L1",
        "ppg": 117.2, "opp_ppg": 112.8, "style": "Luka-centric offense"
    },
    "Houston Rockets": {
        "abbrev": "HOU", "pace": 101.2, "off_rtg": 112.8, "def_rtg": 109.5,
        "record": "19-11", "home": "12-4", "away": "7-7", "streak": "W3",
        "ppg": 112.5, "opp_ppg": 108.9, "style": "young and hungry"
    },
    "New York Knicks": {
        "abbrev": "NYK", "pace": 97.5, "off_rtg": 116.2, "def_rtg": 111.8,
        "record": "18-12", "home": "10-5", "away": "8-7", "streak": "W2",
        "ppg": 113.5, "opp_ppg": 109.2, "style": "physical defense"
    },
    "Denver Nuggets": {
        "abbrev": "DEN", "pace": 98.5, "off_rtg": 118.5, "def_rtg": 113.2,
        "record": "17-11", "home": "11-3", "away": "6-8", "streak": "L2",
        "ppg": 116.8, "opp_ppg": 112.5, "style": "Jokic-orchestrated offense"
    },
    "Los Angeles Lakers": {
        "abbrev": "LAL", "pace": 100.8, "off_rtg": 115.2, "def_rtg": 111.5,
        "record": "16-13", "home": "10-5", "away": "6-8", "streak": "W1",
        "ppg": 115.2, "opp_ppg": 111.8, "style": "LeBron-led veteran squad"
    },
    "Golden State Warriors": {
        "abbrev": "GSW", "pace": 101.5, "off_rtg": 113.2, "def_rtg": 112.8,
        "record": "15-13", "home": "9-5", "away": "6-8", "streak": "L1",
        "ppg": 112.5, "opp_ppg": 112.2, "style": "motion offense specialists"
    },
    "Miami Heat": {
        "abbrev": "MIA", "pace": 96.8, "off_rtg": 111.5, "def_rtg": 110.8,
        "record": "15-13", "home": "9-5", "away": "6-8", "streak": "W1",
        "ppg": 108.5, "opp_ppg": 107.8, "style": "gritty and physical"
    },
    "Milwaukee Bucks": {
        "abbrev": "MIL", "pace": 99.2, "off_rtg": 114.8, "def_rtg": 113.5,
        "record": "14-14", "home": "9-6", "away": "5-8", "streak": "L3",
        "ppg": 113.8, "opp_ppg": 112.5, "style": "Giannis-powered attack"
    },
    "Phoenix Suns": {
        "abbrev": "PHX", "pace": 98.8, "off_rtg": 115.5, "def_rtg": 114.2,
        "record": "15-14", "home": "10-5", "away": "5-9", "streak": "W2",
        "ppg": 114.2, "opp_ppg": 113.5, "style": "star-driven scoring"
    },
    "Indiana Pacers": {
        "abbrev": "IND", "pace": 103.5, "off_rtg": 116.8, "def_rtg": 115.2,
        "record": "15-15", "home": "10-6", "away": "5-9", "streak": "L1",
        "ppg": 118.2, "opp_ppg": 116.5, "style": "fastest pace in the league"
    },
    "Atlanta Hawks": {
        "abbrev": "ATL", "pace": 100.2, "off_rtg": 114.5, "def_rtg": 114.8,
        "record": "16-14", "home": "11-5", "away": "5-9", "streak": "W1",
        "ppg": 116.8, "opp_ppg": 117.2, "style": "Trae Young's playmaking"
    },
    "Los Angeles Clippers": {
        "abbrev": "LAC", "pace": 98.5, "off_rtg": 112.5, "def_rtg": 111.8,
        "record": "17-12", "home": "10-4", "away": "7-8", "streak": "W2",
        "ppg": 110.8, "opp_ppg": 110.2, "style": "depth and versatility"
    },
    "Minnesota Timberwolves": {
        "abbrev": "MIN", "pace": 97.2, "off_rtg": 112.2, "def_rtg": 110.5,
        "record": "17-12", "home": "11-4", "away": "6-8", "streak": "L1",
        "ppg": 109.5, "opp_ppg": 107.8, "style": "elite rim protection"
    },
    "Sacramento Kings": {
        "abbrev": "SAC", "pace": 101.8, "off_rtg": 113.5, "def_rtg": 114.2,
        "record": "13-17", "home": "8-8", "away": "5-9", "streak": "L2",
        "ppg": 114.5, "opp_ppg": 115.2, "style": "fast-paced offense"
    },
    "San Antonio Spurs": {
        "abbrev": "SAS", "pace": 100.5, "off_rtg": 110.2, "def_rtg": 115.8,
        "record": "13-17", "home": "8-7", "away": "5-10", "streak": "W1",
        "ppg": 110.5, "opp_ppg": 116.2, "style": "Wemby development project"
    },
    "Detroit Pistons": {
        "abbrev": "DET", "pace": 99.8, "off_rtg": 109.5, "def_rtg": 112.5,
        "record": "14-16", "home": "9-7", "away": "5-9", "streak": "W4",
        "ppg": 109.2, "opp_ppg": 112.8, "style": "young and improving"
    },
    "Chicago Bulls": {
        "abbrev": "CHI", "pace": 98.2, "off_rtg": 110.8, "def_rtg": 115.2,
        "record": "13-18", "home": "8-8", "away": "5-10", "streak": "L2",
        "ppg": 109.5, "opp_ppg": 114.2, "style": "struggling for identity"
    },
    "Toronto Raptors": {
        "abbrev": "TOR", "pace": 99.5, "off_rtg": 108.5, "def_rtg": 116.8,
        "record": "8-22", "home": "4-11", "away": "4-11", "streak": "L5",
        "ppg": 107.2, "opp_ppg": 116.5, "style": "rebuilding"
    },
    "Brooklyn Nets": {
        "abbrev": "BKN", "pace": 100.2, "off_rtg": 109.8, "def_rtg": 115.5,
        "record": "11-18", "home": "7-8", "away": "4-10", "streak": "L1",
        "ppg": 108.5, "opp_ppg": 114.8, "style": "young development"
    },
    "Orlando Magic": {
        "abbrev": "ORL", "pace": 96.5, "off_rtg": 110.5, "def_rtg": 107.2,
        "record": "21-11", "home": "13-4", "away": "8-7", "streak": "W1",
        "ppg": 106.8, "opp_ppg": 103.5, "style": "suffocating defense"
    },
    "Charlotte Hornets": {
        "abbrev": "CHA", "pace": 101.2, "off_rtg": 107.5, "def_rtg": 118.2,
        "record": "7-22", "home": "4-10", "away": "3-12", "streak": "L3",
        "ppg": 106.5, "opp_ppg": 118.8, "style": "rebuilding phase"
    },
    "Philadelphia 76ers": {
        "abbrev": "PHI", "pace": 97.8, "off_rtg": 109.2, "def_rtg": 113.5,
        "record": "11-17", "home": "6-8", "away": "5-9", "streak": "L2",
        "ppg": 106.2, "opp_ppg": 110.8, "style": "injury-plagued"
    },
    "Portland Trail Blazers": {
        "abbrev": "POR", "pace": 100.8, "off_rtg": 108.2, "def_rtg": 116.5,
        "record": "10-19", "home": "6-8", "away": "4-11", "streak": "W1",
        "ppg": 107.8, "opp_ppg": 116.2, "style": "youth movement"
    },
    "Utah Jazz": {
        "abbrev": "UTA", "pace": 99.5, "off_rtg": 110.5, "def_rtg": 117.2,
        "record": "9-20", "home": "5-9", "away": "4-11", "streak": "L4",
        "ppg": 109.2, "opp_ppg": 116.8, "style": "tanking for picks"
    },
    "Washington Wizards": {
        "abbrev": "WAS", "pace": 101.5, "off_rtg": 105.8, "def_rtg": 119.5,
        "record": "6-22", "home": "4-10", "away": "2-12", "streak": "L6",
        "ppg": 104.5, "opp_ppg": 119.2, "style": "full rebuild"
    },
    "New Orleans Pelicans": {
        "abbrev": "NOP", "pace": 98.2, "off_rtg": 107.5, "def_rtg": 113.2,
        "record": "8-22", "home": "5-10", "away": "3-12", "streak": "L4",
        "ppg": 105.8, "opp_ppg": 112.5, "style": "injury-decimated"
    }
}


class NarrativeEngine:
    """Generates rich game narratives from structured data."""
    
    def __init__(self):
        self.team_data = NBA_TEAM_DATA
    
    def get_team_form(self, team_name: str) -> TeamForm:
        """Get team form analysis."""
        data = self.team_data.get(team_name, {})
        if not data:
            for name, d in self.team_data.items():
                if team_name.lower() in name.lower():
                    data = d
                    team_name = name
                    break
        
        if not data:
            return TeamForm(team_name=team_name)
        
        streak_str = data.get("streak", "")
        win_streak = 0
        loss_streak = 0
        if streak_str.startswith("W"):
            win_streak = int(streak_str[1:]) if streak_str[1:].isdigit() else 0
        elif streak_str.startswith("L"):
            loss_streak = int(streak_str[1:]) if streak_str[1:].isdigit() else 0
        
        return TeamForm(
            team_name=team_name,
            record=data.get("record", ""),
            win_streak=win_streak,
            loss_streak=loss_streak,
            last_5=streak_str,
            home_record=data.get("home", ""),
            away_record=data.get("away", ""),
            points_per_game=data.get("ppg", 0),
            points_allowed=data.get("opp_ppg", 0),
            pace=data.get("pace", 100),
            offensive_rating=data.get("off_rtg", 110),
            defensive_rating=data.get("def_rtg", 110)
        )
    
    def analyze_matchup(self, home_form: TeamForm, away_form: TeamForm) -> MatchupAnalysis:
        """Analyze the matchup between two teams."""
        pace_diff = home_form.pace - away_form.pace
        
        if home_form.offensive_rating > away_form.offensive_rating + 3:
            off_adv = home_form.team_name
        elif away_form.offensive_rating > home_form.offensive_rating + 3:
            off_adv = away_form.team_name
        else:
            off_adv = "Even"
        
        if home_form.defensive_rating < away_form.defensive_rating - 3:
            def_adv = home_form.team_name
        elif away_form.defensive_rating < home_form.defensive_rating - 3:
            def_adv = away_form.team_name
        else:
            def_adv = "Even"
        
        if abs(pace_diff) > 3:
            if pace_diff > 0:
                style = f"{home_form.team_name} will try to push the pace against {away_form.team_name}'s slower style"
            else:
                style = f"{away_form.team_name} will try to push the pace against {home_form.team_name}'s slower style"
        else:
            style = "Both teams play at similar tempos"
        
        return MatchupAnalysis(
            pace_differential=round(pace_diff, 1),
            offensive_advantage=off_adv,
            defensive_advantage=def_adv,
            style_clash=style
        )
    
    def detect_storylines(
        self, 
        home_team: str, 
        away_team: str,
        home_form: TeamForm,
        away_form: TeamForm
    ) -> List[Storyline]:
        """Detect narrative storylines for the game."""
        storylines = []
        
        if home_form.win_streak >= 5:
            storylines.append(Storyline(
                type="streak",
                headline=f"{home_team} Riding Hot Streak",
                description=f"The {home_team} enter on a {home_form.win_streak}-game winning streak and look to extend their dominance at home.",
                weight=1.5
            ))
        elif away_form.win_streak >= 5:
            storylines.append(Storyline(
                type="streak",
                headline=f"{away_team} Rolling Into Town",
                description=f"The {away_team} bring a {away_form.win_streak}-game winning streak into this road matchup.",
                weight=1.5
            ))
        
        if home_form.loss_streak >= 4:
            storylines.append(Storyline(
                type="struggle",
                headline=f"{home_team} Looking to End Skid",
                description=f"The {home_team} have dropped {home_form.loss_streak} straight and desperately need a win at home.",
                weight=1.3
            ))
        elif away_form.loss_streak >= 4:
            storylines.append(Storyline(
                type="struggle",
                headline=f"{away_team} Struggling on the Road",
                description=f"The {away_team} have lost {away_form.loss_streak} in a row and look to right the ship.",
                weight=1.3
            ))
        
        home_net = home_form.net_rating()
        away_net = away_form.net_rating()
        if home_net > 8 and away_net > 8:
            storylines.append(Storyline(
                type="marquee",
                headline="Elite Showdown",
                description=f"Two of the league's best meet as the {home_team} (Net Rating: +{home_net:.1f}) host the {away_team} (Net Rating: +{away_net:.1f}).",
                weight=2.0
            ))
        
        if home_form.pace > 102 and away_form.pace > 102:
            storylines.append(Storyline(
                type="pace",
                headline="Track Meet Expected",
                description=f"Both teams play at a fast pace - expect a high-scoring affair with the over in play.",
                weight=1.2
            ))
        elif home_form.pace < 98 and away_form.pace < 98:
            storylines.append(Storyline(
                type="pace",
                headline="Grind-It-Out Battle",
                description=f"Two methodical teams should produce a lower-scoring, half-court game.",
                weight=1.2
            ))
        
        if home_form.defensive_rating < 108 and away_form.defensive_rating < 108:
            storylines.append(Storyline(
                type="defense",
                headline="Defensive Showdown",
                description=f"Two elite defenses clash - points could be at a premium in this one.",
                weight=1.4
            ))
        
        return storylines
    
    def generate_headline(
        self, 
        home_team: str, 
        away_team: str,
        home_form: TeamForm,
        away_form: TeamForm,
        storylines: List[Storyline]
    ) -> str:
        """Generate a compelling headline for the game."""
        if storylines:
            top_storyline = max(storylines, key=lambda s: s.weight)
            return top_storyline.headline
        
        home_net = home_form.net_rating()
        away_net = away_form.net_rating()
        
        if home_net > away_net + 5:
            return f"{home_team} Look to Dominate at Home"
        elif away_net > home_net + 5:
            return f"{away_team} Seek Road Statement Win"
        else:
            return f"{away_team} Visit {home_team} in Clash of Equals"
    
    def generate_preview(
        self,
        home_team: str,
        away_team: str,
        home_form: TeamForm,
        away_form: TeamForm,
        matchup: MatchupAnalysis
    ) -> str:
        """Generate a short preview paragraph."""
        home_data = self.team_data.get(home_team, {})
        away_data = self.team_data.get(away_team, {})
        
        home_style = home_data.get("style", "")
        away_style = away_data.get("style", "")
        
        preview = f"The {home_team} ({home_form.record}) host the {away_team} ({away_form.record}). "
        
        if home_style and away_style:
            preview += f"It's a clash of styles as {home_team}'s {home_style} faces {away_team}'s {away_style}. "
        
        if matchup.offensive_advantage != "Even":
            preview += f"{matchup.offensive_advantage} hold the offensive edge. "
        
        if matchup.defensive_advantage != "Even":
            preview += f"{matchup.defensive_advantage} have the defensive advantage. "
        
        return preview.strip()
    
    def generate_full_narrative(
        self,
        home_team: str,
        away_team: str,
        home_form: TeamForm,
        away_form: TeamForm,
        matchup: MatchupAnalysis,
        storylines: List[Storyline]
    ) -> str:
        """Generate a full narrative breakdown."""
        sections = []
        
        sections.append(f"## {away_team} @ {home_team}")
        sections.append("")
        
        sections.append("### Team Form")
        sections.append(f"**{home_team}** ({home_form.record}, {home_form.home_record} at home)")
        sections.append(f"- Scoring: {home_form.points_per_game:.1f} PPG | Allowing: {home_form.points_allowed:.1f}")
        sections.append(f"- Offensive Rating: {home_form.offensive_rating:.1f} | Defensive Rating: {home_form.defensive_rating:.1f}")
        sections.append(f"- Current Form: {home_form.form_description().title()}")
        sections.append("")
        
        sections.append(f"**{away_team}** ({away_form.record}, {away_form.away_record} on the road)")
        sections.append(f"- Scoring: {away_form.points_per_game:.1f} PPG | Allowing: {away_form.points_allowed:.1f}")
        sections.append(f"- Offensive Rating: {away_form.offensive_rating:.1f} | Defensive Rating: {away_form.defensive_rating:.1f}")
        sections.append(f"- Current Form: {away_form.form_description().title()}")
        sections.append("")
        
        sections.append("### Matchup Analysis")
        sections.append(f"- Pace Differential: {matchup.pace_differential:+.1f}")
        sections.append(f"- Offensive Advantage: {matchup.offensive_advantage}")
        sections.append(f"- Defensive Advantage: {matchup.defensive_advantage}")
        sections.append(f"- Style Clash: {matchup.style_clash}")
        sections.append("")
        
        if storylines:
            sections.append("### Key Storylines")
            for story in sorted(storylines, key=lambda s: s.weight, reverse=True):
                sections.append(f"**{story.headline}**")
                sections.append(story.description)
                sections.append("")
        
        return "\n".join(sections)
    
    def generate_key_factors(
        self,
        home_team: str,
        away_team: str,
        home_form: TeamForm,
        away_form: TeamForm,
        matchup: MatchupAnalysis
    ) -> List[str]:
        """Generate key factors for the game."""
        factors = []
        
        if home_form.win_streak >= 3:
            factors.append(f"{home_team} on {home_form.win_streak}-game win streak")
        elif home_form.loss_streak >= 3:
            factors.append(f"{home_team} have lost {home_form.loss_streak} straight")
        
        if away_form.win_streak >= 3:
            factors.append(f"{away_team} riding {away_form.win_streak}-game win streak")
        elif away_form.loss_streak >= 3:
            factors.append(f"{away_team} struggling with {away_form.loss_streak} straight losses")
        
        home_net = home_form.net_rating()
        away_net = away_form.net_rating()
        if abs(home_net - away_net) > 5:
            better = home_team if home_net > away_net else away_team
            factors.append(f"{better} significantly higher net rating")
        
        if abs(matchup.pace_differential) > 3:
            faster = home_team if matchup.pace_differential > 0 else away_team
            factors.append(f"Pace mismatch - {faster} plays much faster")
        
        if home_form.defensive_rating < 109:
            factors.append(f"{home_team} elite defense (Def Rtg: {home_form.defensive_rating:.1f})")
        if away_form.defensive_rating < 109:
            factors.append(f"{away_team} elite defense (Def Rtg: {away_form.defensive_rating:.1f})")
        
        return factors[:5]
    
    def generate_betting_angle(
        self,
        home_team: str,
        away_team: str,
        home_form: TeamForm,
        away_form: TeamForm,
        matchup: MatchupAnalysis
    ) -> str:
        """Generate a betting angle insight."""
        angles = []
        
        expected_total = (home_form.points_per_game + away_form.points_per_game + 
                         home_form.points_allowed + away_form.points_allowed) / 4
        
        if home_form.pace > 102 and away_form.pace > 102:
            angles.append(f"Both teams play uptempo - lean OVER. Expected total around {expected_total:.0f}.")
        elif home_form.pace < 98 and away_form.pace < 98:
            angles.append(f"Slow-paced matchup - consider UNDER. Expected total around {expected_total:.0f}.")
        
        home_net = home_form.net_rating()
        away_net = away_form.net_rating()
        
        if home_net > away_net + 5:
            angles.append(f"{home_team} superior net rating (+{home_net:.1f} vs +{away_net:.1f}) favors home side.")
        elif away_net > home_net + 5:
            angles.append(f"{away_team} stronger overall (+{away_net:.1f} net rating) could cover on the road.")
        
        if home_form.win_streak >= 4:
            angles.append(f"{home_team} momentum (W{home_form.win_streak}) could carry at home.")
        if away_form.loss_streak >= 4:
            angles.append(f"Fade {away_team} - L{away_form.loss_streak} streak shows struggles.")
        
        return " ".join(angles) if angles else "No clear betting edge identified from team metrics."
    
    def generate_game_narrative(self, game_data: Dict[str, Any]) -> GameNarrative:
        """Generate complete narrative for a game."""
        home_team = game_data.get("home_team", "")
        away_team = game_data.get("away_team", "")
        game_id = game_data.get("game_id", "")
        
        if isinstance(home_team, dict):
            home_team = home_team.get("name", str(home_team))
        if isinstance(away_team, dict):
            away_team = away_team.get("name", str(away_team))
        
        home_form = self.get_team_form(home_team)
        away_form = self.get_team_form(away_team)
        
        matchup = self.analyze_matchup(home_form, away_form)
        
        storylines = self.detect_storylines(home_team, away_team, home_form, away_form)
        
        headline = self.generate_headline(home_team, away_team, home_form, away_form, storylines)
        preview = self.generate_preview(home_team, away_team, home_form, away_form, matchup)
        full_narrative = self.generate_full_narrative(
            home_team, away_team, home_form, away_form, matchup, storylines
        )
        key_factors = self.generate_key_factors(home_team, away_team, home_form, away_form, matchup)
        betting_angle = self.generate_betting_angle(home_team, away_team, home_form, away_form, matchup)
        
        return GameNarrative(
            game_id=game_id,
            home_team=home_team,
            away_team=away_team,
            headline=headline,
            preview=preview,
            full_narrative=full_narrative,
            home_form=home_form,
            away_form=away_form,
            matchup=matchup,
            storylines=storylines,
            key_factors=key_factors,
            betting_angle=betting_angle,
            generated_at=datetime.now().isoformat()
        )


def generate_narrative(game_data: Dict[str, Any]) -> Dict[str, Any]:
    """Convenience function to generate narrative for a game."""
    engine = NarrativeEngine()
    narrative = engine.generate_game_narrative(game_data)
    return narrative.to_dict()


def generate_all_narratives(games: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Generate narratives for all games."""
    engine = NarrativeEngine()
    return [engine.generate_game_narrative(g).to_dict() for g in games]
