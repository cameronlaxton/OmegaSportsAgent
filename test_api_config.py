#!/usr/bin/env python3
"""
Test script to validate API configuration is working correctly.
"""

import sys
import os

def test_api_config_module():
    """Test API configuration module"""
    print("\n=== Testing API Configuration Module ===")
    
    from omega.foundation.api_config import (
        get_api_keys,
        get_balldontlie_key,
        get_odds_api_key,
        check_api_keys
    )
    
    # Test getting all keys
    keys = get_api_keys()
    assert "BALLDONTLIE_API_KEY" in keys, "Missing BALLDONTLIE_API_KEY"
    assert "ODDS_API_KEY" in keys, "Missing ODDS_API_KEY"
    print(f"✓ API keys loaded: {list(keys.keys())}")
    
    # Test individual key getters
    bdl_key = get_balldontlie_key()
    odds_key = get_odds_api_key()
    assert bdl_key, "BALLDONTLIE_API_KEY is empty"
    assert odds_key, "ODDS_API_KEY is empty"
    print(f"✓ Ball Don't Lie Key: {bdl_key[:8]}...{bdl_key[-4:]}")
    print(f"✓ Odds API Key: {odds_key[:8]}...{odds_key[-4:]}")
    
    # Test key status check
    status = check_api_keys()
    print(f"✓ Key status checked: {len(status)} keys")
    for key_name, info in status.items():
        print(f"  - {key_name}: source={info['source']}, configured={info['configured']}")
    
    return True


def test_odds_scraper_integration():
    """Test odds scraper uses new config"""
    print("\n=== Testing Odds Scraper Integration ===")
    
    from omega.data.odds_scraper import ODDS_API_KEY, check_api_status
    
    assert ODDS_API_KEY, "ODDS_API_KEY not loaded in odds_scraper"
    print(f"✓ Odds scraper has API key: {ODDS_API_KEY[:8]}...{ODDS_API_KEY[-4:]}")
    
    # Test API status check
    status = check_api_status()
    print(f"✓ API status: {status.get('status', 'unknown')}")
    
    return True


def test_stats_ingestion_integration():
    """Test stats ingestion uses new config"""
    print("\n=== Testing Stats Ingestion Integration ===")
    
    from omega.data.stats_ingestion import BALLDONTLIE_API_KEY
    
    assert BALLDONTLIE_API_KEY, "BALLDONTLIE_API_KEY not loaded in stats_ingestion"
    print(f"✓ Stats ingestion has API key: {BALLDONTLIE_API_KEY[:8]}...{BALLDONTLIE_API_KEY[-4:]}")
    
    return True


def test_environment_override():
    """Test environment variable override works"""
    print("\n=== Testing Environment Variable Override ===")
    
    # Set test environment variable
    test_key = "test_key_12345678"
    os.environ["BALLDONTLIE_API_KEY"] = test_key
    
    # Reimport to get new value
    import importlib
    from omega.foundation import api_config
    importlib.reload(api_config)
    
    key = api_config.get_balldontlie_key()
    assert key == test_key, f"Environment override failed: expected {test_key}, got {key}"
    print(f"✓ Environment override works: {key}")
    
    # Clean up
    del os.environ["BALLDONTLIE_API_KEY"]
    importlib.reload(api_config)
    
    return True


def main():
    """Run all tests"""
    print("============================================================")
    print("API Configuration Test Suite")
    print("============================================================")
    
    tests = [
        ("API Config Module", test_api_config_module),
        ("Odds Scraper Integration", test_odds_scraper_integration),
        ("Stats Ingestion Integration", test_stats_ingestion_integration),
        ("Environment Override", test_environment_override),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            if test_func():
                print(f"✅ {test_name} passed\n")
                passed += 1
        except Exception as e:
            print(f"❌ {test_name} failed: {e}\n")
            failed += 1
    
    print("============================================================")
    print(f"Test Results: {passed} passed, {failed} failed")
    print("============================================================")
    
    if failed > 0:
        print("\n❌ Some tests failed!")
        sys.exit(1)
    else:
        print("\n✅ All API configuration tests passed!")
        sys.exit(0)


if __name__ == "__main__":
    main()
