"""
Adapters Package

Adapter modules for integrating with external systems (OmegaSportsAgent).

Modules:
    - agent_outputs_adapter: Ingest OmegaSportsAgent JSON outputs
    - apply_calibration: Apply calibration packs to OmegaSportsAgent

Note: These are STUB implementations for future integration.
"""

from .agent_outputs_adapter import (
    AgentOutputsAdapter,
    AgentBetRecommendation,
    AgentOutputBatch
)

from .apply_calibration import (
    CalibrationApplicator,
    ParameterChange,
    PatchPlan
)

__all__ = [
    'AgentOutputsAdapter',
    'AgentBetRecommendation',
    'AgentOutputBatch',
    'CalibrationApplicator',
    'ParameterChange',
    'PatchPlan'
]
