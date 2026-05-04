from datetime import UTC, datetime, timedelta
from decimal import Decimal

from polymarket_bot.config import BotConfig
from polymarket_bot.models import Market, Outcome, Quote
from polymarket_bot.strategy import SequentialLateEntryStrategy


def market(seconds_left: int, now: datetime) -> Market:
    return Market(
        slug="btc-test",
        question="BTC up or down?",
        end_time=now + timedelta(seconds=seconds_left),
        outcomes=(
            Outcome("Up", "up-token"),
            Outcome("Down", "down-token"),
        ),
    )


def test_buys_best_side_inside_entry_window() -> None:
    strategy = SequentialLateEntryStrategy(BotConfig())
    now = datetime(2026, 5, 4, tzinfo=UTC)

    intent = strategy.evaluate(
        market(60, now),
        (
            Quote("up-token", "Up", 0.82, 60),
            Quote("down-token", "Down", 0.18, 60),
        ),
        now=now,
    )

    assert intent is not None
    assert intent.outcome_name == "Up"
    assert intent.price == 0.82
    assert intent.usd_size == 1.0
    assert intent.shares > 1.21


def test_skips_when_price_too_low_to_indicate_direction() -> None:
    strategy = SequentialLateEntryStrategy(BotConfig())
    now = datetime(2026, 5, 4, tzinfo=UTC)

    intent = strategy.evaluate(
        market(60, now),
        (
            Quote("up-token", "Up", 0.70, 60),
            Quote("down-token", "Down", 0.30, 60),
        ),
        now=now,
    )

    assert intent is None


def test_skips_when_price_too_high_for_profit_target() -> None:
    config = BotConfig(max_entry_price=Decimal("0.95"), min_expected_profit_usdc=Decimal("0.10"))
    strategy = SequentialLateEntryStrategy(config)
    now = datetime(2026, 5, 4, tzinfo=UTC)

    intent = strategy.evaluate(
        market(60, now),
        (
            Quote("up-token", "Up", 0.91, 60),
            Quote("down-token", "Down", 0.09, 60),
        ),
        now=now,
    )

    assert intent is None


def test_skips_when_expected_profit_is_below_configured_floor() -> None:
    config = BotConfig(min_expected_profit_usdc=Decimal("0.25"))
    strategy = SequentialLateEntryStrategy(config)
    now = datetime(2026, 5, 4, tzinfo=UTC)

    intent = strategy.evaluate(
        market(60, now),
        (
            Quote("up-token", "Up", 0.84, 60),
            Quote("down-token", "Down", 0.16, 60),
        ),
        now=now,
    )

    assert intent is None


def test_skips_outside_late_entry_time_window() -> None:
    strategy = SequentialLateEntryStrategy(BotConfig())
    now = datetime(2026, 5, 4, tzinfo=UTC)

    assert strategy.evaluate(market(120, now), (Quote("up-token", "Up", 0.82, 120),), now=now) is None
    assert strategy.evaluate(market(5, now), (Quote("up-token", "Up", 0.82, 5),), now=now) is None
