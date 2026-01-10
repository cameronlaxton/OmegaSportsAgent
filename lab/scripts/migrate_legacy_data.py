#!/usr/bin/env python3
"""
Legacy Data Migration Script

Migrates bet logs, predictions, and reports from legacy locations to canonical paths:
- data/exports/BetLog.csv → data/exports/BetLog.csv (consolidate duplicates)
- outputs/recommendations_*.json → outputs/recommendations_*.json (keep, already canonical)
- data/logs/predictions.json → data/logs/predictions.json (consolidate duplicates)
- data/config/tuned_parameters.json → config/calibration/ (merge into calibration pack if needed)
- data/outputs/ → outputs/ (move all files)
- outputs/ (old scattered files) → outputs/ (consolidate)

This script should be run once after the monorepo refactor to clean up legacy paths.
"""

import json
import csv
import shutil
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


class LegacyDataMigrator:
    """Migrates legacy data files to canonical locations."""
    
    def __init__(self, repo_root: Optional[Path] = None):
        self.repo_root = repo_root or Path(__file__).resolve().parents[2]
        self.data_dir = self.repo_root / "data"
        self.outputs_dir = self.repo_root / "outputs"
        self.config_dir = self.repo_root / "config"
        self.calibration_dir = self.config_dir / "calibration"
        
    def migrate_bet_logs(self) -> bool:
        """Consolidate BetLog CSV files from multiple locations."""
        logger.info("Migrating bet logs...")
        
        legacy_paths = [
            self.data_dir / "exports" / "BetLog.csv",
            self.data_dir / "exports" / "betlog_*.csv",  # Pattern
            self.outputs_dir / "BetLog.csv",  # If exists
        ]
        
        canonical_path = self.data_dir / "exports" / "BetLog.csv"
        canonical_path.parent.mkdir(parents=True, exist_ok=True)
        
        all_rows = []
        seen_ids = set()
        
        # Collect all rows from legacy files
        for pattern in legacy_paths:
            if "*" in str(pattern):
                # Handle glob patterns
                for file_path in self.repo_root.glob(str(pattern.relative_to(self.repo_root))):
                    if file_path.exists() and file_path != canonical_path:
                        rows = self._read_csv_rows(file_path)
                        for row in rows:
                            bet_id = row.get("bet_id") or f"{row.get('date', '')}_{row.get('matchup', '')}"
                            if bet_id not in seen_ids:
                                all_rows.append(row)
                                seen_ids.add(bet_id)
            else:
                if pattern.exists() and pattern != canonical_path:
                    rows = self._read_csv_rows(pattern)
                    for row in rows:
                        bet_id = row.get("bet_id") or f"{row.get('date', '')}_{row.get('matchup', '')}"
                        if bet_id not in seen_ids:
                            all_rows.append(row)
                            seen_ids.add(bet_id)
        
        # Merge with existing canonical file if it exists
        if canonical_path.exists():
            existing_rows = self._read_csv_rows(canonical_path)
            for row in existing_rows:
                bet_id = row.get("bet_id") or f"{row.get('date', '')}_{row.get('matchup', '')}"
                if bet_id not in seen_ids:
                    all_rows.append(row)
                    seen_ids.add(bet_id)
        
        # Write consolidated file
        if all_rows:
            fieldnames = list(all_rows[0].keys()) if all_rows else []
            with open(canonical_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(all_rows)
            logger.info(f"  ✓ Consolidated {len(all_rows)} rows to {canonical_path}")
            return True
        else:
            logger.info("  ℹ No bet log data to migrate")
            return False
    
    def migrate_predictions(self) -> bool:
        """Consolidate predictions JSON files."""
        logger.info("Migrating predictions...")
        
        legacy_paths = [
            self.data_dir / "logs" / "predictions.json",
            self.data_dir / "logs" / "predictions_*.json",  # Pattern
            self.outputs_dir / "predictions.json",  # If exists
        ]
        
        canonical_path = self.data_dir / "logs" / "predictions.json"
        canonical_path.parent.mkdir(parents=True, exist_ok=True)
        
        all_predictions = []
        seen_keys = set()
        
        # Collect all predictions from legacy files
        for pattern in legacy_paths:
            if "*" in str(pattern):
                for file_path in self.repo_root.glob(str(pattern.relative_to(self.repo_root))):
                    if file_path.exists() and file_path != canonical_path:
                        preds = self._read_json(file_path)
                        if isinstance(preds, list):
                            for pred in preds:
                                key = self._prediction_key(pred)
                                if key not in seen_keys:
                                    all_predictions.append(pred)
                                    seen_keys.add(key)
                        elif isinstance(preds, dict):
                            key = self._prediction_key(preds)
                            if key not in seen_keys:
                                all_predictions.append(preds)
                                seen_keys.add(key)
            else:
                if pattern.exists() and pattern != canonical_path:
                    preds = self._read_json(pattern)
                    if isinstance(preds, list):
                        for pred in preds:
                            key = self._prediction_key(pred)
                            if key not in seen_keys:
                                all_predictions.append(pred)
                                seen_keys.add(key)
                    elif isinstance(preds, dict):
                        key = self._prediction_key(preds)
                        if key not in seen_keys:
                            all_predictions.append(preds)
                            seen_keys.add(key)
        
        # Merge with existing canonical file
        if canonical_path.exists():
            existing = self._read_json(canonical_path)
            if isinstance(existing, list):
                for pred in existing:
                    key = self._prediction_key(pred)
                    if key not in seen_keys:
                        all_predictions.append(pred)
                        seen_keys.add(key)
            elif isinstance(existing, dict):
                key = self._prediction_key(existing)
                if key not in seen_keys:
                    all_predictions.append(existing)
                    seen_keys.add(key)
        
        # Write consolidated file
        if all_predictions:
            with open(canonical_path, 'w', encoding='utf-8') as f:
                json.dump(all_predictions, f, indent=2, default=str)
            logger.info(f"  ✓ Consolidated {len(all_predictions)} predictions to {canonical_path}")
            return True
        else:
            logger.info("  ℹ No predictions data to migrate")
            return False
    
    def migrate_outputs(self) -> bool:
        """Move files from data/outputs/ to outputs/."""
        logger.info("Migrating output files...")
        
        legacy_outputs_dir = self.data_dir / "outputs"
        if not legacy_outputs_dir.exists():
            logger.info("  ℹ No legacy outputs directory found")
            return False
        
        self.outputs_dir.mkdir(parents=True, exist_ok=True)
        moved_count = 0
        
        for file_path in legacy_outputs_dir.iterdir():
            if file_path.is_file():
                dest = self.outputs_dir / file_path.name
                # Handle name conflicts
                if dest.exists():
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    stem = file_path.stem
                    suffix = file_path.suffix
                    dest = self.outputs_dir / f"{stem}_migrated_{timestamp}{suffix}"
                shutil.move(str(file_path), str(dest))
                moved_count += 1
        
        if moved_count > 0:
            logger.info(f"  ✓ Moved {moved_count} files from {legacy_outputs_dir} to {self.outputs_dir}")
            # Remove empty directory
            try:
                legacy_outputs_dir.rmdir()
            except OSError:
                pass
            return True
        else:
            return False
    
    def migrate_tuned_parameters(self) -> bool:
        """Move tuned_parameters.json to calibration directory (for reference)."""
        logger.info("Migrating tuned parameters...")
        
        legacy_path = self.data_dir / "config" / "tuned_parameters.json"
        if not legacy_path.exists():
            logger.info("  ℹ No tuned_parameters.json found")
            return False
        
        # Keep as reference, don't merge into calibration pack (Lab generates packs)
        reference_path = self.calibration_dir / "tuned_parameters_legacy.json"
        self.calibration_dir.mkdir(parents=True, exist_ok=True)
        
        if reference_path.exists():
            # Merge if both exist
            legacy_data = self._read_json(legacy_path)
            existing_data = self._read_json(reference_path)
            if isinstance(legacy_data, dict) and isinstance(existing_data, dict):
                merged = {**existing_data, **legacy_data}
                with open(reference_path, 'w', encoding='utf-8') as f:
                    json.dump(merged, f, indent=2, default=str)
            shutil.move(str(legacy_path), str(reference_path))
        else:
            shutil.move(str(legacy_path), str(reference_path))
        
        logger.info(f"  ✓ Moved tuned parameters to {reference_path} (kept as reference)")
        return True
    
    def cleanup_empty_dirs(self) -> None:
        """Remove empty legacy directories."""
        logger.info("Cleaning up empty directories...")
        
        dirs_to_check = [
            self.data_dir / "outputs",
            self.data_dir / "config",
        ]
        
        for dir_path in dirs_to_check:
            if dir_path.exists() and dir_path.is_dir():
                try:
                    # Only remove if empty
                    if not any(dir_path.iterdir()):
                        dir_path.rmdir()
                        logger.info(f"  ✓ Removed empty directory: {dir_path}")
                except OSError:
                    pass
    
    def run_migration(self, dry_run: bool = False) -> Dict[str, Any]:
        """Run full migration process."""
        logger.info("=" * 60)
        logger.info("Legacy Data Migration")
        logger.info("=" * 60)
        
        if dry_run:
            logger.info("[DRY RUN] No files will be modified")
        
        results = {
            "bet_logs": False,
            "predictions": False,
            "outputs": False,
            "tuned_parameters": False,
        }
        
        try:
            if not dry_run:
                results["bet_logs"] = self.migrate_bet_logs()
                results["predictions"] = self.migrate_predictions()
                results["outputs"] = self.migrate_outputs()
                results["tuned_parameters"] = self.migrate_tuned_parameters()
                self.cleanup_empty_dirs()
            else:
                logger.info("[DRY RUN] Would migrate bet logs, predictions, outputs, tuned parameters")
            
            logger.info("=" * 60)
            logger.info("Migration complete!")
            logger.info("=" * 60)
            
            return results
            
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            raise
    
    @staticmethod
    def _read_csv_rows(file_path: Path) -> List[Dict[str, Any]]:
        """Read CSV file and return rows as dicts."""
        if not file_path.exists():
            return []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                return list(reader)
        except Exception as e:
            logger.warning(f"Failed to read {file_path}: {e}")
            return []
    
    @staticmethod
    def _read_json(file_path: Path) -> Any:
        """Read JSON file."""
        if not file_path.exists():
            return None
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to read {file_path}: {e}")
            return None
    
    @staticmethod
    def _prediction_key(pred: Dict[str, Any]) -> str:
        """Generate unique key for a prediction."""
        return f"{pred.get('date', '')}_{pred.get('game_id', '')}_{pred.get('bet_type', '')}_{pred.get('pick', '')}"


def main():
    """CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Migrate legacy data to canonical paths")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be migrated without making changes")
    parser.add_argument("--repo-root", type=Path,
                        help="Repository root directory (default: auto-detect)")
    
    args = parser.parse_args()
    
    migrator = LegacyDataMigrator(repo_root=args.repo_root)
    results = migrator.run_migration(dry_run=args.dry_run)
    
    if args.dry_run:
        print("\n[DRY RUN] Run without --dry-run to perform migration")
    else:
        print(f"\nMigration results: {results}")


if __name__ == "__main__":
    main()

