"""
cost_calculator.py - トークン→USD→円変換
"""
from __future__ import annotations
from pathlib import Path
from dotenv import dotenv_values

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / "config" / ".env"
_env = dotenv_values(ENV_PATH)

USD_JPY_RATE: float = float(_env.get("USD_JPY_RATE", "155"))

# モデル別単価 ($/1M tokens)
MODEL_PRICING: dict[str, dict[str, float]] = {
    "claude-haiku-4-5-20251001": {"input": 0.80, "output": 4.00, "cache_read": 0.08},
    "claude-sonnet-4-6":         {"input": 3.00, "output": 15.00, "cache_read": 0.30},
    "claude-opus-4-6":           {"input": 15.00, "output": 75.00, "cache_read": 1.50},
}
_FALLBACK_MODEL = "claude-sonnet-4-6"


def calc_cost_usd(
    model: str,
    input_tokens: int,
    output_tokens: int,
    cached_tokens: int = 0,
) -> float:
    pricing = MODEL_PRICING.get(model)
    if pricing is None:
        import warnings
        warnings.warn(f"Unknown model '{model}', falling back to sonnet pricing.", stacklevel=2)
        pricing = MODEL_PRICING[_FALLBACK_MODEL]

    input_cost  = (input_tokens  / 1_000_000) * pricing["input"]
    output_cost = (output_tokens / 1_000_000) * pricing["output"]
    cache_cost  = (cached_tokens / 1_000_000) * pricing["cache_read"]
    return input_cost + output_cost + cache_cost


def usd_to_jpy(usd: float) -> float:
    return usd * USD_JPY_RATE
