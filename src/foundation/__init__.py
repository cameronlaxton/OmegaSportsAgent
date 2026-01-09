"""Foundation modules: configuration and core abstractions."""

from src.foundation.model_config import (
    get_edge_thresholds,
    get_variance_scalars,
    get_blend_weights,
    get_confidence_tier_caps,
    get_simulation_params
)
from src.foundation.league_config import (
    get_league_config,
    get_periods,
    get_period_length,
    get_typical_possessions,
    get_scoring_rules,
    get_clock_rules,
    get_key_numbers,
    get_home_advantage
)
from src.foundation.core_abstractions import (
    Team, Player, Game, State,
    Possession, Drive, Inning, Shift,
    team_from_dict, player_from_dict, game_from_dict
)
