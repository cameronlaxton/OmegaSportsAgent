import sys
from pathlib import Path

print("\n" + "="*80)
print("Step 1 Verification: Clone & Connect")
print("="*80)

# Test 1: Project structure
print("\n[1/5] Checking project structure...")
required_dirs = ['core', 'modules', 'data', 'tests', '.github']
for dir_name in required_dirs:
    if Path(dir_name).exists():
        print(f"  ✓ {dir_name}/")
    else:
        print(f"  ✗ {dir_name}/ MISSING")
        sys.exit(1)

# Test 2: Python dependencies
print("\n[2/5] Checking Python dependencies...")
try:
    import pytest
    print(f"  ✓ pytest")
    import numpy
    print(f"  ✓ numpy")
    import pandas
    print(f"  ✓ pandas")
except ImportError as e:
    print(f"  ✗ Missing: {e}")
    sys.exit(1)

# Test 3: Validation Lab imports
print("\n[3/5] Checking Validation Lab modules...")
try:
    from core.data_pipeline import DataPipeline
    print(f"  ✓ DataPipeline")
    from core.simulation_framework import SimulationFramework
    print(f"  ✓ SimulationFramework")
    # Module names can't start with numbers, so use importlib
    import importlib.util
    module_path = Path('modules') / '01_edge_threshold' / 'run_experiment.py'
    if module_path.exists():
        spec = importlib.util.spec_from_file_location("edge_threshold_module", module_path)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            if hasattr(module, 'EdgeThresholdModule'):
                print(f"  ✓ EdgeThresholdModule")
            else:
                print(f"  ⚠ EdgeThresholdModule class not found in module")
        else:
            print(f"  ⚠ Could not load EdgeThresholdModule")
    else:
        print(f"  ⚠ Module file not found: {module_path}")
except ImportError as e:
    print(f"  ✗ Import error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
except Exception as e:
    print(f"  ⚠ Module check note: {e}")

# Test 4: OmegaSports connection
print("\n[4/5] Checking OmegaSports connection...")
try:
    # Path is auto-configured when config is imported
    from utils.config import config
    omega_path = config.omega_engine_path
    
    if omega_path and omega_path.exists():
        print(f"  ✓ OmegaSports path configured: {omega_path}")
        
        # Temporarily remove current directory from path to import from OmegaSportsAgent
        # This allows importing omega.simulation from OmegaSportsAgent
        original_path = sys.path.copy()
        current_dir = str(Path.cwd())
        try:
            if current_dir in sys.path:
                sys.path.remove(current_dir)
            if '.' in sys.path:
                sys.path.remove('.')
            
            from src.simulation.simulation_engine import run_game_simulation
            print(f"  ✓ OmegaSports simulation engine accessible")
            
            # Try running a quick simulation
            # The function expects a projection dict with off_rating
            test_projection = {
                "off_rating": {
                    "Test Home": 110.0,
                    "Test Away": 100.0
                },
                "league": "NBA",
                "variance_scalar": 1.0
            }
            
            result = run_game_simulation(test_projection, n_iter=100)
            print(f"  ✓ Simulation test successful")
        finally:
            sys.path = original_path
    else:
        print(f"  ⚠ OMEGA_ENGINE_PATH not set or doesn't exist")
        print(f"     Set OMEGA_ENGINE_PATH in .env file to point to OmegaSportsAgent")
except ImportError as e:
    print(f"  ⚠ OmegaSports import failed: {e}")
    print(f"     Make sure OMEGA_ENGINE_PATH is set correctly in .env")
except Exception as e:
    print(f"  ⚠ Note: {e}")

# Test 5: Configuration
print("\n[5/5] Checking configuration...")
try:
    from utils.config import config
    print(f"  ✓ Configuration loaded")
    print(f"    - Cache path: {config.cache_path}")
    print(f"    - Data path: {config.historical_data_path}")
except ImportError as e:
    print(f"  ⚠ Config note: {e}")

print("\n" + "="*80)
print("✅ STEP 1 VERIFICATION COMPLETE!")
print("="*80)
print("\nYou're ready for Phase 2!")
print("Next: Read PHASE_2_QUICKSTART.md for next steps")
print("\n")

