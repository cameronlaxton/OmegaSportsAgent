"""
Statistical validation and significance testing.
"""

import logging
from typing import List, Tuple
import numpy as np
from scipy import stats

logger = logging.getLogger(__name__)


class StatisticalValidator:
    """
    Performs statistical validation and significance testing.
    """

    @staticmethod
    def bootstrap_confidence_interval(
        data: List[float], confidence: float = 0.95, n_iterations: int = 10000
    ) -> Tuple[float, float]:
        """
        Calculate bootstrap confidence interval.

        Args:
            data: Data sample
            confidence: Confidence level (0-1)
            n_iterations: Bootstrap iterations

        Returns:
            Tuple of (lower, upper) confidence bounds
        """
        logger.debug(f"Calculating bootstrap CI for {len(data)} samples")
        data = np.array(data)
        bootstrap_means = []

        for _ in range(n_iterations):
            sample = np.random.choice(data, size=len(data), replace=True)
            bootstrap_means.append(np.mean(sample))

        alpha = 1 - confidence
        lower = np.percentile(bootstrap_means, (alpha / 2) * 100)
        upper = np.percentile(bootstrap_means, (1 - alpha / 2) * 100)

        return lower, upper

    @staticmethod
    def t_test(
        group1: List[float], group2: List[float]
    ) -> Tuple[float, float]:
        """
        Perform independent t-test.

        Args:
            group1: First group data
            group2: Second group data

        Returns:
            Tuple of (t_statistic, p_value)
        """
        logger.debug(f"Performing t-test on groups of size {len(group1)} and {len(group2)}")
        t_stat, p_val = stats.ttest_ind(group1, group2)
        return t_stat, p_val

    @staticmethod
    def effect_size(group1: List[float], group2: List[float]) -> float:
        """
        Calculate Cohen's d effect size.

        Args:
            group1: First group data
            group2: Second group data

        Returns:
            Cohen's d value
        """
        mean1 = np.mean(group1)
        mean2 = np.mean(group2)
        std1 = np.std(group1, ddof=1)
        std2 = np.std(group2, ddof=1)
        n1 = len(group1)
        n2 = len(group2)

        pooled_std = np.sqrt(((n1 - 1) * std1**2 + (n2 - 1) * std2**2) / (n1 + n2 - 2))
        cohens_d = (mean1 - mean2) / pooled_std if pooled_std > 0 else 0.0

        return cohens_d
