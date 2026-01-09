"""
OmegaSports path configuration utility.

This module automatically configures sys.path to allow imports from OmegaSportsAgent
while preserving the local omega package for compatibility.
"""

import sys
from pathlib import Path
from typing import Optional


def setup_omega_path() -> Optional[Path]:
    """
    Set up sys.path to allow OmegaSports imports.
    
    This function:
    1. Adds OmegaSportsAgent path to sys.path (at the end, so local omega takes precedence)
    2. Returns the omega_path if configured, None otherwise
    
    Call this at the start of any script that needs to import from OmegaSports.
    
    Returns:
        Path to OmegaSportsAgent if configured, None otherwise
    """
    try:
        from utils.config import config
        omega_path = config.omega_engine_path
        
        if omega_path and omega_path.exists():
            omega_path_str = str(omega_path)
            # Add to end of path so local omega package is found first
            if omega_path_str not in sys.path:
                sys.path.append(omega_path_str)
            return omega_path
        else:
            return None
    except Exception:
        return None


def get_omega_import_path() -> Optional[Path]:
    """
    Get the path to OmegaSportsAgent for direct imports.
    
    Returns:
        Path to OmegaSportsAgent if configured, None otherwise
    """
    try:
        from utils.config import config
        omega_path = config.omega_engine_path
        return omega_path if omega_path and omega_path.exists() else None
    except Exception:
        return None


# Auto-setup on import
_OMEGA_PATH = setup_omega_path()

