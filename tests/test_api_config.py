"""
Tests for the API configuration module (src.foundation.api_config).
"""

import importlib
import os

import pytest


class TestApiConfig:
    """Test API configuration module."""

    def test_api_keys_structure(self):
        from src.foundation.api_config import get_api_keys

        keys = get_api_keys()
        assert "BALLDONTLIE_API_KEY" in keys
        assert "ODDS_API_KEY" in keys

    def test_individual_key_getters_return_strings(self):
        from src.foundation.api_config import get_balldontlie_key, get_odds_api_key

        assert isinstance(get_balldontlie_key(), str)
        assert isinstance(get_odds_api_key(), str)

    def test_check_api_keys_returns_status(self):
        from src.foundation.api_config import check_api_keys

        status = check_api_keys()
        assert len(status) > 0
        for key_name, info in status.items():
            assert "configured" in info


class TestEnvironmentOverride:
    """Test environment variable override works."""

    def test_env_var_overrides_key(self):
        test_key = "test_key_12345678"
        os.environ["BALLDONTLIE_API_KEY"] = test_key

        try:
            from src.foundation import api_config

            importlib.reload(api_config)
            assert api_config.get_balldontlie_key() == test_key
        finally:
            del os.environ["BALLDONTLIE_API_KEY"]
            importlib.reload(api_config)
