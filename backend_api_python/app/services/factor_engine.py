"""
Factor Engine — compute, rank, and combine factors for stock screening.

Supports:
- Single-factor ranking
- Multi-factor composite scoring (equal-weight or custom weights)
- Factor cross-section (rank a universe of stocks by composite score)
- Parallel universe screening via ThreadPoolExecutor
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from app.data_sources.a_share_factors import (
    fetch_factors_for_symbol,
    get_factor_definitions,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)


class FactorEngine:
    """Factor computation and stock screening engine.

    Usage:
        engine = FactorEngine(max_workers=8)

        # Score a single stock
        result = engine.score_stock('600519.SH')

        # Rank a universe
        ranked = engine.rank_universe(
            ['600519.SH', '000858.SZ', '601318.SH'],
            top_n=10,
        )
    """

    def __init__(self, max_workers: int = 8):
        self.max_workers = max_workers
        self.definitions = get_factor_definitions()

    # ------------------------------------------------------------------
    # Single-stock scoring
    # ------------------------------------------------------------------

    def score_stock(
        self,
        symbol: str,
        factor_weights: dict[str, float] | None = None,
    ) -> dict[str, Any] | None:
        """
        Compute composite factor score for a single stock.

        Args:
            symbol: Stock code like '600519.SH'.
            factor_weights: Optional dict of factor_key → weight.
                            If None, equal-weight for all available factors.

        Returns:
            Dict with symbol, composite_score, and factors, or None if
            the stock should be excluded (ST, suspended, no data).
        """
        factors = fetch_factors_for_symbol(symbol)
        if not factors:
            logger.debug("No factors retrieved for %s", symbol)
            return None

        # Exclude ST stocks
        if factors.get("is_st", 0) > 0:
            logger.debug("Excluding ST stock: %s", symbol)
            return None

        # Build weight map — default to equal weight for all available factors
        if factor_weights is None:
            available_keys = [k for k in factors if k in self.definitions and factors[k] is not None]
            weights = dict.fromkeys(available_keys, 1.0)
        else:
            # Only keep weights for factors that are actually available
            weights = {k: w for k, w in factor_weights.items() if w != 0 and factors.get(k) is not None}

        if not weights:
            logger.debug("No weighted factors available for %s", symbol)
            return None

        # Compute normalized composite score
        total_weight = 0.0
        weighted_score = 0.0
        factor_values: dict[str, float] = {}

        for key, weight in weights.items():
            value = factors[key]
            if value is None:
                continue

            defn = self.definitions.get(key, {})
            # For lower_better factors, flip the sign so higher composite = better
            if defn.get("lower_better", False):
                value = -value

            factor_values[key] = float(value)
            weighted_score += value * weight
            total_weight += abs(weight)

        if total_weight == 0:
            return None

        composite = weighted_score / total_weight

        return {
            "symbol": symbol,
            "composite_score": round(composite, 4),
            "factor_count": len(factor_values),
            "factors": factor_values,
        }

    # ------------------------------------------------------------------
    # Universe ranking
    # ------------------------------------------------------------------

    def rank_universe(
        self,
        symbols: list[str],
        factor_weights: dict[str, float] | None = None,
        top_n: int = 20,
    ) -> list[dict[str, Any]]:
        """
        Rank a universe of stocks by composite factor score.

        Scoring runs in parallel via ThreadPoolExecutor.

        Args:
            symbols: List of stock codes.
            factor_weights: Optional factor weights dict.
            top_n: Return only the top-N ranked stocks.

        Returns:
            List of result dicts sorted by composite_score descending.
        """
        results: list[dict[str, Any]] = []

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {executor.submit(self.score_stock, s, factor_weights): s for s in symbols}

            for future in as_completed(futures):
                symbol = futures[future]
                try:
                    result = future.result()
                    if result:
                        results.append(result)
                except Exception as e:
                    logger.warning("Factor scoring failed for %s: %s", symbol, e)

        # Sort by composite score descending (higher = better)
        results.sort(key=lambda x: x["composite_score"], reverse=True)
        ranked = results[:top_n]
        logger.info(
            "Ranked %d stocks → top %d (universe=%d)",
            len(results),
            len(ranked),
            len(symbols),
        )
        return ranked

    # ------------------------------------------------------------------
    # Factor metadata
    # ------------------------------------------------------------------

    def list_factors(self) -> list[dict[str, Any]]:
        """List all supported factors with metadata."""
        return [
            {
                "key": key,
                "name": defn["name"],
                "category": defn["category"],
                "lower_better": defn.get("lower_better", False),
                "description": defn.get("description", ""),
            }
            for key, defn in self.definitions.items()
        ]

    def get_factors_by_category(self) -> dict[str, list[str]]:
        """Group factor keys by category."""
        categories: dict[str, list[str]] = {}
        for key, defn in self.definitions.items():
            cat = defn.get("category", "other")
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(key)
        return categories
