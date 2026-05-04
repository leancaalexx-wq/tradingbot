from datetime import UTC, datetime
from decimal import Decimal

from polymarket_bot.backtest import BacktestReport, BacktestTrade


def test_backtest_report_calculates_summary_metrics() -> None:
    report = BacktestReport(
        initial_capital=Decimal("1000"),
        final_capital=Decimal("1000.25"),
        trades=(
            BacktestTrade(
                market_slug="btc-1",
                end_time=datetime(2026, 5, 4, tzinfo=UTC),
                outcome_name="Up",
                winning_outcome="Up",
                entry_price=0.8,
                stake=Decimal("1"),
                shares=Decimal("1.25"),
                pnl=Decimal("0.25"),
            ),
            BacktestTrade(
                market_slug="btc-2",
                end_time=datetime(2026, 5, 4, 0, 5, tzinfo=UTC),
                outcome_name="Down",
                winning_outcome="Up",
                entry_price=0.82,
                stake=Decimal("1"),
                shares=Decimal("1.2195"),
                pnl=Decimal("-1"),
            ),
        ),
    )

    assert report.pnl == Decimal("0.25")
    assert report.wins == 1
    assert report.losses == 1
    assert report.win_rate == 0.5
