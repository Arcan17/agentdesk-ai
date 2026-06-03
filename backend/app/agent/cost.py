"""Estimated cost from token usage.

Prices are USD per 1K tokens (input, output). The mock provider gets a small nominal
price so observability metrics are non-zero and meaningful in the demo.
"""
from __future__ import annotations

# model -> (input_per_1k, output_per_1k)
_PRICES: dict[str, tuple[float, float]] = {
    "mock-1": (0.0005, 0.0015),
    "claude-haiku-4-5-20251001": (0.001, 0.005),
    "gpt-4o-mini": (0.00015, 0.0006),
}
_DEFAULT = (0.0005, 0.0015)


def estimate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    in_price, out_price = _PRICES.get(model, _DEFAULT)
    cost = (prompt_tokens / 1000.0) * in_price + (completion_tokens / 1000.0) * out_price
    return round(cost, 8)
