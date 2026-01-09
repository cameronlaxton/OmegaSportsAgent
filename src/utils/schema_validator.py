"""
Schema validation utilities with LAX/STRICT modes.
Loads schema_map.json and settings.yaml to validate bet logs and predictions.
"""

from __future__ import annotations
import json
import logging
from pathlib import Path
from typing import Any, Dict, List

try:
    import yaml
except ImportError:  # pragma: no cover - fallback if PyYAML missing
    yaml = None


class SchemaViolationException(Exception):
    """Raised when validation fails in STRICT mode."""


class SchemaValidator:
    def __init__(self, base_dir: Path | None = None):
        self.base_dir = base_dir or Path(__file__).resolve().parents[2]
        self.config_dir = self.base_dir / "config"
        self.schema_map_path = self.config_dir / "schema_map.json"
        self.settings_path = self.config_dir / "settings.yaml"
        self.validation_mode = "LAX"
        self.schemas: Dict[str, Any] = {}
        self.valid_leagues: List[str] = []
        self._load_config()

    def _load_json(self, path: Path) -> Dict[str, Any]:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _load_yaml(self, path: Path) -> Dict[str, Any]:
        if yaml is None:
            raise ImportError("PyYAML is required to load YAML settings.")
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    def _load_config(self) -> None:
        # Load schema map
        if self.schema_map_path.exists():
            schema_map = self._load_json(self.schema_map_path)
            self.schemas = schema_map.get("schemas", {})
            self.valid_leagues = schema_map.get("valid_leagues", [])
            self.validation_mode = schema_map.get("validation_mode", "LAX").upper()

        # Override validation mode from settings.yaml if present
        if self.settings_path.exists():
            try:
                settings = self._load_yaml(self.settings_path)
                mode = (
                    settings.get("logging", {})
                    .get("validation_mode", self.validation_mode)
                )
                if isinstance(mode, str):
                    self.validation_mode = mode.upper()
            except Exception:
                # Keep previously set mode if settings cannot be loaded
                pass

    def _log_or_raise(self, message: str) -> None:
        if self.validation_mode == "STRICT":
            raise SchemaViolationException(message)
        else:  # LAX: log and continue
            log_dir = self.base_dir / "data" / "production_logs"
            log_dir.mkdir(parents=True, exist_ok=True)
            log_file = log_dir / "schema_violations.log"
            logging.warning(message)
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(message + "\n")

    # --------------------- Bet Log Validation --------------------- #
    def validate_betlog_row(self, row: Dict[str, Any]) -> bool:
        schema = self.schemas.get("master_betlog", {})
        required = schema.get("required_columns", [])
        data_types = schema.get("data_types", {})

        missing = [col for col in required if col not in row]
        if missing:
            self._log_or_raise(f"Missing betlog columns: {missing}")
            return False

        # League validation
        league = row.get("league")
        if self.valid_leagues and league not in self.valid_leagues:
            self._log_or_raise(f"Invalid league '{league}' for betlog row.")
            return False

        # Basic type checks for known fields
        checks = {
            "odds_decimal": float,
            "stake_amount": float,
            "model_confidence": float,
            "pnl": float,
        }
        for field, expected in checks.items():
            if field in row and not self._is_type(row[field], expected):
                self._log_or_raise(f"Field '{field}' expected {expected}, got {type(row[field])}")
                return False

        return True

    # --------------------- Predictions Validation --------------------- #
    def validate_predictions(self, data: Any) -> bool:
        schema = self.schemas.get("predictions_daily", {})
        required = schema.get("required_fields", [])

        items = data if isinstance(data, list) else [data]
        for item in items:
            if not isinstance(item, dict):
                self._log_or_raise("Prediction entry must be a dict.")
                return False
            missing = [f for f in required if f not in item]
            if missing:
                self._log_or_raise(f"Missing prediction fields: {missing}")
                return False
            league = item.get("league")
            if self.valid_leagues and league not in self.valid_leagues:
                self._log_or_raise(f"Invalid league '{league}' in prediction.")
                return False
        return True

    @staticmethod
    def _is_type(value: Any, expected: type) -> bool:
        try:
            expected(value)
            return True
        except Exception:
            return False


# Convenience singleton
_schema_validator: SchemaValidator | None = None


def get_schema_validator() -> SchemaValidator:
    global _schema_validator
    if _schema_validator is None:
        _schema_validator = SchemaValidator()
    return _schema_validator

