"""
Entity Resolution Service — re-export shim.

The canonical implementation has moved to src/normalization/entity_resolver.py.
This module re-exports everything for backward compatibility.
"""

from src.normalization.entity_resolver import *  # noqa: F401,F403
