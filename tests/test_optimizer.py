from datetime import UTC, datetime, timedelta
from decimal import Decimal

from polymarket_bot.models import Market, Outcome
from polymarket_bot.optimizer import (
    LoadedMarket,
    StrategyParameters,
    simulate_loaded_markets,
)


def test_simulate_loaded_markets_scores_candidate() -> None:
    end_time = datetime(2026, 5, 4, tzinfo=UTC)
    market = Market(
        slug="btc-test",
        question="BTC up or down?",
        end_time=end_time,
        outcomes=(Outcome("Up", "up", 1.0), Outcome("Down", "down", 0.0)),
    )
    loaded = LoadedMarket(
        market=market,
        histories={
            "Up": ("up", ((end_time - timedelta(seconds=30), 0.72),)),
            "Down": ("down", ((end_time - timedelta(seconds=30), 0.28),)),
        },
    )
    params = StrategyParameters(
        min_entry_price=Decimal("0.70"),
        max_entry_price=Decimal("0.75"),
        min_expected_profit_usdc=Decimal("0.05"),
        min_seconds_to_close=5,
        max_seconds_to_close=45,
    )

    report = simulate_loaded_markets(
        (loaded,),
        parameters=params,
        initial_capital=Decimal("1000"),
        stake=Decimal("100"),
    )

    assert report.trades == 1
    assert report.wins == 1
    assert report.pnl > Decimal("38")
