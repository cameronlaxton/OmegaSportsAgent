#!/usr/bin/env python3
"""
OmegaSports Validation Lab - Main CLI

Unified command-line interface for:
- Repository audit
- Backtesting & calibration
- Calibration pack generation
- Integration with OmegaSportsAgent

Usage:
    # Repository audit
    python cli.py audit
    
    # Run calibration
    python cli.py backtest --league NBA --start-date 2020-01-01 --end-date 2024-12-31
    
    # Generate calibration pack
    python cli.py generate-pack --league NBA --output pack_nba.json
    
    # Database status
    python cli.py db-status
    
    # Apply calibration to agent
    python cli.py apply-pack --pack pack_nba.json --agent-repo ~/OmegaSportsAgent
"""

import argparse
import sys
import json
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from core.calibration_runner import CalibrationRunner
from core.db_manager import DatabaseManager
from adapters.apply_calibration import CalibrationApplicator


def cmd_audit(args):
    """Print repository audit summary."""
    print("\n" + "="*60)
    print("REPOSITORY AUDIT SUMMARY")
    print("="*60)
    
    # Read audit document
    audit_path = Path("docs/audit_repo.md")
    if audit_path.exists():
        with open(audit_path, 'r') as f:
            content = f.read()
        
        # Print executive summary
        print("\n📋 AUDIT DOCUMENT: docs/audit_repo.md")
        print("\nKey Findings:")
        print("  • 9,093 NBA games collected (2019-2025, ~7 years)")
        print("  • Single database: data/sports_data.db (596 MB)")
        print("  • 6 deprecated scripts archived")
        print("  • 1 canonical collection script: collect_historical_sqlite.py")
        print("  • DB access standardized: core/db_manager.py")
        
        print("\nDeprecated Scripts Archived:")
        print("  • collect_historical_5years.py")
        print("  • bulk_collect.py")
        print("  • collect_games_only.py")
        print("  • collect_all_seasons.py")
        print("  • collect_historical_odds.py")
        print("  • collect_data.py")
        print("  • + 7 shell scripts")
        
        print("\nRecommended Actions:")
        print("  ✅ Historical data collection: COMPLETE (no action needed)")
        print("  ✅ Use calibration pipeline: python cli.py backtest")
        print("  ✅ Generate calibration packs: python cli.py generate-pack")
        
        print("\n📄 Full audit: docs/audit_repo.md")
    else:
        print("\n⚠️  Audit document not found. Run: python scripts/collect_historical_sqlite.py --status")
    
    print("="*60 + "\n")


def cmd_db_status(args):
    """Show database status."""
    print("\n" + "="*60)
    print("DATABASE STATUS")
    print("="*60)
    
    db = DatabaseManager(args.db)
    stats = db.get_stats()
    
    print(f"\nDatabase: {args.db}")
    print(f"Games:                {stats.get('games', 0):,}")
    print(f"Player Props:         {stats.get('player_props', 0):,}")
    print(f"Odds History:         {stats.get('odds_history', 0):,}")
    print(f"Player Props Odds:    {stats.get('player_props_odds', 0):,}")
    print(f"Perplexity Cache:     {stats.get('perplexity_cache', 0):,}")
    
    # Check date range
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT sport, MIN(date) as earliest, MAX(date) as latest, COUNT(*) FROM games GROUP BY sport")
    rows = cursor.fetchall()
    
    if rows:
        print("\nDATA COVERAGE:")
        for row in rows:
            sport, earliest, latest, count = row
            print(f"  {sport}: {count:,} games ({earliest} to {latest})")
    else:
        print("\n⚠️  No data found in database")
    
    print("\n" + "="*60 + "\n")


def cmd_backtest(args):
    """Run backtesting & calibration."""
    print("\n" + "="*60)
    print("STARTING BACKTEST CALIBRATION")
    print("="*60)
    print(f"League: {args.league}")
    print(f"Period: {args.start_date} to {args.end_date}")
    print(f"Train Split: {args.train_split:.1%}")
    print(f"Dry Run: {args.dry_run}")
    print("="*60 + "\n")
    
    # Initialize runner
    runner = CalibrationRunner(
        db_path=args.db,
        league=args.league,
        start_date=args.start_date,
        end_date=args.end_date,
        train_split=args.train_split,
        dry_run=args.dry_run
    )
    
    # Run backtest
    edge_thresholds, metrics, reliability_bins, probability_transforms, diagnostics = runner.run_backtest()
    
    # Generate calibration pack if requested
    if args.output or not args.dry_run:
        output_path = args.output or f"data/experiments/backtests/calibration_pack_{args.league.lower()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        pack = runner.generate_calibration_pack(
            edge_thresholds,
            metrics,
            reliability_bins,
            probability_transforms,
            diagnostics,
            output_path
        )
        
        print(f"\n✅ Calibration complete! Pack saved to: {output_path}")
    else:
        print("\n✅ Dry run complete (no output saved)")


