"""Simulation modules: Monte Carlo and Markov play-by-play engines."""

from omega.simulation.simulation_engine import (
    select_distribution,
    run_game_simulation,
    simulate_totals,
    simulate_totals_auto,
    run_player_simulation
)
from omega.simulation.correlated_simulation import (
    get_allocation_rules,
    allocate_player_stats_from_team,
    simulate_team_outcomes,
    simulate_correlated_markets
)
from omega.simulation.markov_engine import (
    MarkovState,
    TransitionMatrix,
    MarkovSimulator,
    run_markov_player_prop_simulation
)

__all__ = [
    'select_distribution',
    'run_game_simulation',
    'simulate_totals',
    'simulate_totals_auto',
    'run_player_simulation',
    'get_allocation_rules',
    'allocate_player_stats_from_team',
    'simulate_team_outcomes',
    'simulate_correlated_markets',
    'MarkovState',
    'TransitionMatrix',
    'MarkovSimulator',
    'run_markov_player_prop_simulation'
]
