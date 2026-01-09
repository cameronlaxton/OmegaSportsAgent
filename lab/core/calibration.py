"""
Calibration utilities for probability transformations.

Provides Platt scaling and shrinkage helpers for model probability calibration.
"""

from typing import Dict, Tuple

import numpy as np


def _logit(probabilities: np.ndarray) -> np.ndarray:
    """Convert probabilities to log-odds (logit)."""
    clipped = np.clip(probabilities, 1e-6, 1 - 1e-6)
    return np.log(clipped / (1 - clipped))


def _sigmoid(values: np.ndarray) -> np.ndarray:
    """Compute sigmoid values."""
    return 1 / (1 + np.exp(-values))


def _fit_platt_coefficients(
    logits: np.ndarray,
    outcomes: np.ndarray,
    max_iter: int = 100,
    tol: float = 1e-6
) -> Tuple[float, float]:
    """Fit Platt scaling coefficients using Newton-Raphson updates."""
    features = np.column_stack([logits, np.ones_like(logits)])
    coefficients = np.zeros(features.shape[1])

    for _ in range(max_iter):
        scores = features @ coefficients
        predictions = _sigmoid(scores)
        weights = np.clip(predictions * (1 - predictions), 1e-6, None)

        hessian = features.T @ (weights[:, None] * features)
        gradient = features.T @ (outcomes - predictions)

        try:
            step = np.linalg.solve(hessian, gradient)
        except np.linalg.LinAlgError:
            break

        coefficients += step

        if np.max(np.abs(step)) < tol:
            break

    return float(coefficients[0]), float(coefficients[1])


def apply_platt(
    probabilities: np.ndarray,
    coefficients: Dict[str, float]
) -> np.ndarray:
    """Apply Platt scaling coefficients to probabilities."""
    logits = _logit(probabilities)
    calibrated = _sigmoid(coefficients["a"] * logits + coefficients["b"])
    return np.clip(calibrated, 1e-6, 1 - 1e-6)


def calibrate_probabilities_platt(
    probs: np.ndarray,
    outcomes: np.ndarray
) -> Tuple[np.ndarray, Dict[str, float]]:
    """
    Fit Platt scaling on probabilities and return calibrated probabilities + coefficients.

    Args:
        probs: Model probabilities.
        outcomes: Binary outcomes (0/1).

    Returns:
        Tuple of (calibrated probabilities, coefficients dict).
    """
    probabilities = np.asarray(probs, dtype=float)
    targets = np.asarray(outcomes, dtype=float)

    if probabilities.size == 0:
        return probabilities, {"a": 1.0, "b": 0.0}

    if np.all(targets == targets[0]):
        return np.clip(probabilities, 1e-6, 1 - 1e-6), {"a": 1.0, "b": 0.0}

    logits = _logit(probabilities)
    coefficient_a, coefficient_b = _fit_platt_coefficients(logits, targets)
    coefficients = {"a": coefficient_a, "b": coefficient_b}

    calibrated = apply_platt(probabilities, coefficients)

    return calibrated, coefficients


def shrink_toward_market(
    model_probs: np.ndarray,
    market_probs: np.ndarray,
    alpha: float
) -> np.ndarray:
    """
    Shrink model probabilities toward market probabilities.

    Args:
        model_probs: Model probabilities.
        market_probs: Market-implied probabilities.
        alpha: Shrinkage factor (0 = no shrinkage, 1 = full market).
    """
    model_probs = np.asarray(model_probs, dtype=float)
    market_probs = np.asarray(market_probs, dtype=float)
    blended = (1 - alpha) * model_probs + alpha * market_probs
    return np.clip(blended, 1e-6, 1 - 1e-6)