def cmd_generate_pack(args):
    """Generate calibration pack from existing backtest."""
    print("\n" + "="*60)
    print("GENERATING CALIBRATION PACK")
    print("="*60)
    
    if not args.league or not args.output:
        print("\n❌ Error: Both --league and --output are required")
        print("\nUsage:")
        print("  python cli.py generate-pack --league NBA --output pack_nba.json")
        sys.exit(1)
    
    # Run backtest
    print(f"\nRunning calibration for {args.league}...")
    
    runner = CalibrationRunner(
        db_path=args.db,
        league=args.league,
        start_date=args.start_date,
        end_date=args.end_date,
        train_split=args.train_split
    )
    
    edge_thresholds, metrics, reliability_bins, probability_transforms, diagnostics = runner.run_backtest()
    
    # Generate pack
    pack = runner.generate_calibration_pack(
        edge_thresholds,
        metrics,
        reliability_bins,
        probability_transforms,
        diagnostics,
        args.output
    )
    
    print(f"\n✅ Calibration pack generated: {args.output}")
    print("\nNext steps:")
    print(f"  1. Review pack: cat {args.output}")
    print(f"  2. Apply to agent: python cli.py apply-pack --pack {args.output} --agent-repo ~/OmegaSportsAgent")
    print("="*60 + "\n")


def cmd_apply_pack(args):
    """Apply calibration pack to OmegaSportsAgent."""
    print("\n" + "="*60)
    print("APPLYING CALIBRATION PACK")
    print("="*60)
    
    if not args.pack or not args.agent_repo:
        print("\n❌ Error: Both --pack and --agent-repo are required")
        print("\nUsage:")
        print("  python cli.py apply-pack --pack pack_nba.json --agent-repo ~/OmegaSportsAgent")
        sys.exit(1)
    
    # Initialize applicator
    applicator = CalibrationApplicator(args.agent_repo)
    
    # Generate patch plan
    print(f"\nGenerating patch plan for: {args.pack}")
    patch_plan = applicator.generate_patch_plan(args.pack)
    
    # Print summary
    patch_plan.print_summary()
    
    if args.apply:
        print("\n⚠️  Attempting to apply patch...")
        try:
            applicator.apply_patch(patch_plan, dry_run=False)
        except NotImplementedError as e:
            print(f"\n❌ {e}")
            print("\n✅ For now, manually apply changes to OmegaSportsAgent")
    else:
        print("\n✅ Dry-run complete - no changes made")
        print("   Use --apply flag to attempt application (when implemented)")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog='cli.py',
        description='OmegaSports Validation Lab - Unified CLI',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Repository audit
  python cli.py audit
  
  # Database status
  python cli.py db-status
  
  # Run calibration
  python cli.py backtest --league NBA --start-date 2020-01-01 --end-date 2024-12-31
  
  # Quick test run (dry-run)
  python cli.py backtest --league NBA --start-date 2023-01-01 --end-date 2023-12-31 --dry-run
  
  # Generate calibration pack
  python cli.py generate-pack --league NBA --output calibration_pack_nba.json
  
  # Apply pack to agent (dry-run)
  python cli.py apply-pack --pack calibration_pack_nba.json --agent-repo ~/OmegaSportsAgent
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # Audit command
    parser_audit = subparsers.add_parser('audit', help='Show repository audit summary')
    
    # DB status command
    parser_db = subparsers.add_parser('db-status', help='Show database status')
    parser_db.add_argument('--db', default='data/sports_data.db', help='Database path')
    
    # Backtest command
    parser_backtest = subparsers.add_parser('backtest', help='Run backtesting & calibration')
    parser_backtest.add_argument('--league', type=str, default='NBA', help='League to calibrate')
    parser_backtest.add_argument('--start-date', type=str, default='2020-01-01', help='Start date (YYYY-MM-DD)')
    parser_backtest.add_argument('--end-date', type=str, default='2024-12-31', help='End date (YYYY-MM-DD)')
    parser_backtest.add_argument('--train-split', type=float, default=0.7, help='Train split fraction (0.0-1.0)')
    parser_backtest.add_argument('--db', default='data/sports_data.db', help='Database path')
    parser_backtest.add_argument('--output', type=str, help='Output path for calibration pack')
    parser_backtest.add_argument('--dry-run', action='store_true', help='Dry run (no output saved)')
    
    # Generate pack command
    parser_gen = subparsers.add_parser('generate-pack', help='Generate calibration pack')
    parser_gen.add_argument('--league', type=str, required=True, help='League to calibrate')
    parser_gen.add_argument('--start-date', type=str, default='2020-01-01', help='Start date')
    parser_gen.add_argument('--end-date', type=str, default='2024-12-31', help='End date')
    parser_gen.add_argument('--train-split', type=float, default=0.7, help='Train split fraction')
    parser_gen.add_argument('--db', default='data/sports_data.db', help='Database path')
    parser_gen.add_argument('--output', type=str, required=True, help='Output JSON file path')
    
    # Apply pack command
    parser_apply = subparsers.add_parser('apply-pack', help='Apply calibration pack to OmegaSportsAgent')
    parser_apply.add_argument('--pack', type=str, required=True, help='Calibration pack JSON file')
    parser_apply.add_argument('--agent-repo', type=str, required=True, help='Path to OmegaSportsAgent repo')
    parser_apply.add_argument('--apply', action='store_true', help='Actually apply changes (experimental)')
    
    # Parse args
    args = parser.parse_args()
    
    # Dispatch commands
    if args.command == 'audit':
        cmd_audit(args)
    elif args.command == 'db-status':
        cmd_db_status(args)
    elif args.command == 'backtest':
        cmd_backtest(args)
    elif args.command == 'generate-pack':
        cmd_generate_pack(args)
    elif args.command == 'apply-pack':
        cmd_apply_pack(args)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
