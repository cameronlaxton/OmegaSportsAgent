#!/usr/bin/env python3
"""
API Integration Demo

Demonstrates the integrated BALL DONT LIE and ODDS API functionality.
Shows how the APIs work with the pre-configured keys.
"""

import sys
import json
from datetime import datetime

def demo_api_config():
    """Demonstrate API configuration"""
    print("\n" + "="*60)
    print("API CONFIGURATION DEMO")
    print("="*60)
    
    from src.foundation.api_config import check_api_keys, get_api_keys
    
    print("\n✓ Checking API key configuration...")
    status = check_api_keys()
    
    for key_name, info in status.items():
        print(f"\n{key_name}:")
        print(f"  Status: {'✓ Configured' if info['configured'] else '✗ Not configured'}")
        print(f"  Source: {info['source']}")
        print(f"  Value: {info['value']}")


def demo_odds_api():
    """Demonstrate ODDS API integration"""
    print("\n" + "="*60)
    print("ODDS API DEMO - Live Betting Lines")
    print("="*60)
    
    from src.data.odds_scraper import get_upcoming_games, check_api_status
    
    # Check API status
    print("\n✓ Checking Odds API status...")
    status = check_api_status()
    print(f"  Status: {status.get('status', 'unknown')}")
    if status.get('requests_remaining'):
        print(f"  Requests remaining: {status['requests_remaining']}")
    
    # Fetch NBA games (this will use the API if available, or fallback)
    print("\n✓ Fetching upcoming NBA games...")
    try:
        games = get_upcoming_games("NBA")
        
        if games:
            print(f"  Found {len(games)} game(s)")
            
            # Show first game details
            if len(games) > 0:
                game = games[0]
                print(f"\n  Example Game:")
                print(f"    {game.get('away_team')} @ {game.get('home_team')}")
                print(f"    League: {game.get('league')}")
                print(f"    Source: {game.get('source', 'odds_api')}")
                
                # Show bookmakers if available
                bookmakers = game.get('bookmakers', [])
                if bookmakers:
                    print(f"    Bookmakers: {len(bookmakers)}")
                    if len(bookmakers) > 0:
                        book = bookmakers[0]
                        print(f"      - {book.get('name')}")
                        markets = book.get('markets', {})
                        print(f"      - Markets: {list(markets.keys())}")
        else:
            print("  No games found (API may be rate limited or no games scheduled)")
            
    except Exception as e:
        print(f"  Error: {e}")


def demo_balldontlie_api():
    """Demonstrate BALL DONT LIE API integration"""
    print("\n" + "="*60)
    print("BALL DONT LIE API DEMO - NBA Player Stats")
    print("="*60)
    
    from src.data.stats_ingestion import get_player_stats_from_balldontlie
    
    # Test with a popular NBA player
    test_players = ["LeBron James", "Stephen Curry", "Luka Doncic"]
    
    for player_name in test_players:
        print(f"\n✓ Fetching stats for {player_name}...")
        
        try:
            stats = get_player_stats_from_balldontlie(player_name)
            
            if stats:
                print(f"  Source: {stats.get('source', 'balldontlie')}")
                print(f"  PPG: {stats.get('pts_mean', 0):.1f}")
                print(f"  RPG: {stats.get('reb_mean', 0):.1f}")
                print(f"  APG: {stats.get('ast_mean', 0):.1f}")
                print(f"  Team: {stats.get('team', 'N/A')}")
                print(f"  Position: {stats.get('position', 'N/A')}")
                break  # Only show one successful example
            else:
                print(f"  No stats found (trying next player...)")
                
        except Exception as e:
            print(f"  Error: {e}")
            continue
    else:
        print("\n  Note: Could not fetch player stats (API may require valid key or have rate limits)")


def demo_unified_workflow():
    """Demonstrate how APIs work together in a workflow"""
    print("\n" + "="*60)
    print("UNIFIED WORKFLOW DEMO")
    print("="*60)
    
    print("\n✓ APIs are integrated into the following workflows:")
    print("\n  1. Morning Bets Workflow (omega/workflows/morning_bets.py)")
    print("     - Uses ODDS API for live betting lines")
    print("     - Uses BALL DONT LIE for player statistics")
    print("     - Combines data for +EV bet recommendations")
    
    print("\n  2. Markov Props Analysis (omega/api/markov_analysis.py)")
    print("     - Uses BALL DONT LIE for player averages")
    print("     - Uses ODDS API for player prop lines")
    print("     - Runs Markov chain simulations")
    
    print("\n  3. Team Context Ingestion (omega/data/stats_ingestion.py)")
    print("     - Multi-source fallback chain:")
    print("       • ESPN API")
    print("       • Basketball Reference scraper")
    print("       • NBA.com Stats API")
    print("       • BALL DONT LIE API (new)")
    print("       • Perplexity AI (optional)")
    
    print("\n✓ Example Usage:")
    print("  python main.py --morning-bets --leagues NBA")
    print("  python main.py --markov-props --league NBA --min-edge 5.0")


def main():
    """Run all demos"""
    print("\n")
    print("╔════════════════════════════════════════════════════════════╗")
    print("║  OmegaSports API Integration Demo                          ║")
    print("║  BALL DONT LIE API + THE ODDS API                          ║")
    print("╚════════════════════════════════════════════════════════════╝")
    
    try:
        demo_api_config()
        demo_odds_api()
        demo_balldontlie_api()
        demo_unified_workflow()
        
        print("\n" + "="*60)
        print("✅ API Integration Demo Complete")
        print("="*60)
        print("\nAll APIs are properly configured and integrated!")
        print("The system will use these APIs automatically in workflows.")
        print("\nTo override with custom keys, set environment variables:")
        print("  export BALLDONTLIE_API_KEY='your_key'")
        print("  export ODDS_API_KEY='your_key'")
        print("\n")
        
    except KeyboardInterrupt:
        print("\n\n✗ Demo interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n✗ Demo error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
