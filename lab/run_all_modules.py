#!/usr/bin/env python
"""
Main runner script to execute all experimental modules.

Usage:
    python run_all_modules.py
    python run_all_modules.py --module 01  # Run specific module
"""

import logging
import sys
import importlib
import argparse
from pathlib import Path
from typing import List, Dict, Any

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def discover_modules(modules_dir: Path) -> List[Dict[str, Any]]:
    """
    Discover available experiment modules.
    
    Args:
        modules_dir: Path to modules directory
        
    Returns:
        List of module info dictionaries
    """
    modules = []
    
    # Look for numbered module directories with run_experiment.py
    for module_path in sorted(modules_dir.iterdir()):
        if not module_path.is_dir():
            continue
        
        # Check for module number pattern (e.g., 01_edge_threshold)
        if not module_path.name[0].isdigit():
            continue
        
        run_script = module_path / "run_experiment.py"
        if not run_script.exists():
            logger.warning(f"Module {module_path.name} missing run_experiment.py, skipping")
            continue
        
        # Extract module number and name
        parts = module_path.name.split("_", 1)
        module_num = parts[0]
        module_name = parts[1] if len(parts) > 1 else module_path.name
        
        modules.append({
            "number": module_num,
            "name": module_name,
            "path": module_path,
            "script": run_script
        })
        
        logger.info(f"Discovered Module {module_num}: {module_name}")
    
    return modules


def run_module(module_info: Dict[str, Any]) -> bool:
    """
    Run a single experiment module.
    
    Args:
        module_info: Module information dictionary
        
    Returns:
        True if successful, False otherwise
    """
    module_num = module_info["number"]
    module_name = module_info["name"]
    script_path = module_info["script"]
    
    logger.info("\n" + "="*80)
    logger.info(f"Executing Module {module_num}: {module_name}")
    logger.info("="*80)
    
    try:
        # Load module directly from file path (avoids numeric module name issues)
        import importlib.util
        
        spec = importlib.util.spec_from_file_location("module_runner", script_path)
        if spec is None or spec.loader is None:
            logger.error(f"✗ Module {module_num} could not be loaded")
            return False
        
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Run the main function
        if hasattr(module, "main"):
            result = module.main()
            if result == 0:
                logger.info(f"✓ Module {module_num} completed successfully")
                return True
            else:
                logger.error(f"✗ Module {module_num} failed with code {result}")
                return False
        else:
            logger.error(f"✗ Module {module_num} missing main() function")
            return False
            
    except Exception as e:
        logger.error(f"✗ Module {module_num} failed with exception: {e}")
        logger.exception("Full traceback:")
        return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run OmegaSports Validation Lab experiment modules"
    )
    parser.add_argument(
        "--module",
        type=str,
        help="Run specific module by number (e.g., '01' or '02')"
    )
    parser.add_argument(
        "--skip-errors",
        action="store_true",
        help="Continue execution even if a module fails"
    )
    
    args = parser.parse_args()
    
    logger.info("\n" + "="*80)
    logger.info("OmegaSports Validation Lab - Module Execution")
    logger.info("="*80)

    project_root = Path(__file__).parent
    modules_dir = project_root / "modules"

    if not modules_dir.exists():
        logger.error(f"Modules directory not found: {modules_dir}")
        logger.info("Please ensure all module directories are created.")
        return 1

    # Discover available modules
    logger.info("\nDiscovering available modules...")
    modules = discover_modules(modules_dir)
    
    if not modules:
        logger.warning("No executable modules found")
        logger.info("Modules should have format: NN_name/run_experiment.py")
        return 1
    
    # Filter to specific module if requested
    if args.module:
        modules = [m for m in modules if m["number"] == args.module]
        if not modules:
            logger.error(f"Module {args.module} not found")
            return 1
    
    # Execute modules
    logger.info(f"\nExecuting {len(modules)} module(s)...\n")
    
    results = []
    for module_info in modules:
        success = run_module(module_info)
        results.append({
            "module": module_info["number"],
            "name": module_info["name"],
            "success": success
        })
        
        if not success and not args.skip_errors:
            logger.error("Stopping execution due to module failure")
            break
    
    # Summary
    logger.info("\n" + "="*80)
    logger.info("Execution Summary")
    logger.info("="*80)
    
    for result in results:
        status = "✓ SUCCESS" if result["success"] else "✗ FAILED"
        logger.info(f"Module {result['module']}: {status} - {result['name']}")
    
    successful = sum(1 for r in results if r["success"])
    total = len(results)
    
    logger.info(f"\nTotal: {successful}/{total} modules completed successfully")
    logger.info("="*80)
    
    return 0 if successful == total else 1


if __name__ == "__main__":
    sys.exit(main())
