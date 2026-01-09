#!/usr/bin/env python3
"""
Legacy Data Archive Script

Archives legacy data files after successful migration:
1. Creates data/archive/ directory
2. Moves historical JSON files
3. Moves odds_cache/ directories
4. Moves old perplexity.db
5. Updates DATABASE_STORAGE_GUIDE.md with deprecation notice

Usage:
    python scripts/archive_legacy.py [--dry-run] [--force]
"""

import os
import sys
import shutil
from datetime import datetime
from typing import List, Tuple

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


class LegacyArchiver:
    """Archives legacy data files after migration."""
    
    def __init__(self, dry_run: bool = False, force: bool = False):
        """
        Initialize archiver.
        
        Args:
            dry_run: If True, simulate without moving files
            force: If True, skip migration verification
        """
        self.dry_run = dry_run
        self.force = force
        
        self.archive_dir = "data/archive"
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        self.stats = {
            'files_moved': 0,
            'dirs_moved': 0,
            'bytes_moved': 0,
            'errors': []
        }
        
        print("=" * 80)
        print("📦 LEGACY DATA ARCHIVER")
        print("=" * 80)
        print(f"Archive Directory: {self.archive_dir}")
        print(f"Mode: {'DRY RUN' if dry_run else 'LIVE'}")
        print()
    
    def verify_migration_complete(self) -> bool:
        """
        Verify that migration is complete before archiving.
        
        Returns:
            True if safe to archive, False otherwise
        """
        if self.force:
            print("⚠️  --force flag set, skipping migration verification")
            return True
        
        print("=" * 80)
        print("🔍 VERIFYING MIGRATION STATUS")
        print("=" * 80)
        
        # Check if sports_data.db exists and has data
        db_path = "data/sports_data.db"
        
        if not os.path.exists(db_path):
            print(f"❌ Target database not found: {db_path}")
            print("   Run finalize_migration.py first!")
            return False
        
        # Check database size
        db_size_mb = os.path.getsize(db_path) / (1024 * 1024)
        print(f"Database size: {db_size_mb:.2f} MB")
        
        if db_size_mb < 1:
            print("⚠️  WARNING: Database is very small (< 1 MB)")
            print("   Migration may be incomplete!")
            
            response = input("\nProceed anyway? (yes/no): ")
            if response.lower() != 'yes':
                return False
        
        # Quick check: Count games in database
        try:
            import sqlite3
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM games")
            game_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM games WHERE has_player_stats = 1")
            enriched_count = cursor.fetchone()[0]
            
            conn.close()
            
            print(f"Games in database: {game_count:,}")
            print(f"With player stats: {enriched_count:,}")
            print()
            
            if game_count == 0:
                print("❌ No games in database - migration incomplete!")
                print("   Run finalize_migration.py first!")
                return False
            
            if game_count < 100:
                print("⚠️  WARNING: Low game count, migration may be incomplete")
                response = input("\nProceed anyway? (yes/no): ")
                if response.lower() != 'yes':
                    return False
        
        except Exception as e:
            print(f"⚠️  Could not verify database contents: {e}")
            response = input("\nProceed anyway? (yes/no): ")
            if response.lower() != 'yes':
                return False
        
        print("✅ Migration appears complete")
        print()
        
        return True
    
    def create_archive_directory(self):
        """Create archive directory structure."""
        if self.dry_run:
            print(f"[DRY RUN] Would create: {self.archive_dir}/")
            return
        
        # Create main archive directory
        os.makedirs(self.archive_dir, exist_ok=True)
        
        # Create subdirectories
        os.makedirs(f"{self.archive_dir}/historical", exist_ok=True)
        os.makedirs(f"{self.archive_dir}/odds_cache", exist_ok=True)
        os.makedirs(f"{self.archive_dir}/cache", exist_ok=True)
        
        print(f"✅ Created archive directory: {self.archive_dir}/")
        print()
    
    def archive_files(self, file_patterns: List[str], description: str) -> List[Tuple[str, str]]:
        """
        Archive files matching patterns.
        
        Args:
            file_patterns: List of file paths or glob patterns
            description: Description for logging
            
        Returns:
            List of (source, destination) tuples for moved files
        """
        import glob
        
        print("=" * 80)
        print(f"📦 ARCHIVING: {description}")
        print("=" * 80)
        
        moved_files = []
        
        for pattern in file_patterns:
            # Handle both exact paths and glob patterns
            if '*' in pattern or '?' in pattern:
                files = glob.glob(pattern)
            else:
                files = [pattern] if os.path.exists(pattern) else []
            
            for file_path in files:
                if not os.path.exists(file_path):
                    continue
                
                # Determine destination
                rel_path = file_path
                if rel_path.startswith('data/'):
                    rel_path = rel_path[5:]  # Remove 'data/' prefix
                
                dest_path = os.path.join(self.archive_dir, rel_path)
                
                # Get file size
                if os.path.isfile(file_path):
                    file_size = os.path.getsize(file_path)
                    size_mb = file_size / (1024 * 1024)
                    print(f"  {file_path} ({size_mb:.2f} MB)")
                else:
                    print(f"  {file_path}/ (directory)")
                
                if self.dry_run:
                    print(f"    → [DRY RUN] Would move to: {dest_path}")
                else:
                    try:
                        # Create destination directory
                        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                        
                        # Move file or directory
                        shutil.move(file_path, dest_path)
                        print(f"    → Moved to: {dest_path}")
                        
                        moved_files.append((file_path, dest_path))
                        
                        if os.path.isfile(dest_path):
                            self.stats['files_moved'] += 1
                            self.stats['bytes_moved'] += os.path.getsize(dest_path)
                        else:
                            self.stats['dirs_moved'] += 1
                    
                    except Exception as e:
                        error_msg = f"Error moving {file_path}: {e}"
                        print(f"    ❌ {error_msg}")
                        self.stats['errors'].append(error_msg)
        
        print()
        return moved_files
    
    def update_documentation(self):
        """Update DATABASE_STORAGE_GUIDE.md with deprecation notice."""
        doc_path = "DATABASE_STORAGE_GUIDE.md"
        
        if not os.path.exists(doc_path):
            print(f"⚠️  Documentation file not found: {doc_path}")
            return
        
        print("=" * 80)
        print("📝 UPDATING DOCUMENTATION")
        print("=" * 80)
        print(f"File: {doc_path}")
        
        deprecation_notice = f"""
---
**⚠️ DEPRECATION NOTICE** *(Added: {datetime.now().strftime('%Y-%m-%d')})*

This document describes the **legacy JSON-based storage system** which has been replaced by the unified SQLite database (`data/sports_data.db`).

**All legacy data has been archived to `data/archive/` as of {datetime.now().strftime('%Y-%m-%d')}.**

For current data architecture, see:
- **SQLITE_MIGRATION_COMPLETE.md** - Primary reference for SQLite storage
- **API_USAGE_GUIDE.md** - How to query the unified database
- **DATA_SCHEMA.md** - Table schemas and data structures

---

"""
        
        if self.dry_run:
            print("[DRY RUN] Would add deprecation notice to top of file")
            print()
            return
        
        try:
            # Read existing content
            with open(doc_path, 'r') as f:
                content = f.read()
            
            # Check if already deprecated
            if 'DEPRECATION NOTICE' in content:
                print("ℹ️  File already contains deprecation notice")
                print()
                return
            
            # Add notice at the top (after title if present)
            lines = content.split('\n')
            
            # Find where to insert (after first heading)
            insert_idx = 0
            for i, line in enumerate(lines):
                if line.startswith('#'):
                    insert_idx = i + 1
                    break
            
            # Insert deprecation notice
            lines.insert(insert_idx, deprecation_notice)
            
            # Write back
            with open(doc_path, 'w') as f:
                f.write('\n'.join(lines))
            
            print(f"✅ Added deprecation notice to {doc_path}")
            print()
        
        except Exception as e:
            error_msg = f"Error updating documentation: {e}"
            print(f"❌ {error_msg}")
            self.stats['errors'].append(error_msg)
    
    def create_archive_readme(self, moved_files: List[Tuple[str, str]]):
        """Create README in archive directory explaining what was archived."""
        readme_path = f"{self.archive_dir}/README.md"
        
        if self.dry_run:
            print(f"[DRY RUN] Would create: {readme_path}")
            return
        
        content = f"""# Archived Legacy Data

**Archive Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

This directory contains legacy data files that have been migrated to the unified SQLite database (`../sports_data.db`).

## What's Archived

### Historical Game Data (JSON)
- `historical/nba_2020_games.json`
- `historical/nba_2023_games.json`
- `historical/nba_2024_games.json`
- `historical/sample_nba_2024_games.json`

**Status**: ✅ Migrated to `games` table in `sports_data.db`

### Odds Cache (JSON)
- `odds_cache/nba/2023/*.json` - Daily odds snapshots from 2023 season
- `odds_cache/nba/2024/*.json` - Daily odds snapshots from 2024 season

**Status**: ✅ Migrated to `odds_history` table in `sports_data.db`

### Perplexity Cache (SQLite)
- `cache/perplexity.db` - Old LLM API response cache

**Status**: ✅ Merged into `perplexity_cache` table in `sports_data.db`

## Why Archived?

The project underwent a **Grand Unification Migration** to consolidate data storage:

**Before** (Legacy System):
- Multiple JSON files for game data
- Separate cache directories for odds
- Standalone perplexity.db for API cache
- Issues: Hanging processes, no resume capability, memory inefficiency

**After** (Unified System):
- Single `sports_data.db` SQLite database
- All tables in one place: `games`, `odds_history`, `player_props`, `perplexity_cache`
- Benefits: Crash-safe, concurrent access, WAL mode, indexed queries

## Migration Details

Total files archived: {self.stats['files_moved']}
Total directories archived: {self.stats['dirs_moved']}
Total size: {self.stats['bytes_moved'] / (1024 * 1024):.2f} MB

## Files Moved

"""
        
        for src, dst in moved_files:
            content += f"- `{src}` → `{dst}`\n"
        
        content += f"""

## Can I Delete These Files?

**Yes**, but keep them for now as a backup:

1. First verify the unified database is working:
   ```bash
   python scripts/audit_state.py --verbose
   ```

2. Confirm all expected data is present:
   - Game results with scores
   - Player stats (JSON blobs in `games.player_stats`)
   - Historical odds in `odds_history` table

3. After 30 days of successful operation, you can safely delete this archive directory.

## Restoration

If you need to restore from archive:

```bash
# Restore game data
cp archive/historical/*.json data/historical/

# Restore odds cache
cp -r archive/odds_cache/* data/odds_cache/

# Restore perplexity cache
cp archive/cache/perplexity.db data/cache/

# Re-run migration
python scripts/finalize_migration.py
```

## Documentation

- **SQLITE_MIGRATION_COMPLETE.md** - Primary data architecture reference
- **API_USAGE_GUIDE.md** - How to query the unified database
- **GETTING_STARTED.md** - Quick start guide

---

*Archive created by: scripts/archive_legacy.py*
*Migration guide: SQLITE_MIGRATION_COMPLETE.md*
"""
        
        try:
            with open(readme_path, 'w') as f:
                f.write(content)
            
            print(f"✅ Created: {readme_path}")
            print()
        
        except Exception as e:
            error_msg = f"Error creating archive README: {e}"
            print(f"❌ {error_msg}")
            self.stats['errors'].append(error_msg)
    
    def print_summary(self):
        """Print archive summary."""
        print("=" * 80)
        print("📊 ARCHIVE SUMMARY")
        print("=" * 80)
        print()
        
        print(f"Files Moved:       {self.stats['files_moved']}")
        print(f"Directories Moved: {self.stats['dirs_moved']}")
        print(f"Total Size:        {self.stats['bytes_moved'] / (1024 * 1024):.2f} MB")
        print()
        
        if self.stats['errors']:
            print("⚠️  ERRORS:")
            for error in self.stats['errors']:
                print(f"  - {error}")
            print()
        
        if not self.dry_run:
            print("✅ Archive Complete!")
            print()
            print(f"📁 Legacy files archived to: {self.archive_dir}/")
            print(f"📄 Archive README: {self.archive_dir}/README.md")
            print()
            print("📋 VERIFICATION:")
            print("  1. Run: python scripts/audit_state.py --verbose")
            print("  2. Verify all data is present in sports_data.db")
            print("  3. Keep archive as backup for 30 days")
            print("  4. After verification, archive can be safely deleted")
        else:
            print("ℹ️  This was a DRY RUN - no files were moved")
            print("   Remove --dry-run flag to execute archival")
        
        print()
        print("=" * 80)
    
    def execute(self):
        """Execute full archival process."""
        # Step 1: Verify migration is complete
        if not self.verify_migration_complete():
            print("\n❌ Archival aborted - complete migration first")
            print("   Run: python scripts/finalize_migration.py")
            return False
        
        # Step 2: Create archive directory
        self.create_archive_directory()
        
        # Step 3: Archive historical JSON files
        historical_files = self.archive_files(
            file_patterns=[
                'data/historical/nba_*.json',
                'data/historical/sample_*.json'
            ],
            description="Historical Game Data (JSON)"
        )
        
        # Step 4: Archive odds cache
        odds_files = self.archive_files(
            file_patterns=['data/odds_cache'],
            description="Odds Cache (JSON)"
        )
        
        # Step 5: Archive perplexity.db
        perplexity_files = self.archive_files(
            file_patterns=['data/cache/perplexity.db'],
            description="Perplexity Cache (SQLite)"
        )
        
        # Step 6: Update documentation
        self.update_documentation()
        
        # Step 7: Create archive README
        all_moved = historical_files + odds_files + perplexity_files
        self.create_archive_readme(all_moved)
        
        # Step 8: Print summary
        self.print_summary()
        
        return True


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Archive legacy data files")
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Simulate without moving files'
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='Skip migration verification (use with caution!)'
    )
    
    args = parser.parse_args()
    
    # Create archiver
    archiver = LegacyArchiver(dry_run=args.dry_run, force=args.force)
    
    try:
        success = archiver.execute()
        
        if not success:
            sys.exit(1)
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Archival interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
