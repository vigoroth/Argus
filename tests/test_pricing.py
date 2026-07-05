"""Cost math in app/core/pricing.py."""
from app.core.pricing import PRICES, cost_usd


def test_known_model_cost():
    # gpt-4o-mini: $0.15 / 1M in, $0.60 / 1M out
    cost = cost_usd("gpt-4o-mini", 1_000_000, 1_000_000)
    assert cost == 0.15 + 0.6


def test_partial_token_cost():
    # 500k in, 250k out on gpt-4o ($2.5 in, $10 out)
    cost = cost_usd("gpt-4o", 500_000, 250_000)
    assert cost == (0.5 * 2.5) + (0.25 * 10)


def test_unknown_model_is_free():
    # local Ollama / unrecognized models map to $0
    assert cost_usd("qwen3:8b", 1_000_000, 1_000_000) == 0.0


def test_embedding_output_is_free():
    # embedding models have zero output price
    cost = cost_usd("text-embedding-3-small", 1_000_000, 1_000_000)
    assert cost == PRICES["text-embedding-3-small"][0] / 1  # only input priced


def test_zero_tokens_zero_cost():
    assert cost_usd("gpt-4o", 0, 0) == 0.0
