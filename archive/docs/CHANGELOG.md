# Changelog

All notable changes to the OMEGA Sports Betting Simulation project will be documented in this file.

## [Unreleased]

### Added
- **GitHub Integration**: Organized repository structure with modules/, config/, docs/, data/, examples/ directories
- **Swappable Storage Backend**: `OmegaCacheLogger` now supports configurable paths (default: `data/logs/` and `data/exports/`)
- **MODULE_LOAD_ORDER.md**: Quick reference for module loading order
- **docs/SETUP.md**: Comprehensive GitHub setup and Perplexity Space integration guide
- **config/AGENT_SPACE_INSTRUCTIONS.md**: Perplexity Space configuration instructions
- **.github/workflows/validate-modules.yml**: CI workflow for module validation
- **Three-layer persistence strategy**: Session storage → Space attachments → GitHub commits

### Changed
- **Directory Structure**: Reorganized all modules into logical subdirectories (foundation/, analytics/, modeling/, simulation/, betting/, adjustments/, utilities/)
- **Module Paths**: Updated all module references to use new directory structure (e.g., `modules/foundation/model_config.md`)
- **Storage Defaults**: Changed default storage paths from `/tmp/omega_storage/` to `data/logs/` and `data/exports/`
- **OmegaCacheLogger**: Refactored to accept swappable `base_path` and `exports_path` parameters
- **Documentation**: Updated all documentation files with new paths and GitHub integration info

### Removed
- **Cache Functions**: Removed `cache_data()`, `load_cached_data()`, and `get_cache_directory()` from `data_logging.md`
- **Cache References**: Removed all cache directory references from documentation
- **Redundant Files**: Removed `MasterInstructions.md` and `WorkflowInstructions.md` (merged into `CombinedInstructions.md`)
- **init_persistence.md**: Removed (functionality integrated into `sandbox_persistence.md`)

### Fixed
- **Path References**: All module cross-references now use correct paths
- **Storage Strategy**: Clarified three-layer persistence (session → attachments → GitHub)
- **Documentation**: Updated all file paths and references to match new structure

## File Organization

### Moved Files
- All module files moved to `modules/` subdirectories
- `CombinedInstructions.md` → `config/CombinedInstructions.md`
- `ARCHITECTURE.md` → `docs/ARCHITECTURE.md`
- `bet_log_template.md` → `docs/bet_log_template.md`
- `BetLog.csv` → `examples/BetLog.csv`

### Created Files
- `.gitignore` - Git ignore rules for generated data files
- `MODULE_LOAD_ORDER.md` - Module loading reference
- `docs/SETUP.md` - Setup guide
- `config/AGENT_SPACE_INSTRUCTIONS.md` - Space configuration
- `.github/workflows/validate-modules.yml` - CI workflow
- `data/.gitkeep`, `data/logs/.gitkeep`, `data/exports/.gitkeep`, `data/audits/.gitkeep` - Preserve directory structure

