"""Pricing data structures for model registry."""

from dataclasses import dataclass
from typing import Any, Dict, List, Literal, Optional


@dataclass(frozen=True)
class PricingInfo:
    """Unified pricing information for a model.

    This unified schema supports both token-based and non-token pricing.

    - scheme: pricing method
    - unit: display/normalization unit
    - input_cost_per_unit / output_cost_per_unit: numeric non-negative costs
    - currency: ISO currency code (default: USD)
    """

    scheme: Literal["per_token", "per_minute", "per_image", "per_request"]
    unit: Literal["million_tokens", "minute", "image", "request"]
    input_cost_per_unit: float
    output_cost_per_unit: float
    currency: str = "USD"
    # Optional tiers for per_image (and future schemes):
    # [ { quality: str, sizes: [ { size: str, cost_per_image: float } ] }, ... ]
    tiers: Optional[List[Dict[str, Any]]] = None

    def __post_init__(self) -> None:  # noqa: D401
        """Basic validation ensuring non-negative costs."""
        if self.input_cost_per_unit < 0:
            raise ValueError("Input cost must be non-negative")
        if self.output_cost_per_unit < 0:
            raise ValueError("Output cost must be non-negative")
        # Basic structure validation for tiers when present
        if self.tiers is not None:
            if not isinstance(self.tiers, list):
                raise ValueError("tiers must be a list if provided")
