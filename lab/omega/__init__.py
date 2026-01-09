"""
Omega package compatibility layer for Validation Lab.

This package provides compatibility for omega.scraper_engine while allowing
other omega submodules (like omega.simulation) to be imported from OmegaSportsAgent.

This is a namespace package that allows both the local scraper_engine and
OmegaSportsAgent's omega modules to coexist.
"""

__version__ = "1.0.0"

import sys
from pathlib import Path

# Set up OmegaSports path if not already configured
def _setup_omega_path():
    """Ensure OmegaSports path is in sys.path."""
    try:
        from utils.config import config
        omega_path = config.omega_engine_path
        if omega_path and omega_path.exists():
            omega_path_str = str(omega_path)
            if omega_path_str not in sys.path:
                sys.path.append(omega_path_str)
    except Exception:
        # Try to get from environment directly
        import os
        omega_path = os.getenv("OMEGA_ENGINE_PATH")
        if omega_path:
            omega_path_obj = Path(omega_path)
            if omega_path_obj.exists():
                omega_path_str = str(omega_path_obj)
                if omega_path_str not in sys.path:
                    sys.path.append(omega_path_str)

# Auto-setup on import
_setup_omega_path()

# Make this a namespace package so OmegaSportsAgent's omega can contribute
# This allows omega.simulation to be imported from OmegaSportsAgent
__path__ = __import__('pkgutil').extend_path(__path__, __name__)

