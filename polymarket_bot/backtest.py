from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import requests

from .config import BotConfig
from .gamma import GammaClient
from .models import Market, Quote, TradeIntent
from .strategy import SequentialLateEntryStrategy

LOGGER = logging.getLogger(__name__)
_MISSING_HISTORY = object()


@dataclass(frozen=True)
class BacktestTrade:
    market_slug: str
    end_time: datetime
    outcome_name: str
    winning_outcome: str
    entry_price: float
    stake: Decimal
    shares: Decimal
    pnl: Decimal


@dataclass(frozen=True)
class BacktestReport:
    initial_capital: Decimal
    final_capital: Decimal
    trades: tuple[BacktestTrade, ...] = field(default_factory=tuple)
    markets_seen: int = 0
    markets_without_signal: int = 0
    markets_missing_history: int = 0

    @property
    def pnl(self) -> Decimal:
        return self.final_capital - self.initial_capital

    @property
    def wins(self) -> int:
        return sum(1 for trade in self.trades if trade.pnl > 0)

    @property
    def losses(self) -> int:
        return sum(1 for trade in self.trades if trade.pnl < 0)

    @property
    def win_rate(self) -> float:
        return self.wins / len(self.trades) if self.trades else 0.0

    def to_text(self) -> str:
        return "\n".join(
            [
                "Backtest report",
                f"Initial capital: {self.initial_capital:.2f} USDC",
                f"Final capital:   {self.final_capital:.2f} USDC",
                f"PnL:             {self.pnl:.2f} USDC",
                f"Markets seen:    {self.markets_seen}",
                f"Trades:          {len(self.trades)}",
                f"Wins/Losses:     {self.wins}/{self.losses}",
                f"Win rate:        {self.win_rate:.2%}",
                f"No signal:       {self.markets_without_signal}",
                f"Missing history: {self.markets_missing_history}",
            ]
        )


class PriceHistoryClient:
    def __init__(self, base_url: str, timeout_seconds: float = 10.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds

    def prices(
        self,
        token_id: str,
        *,
        start: datetime,
        end: datetime,
        fidelity_minutes: int = 1,
    ) -> tuple[tuple[datetime, float], ...]:
        response = requests.get(
            f"{self._base_url}/prices-history",
            params={
                "market": token_id,
                "startTs": int(start.timestamp()),
                "endTs": int(end.timestamp()),
                "fidelity": fidelity_minutes,
            },
            timeout=self._timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()
        rows = payload.get("history", []) if isinstance(payload, dict) else []
        parsed: list[tuple[datetime, float]] = []
        for row in rows:
            try:
                parsed.append((datetime.fromtimestamp(int(row["t"]), UTC), float(row["p"])))
            except (KeyError, TypeError, ValueError):
                continue
        return tuple(sorted(parsed, key=lambda item: item[0]))


class Backtester:
    def __init__(self, config: BotConfig) -> None:
        config.validate()
        self.config = config
        self.gamma = GammaClient(
            config.gamma_base_url,
            config.series_slug,
            timeout_seconds=config.request_timeout_seconds,
        )
        self.history = PriceHistoryClient(
            config.clob_base_url,
            timeout_seconds=config.request_timeout_seconds,
        )
        self.strategy = SequentialLateEntryStrategy(config)

    def run(
        self,
        *,
        days: int,
        initial_capital: Decimal,
        end: datetime | None = None,
        workers: int = 16,
    ) -> BacktestReport:
        end_time = end or datetime.now(UTC)
        start_time = end_time - timedelta(days=days)
        markets = self.gamma.closed_markets(start=start_time, end=end_time)
        capital = initial_capital
        trades: list[BacktestTrade] = []
        missing_history = 0
        without_signal = 0

        results: list[tuple[datetime, BacktestTrade | None, str | None]] = []
        with ThreadPoolExecutor(max_workers=max(1, workers)) as executor:
            futures = {
                executor.submit(self._evaluate_market, market): market
                for market in markets
            }
            for future in as_completed(futures):
                market = futures[future]
                try:
                    trade, skip_reason = future.result()
                except Exception:
                    LOGGER.exception("Failed to evaluate market %s", market.slug)
                    missing_history += 1
                    continue
                results.append((market.end_time, trade, skip_reason))

        for _, trade, skip_reason in sorted(results, key=lambda item: item[0]):
            if capital < self.config.stake_usdc:
                LOGGER.warning("Capital below stake size; stopping backtest")
                break
            if skip_reason == "missing_history":
                missing_history += 1
                continue
            if trade is None:
                without_signal += 1
                continue
            capital += trade.pnl
            trades.append(trade)

        return BacktestReport(
            initial_capital=initial_capital,
            final_capital=capital,
            trades=tuple(trades),
            markets_seen=len(markets),
            markets_without_signal=without_signal,
            markets_missing_history=missing_history,
        )

    def _evaluate_market(self, market: Market) -> tuple[BacktestTrade | None, str | None]:
        intent = self._first_signal_in_strategy_window(market)
        if intent is _MISSING_HISTORY:
            return None, "missing_history"
        if intent is None:
            return None, "no_signal"

        winning_outcome = _winning_outcome(market)
        pnl = _trade_pnl(intent, winning_outcome)
        return (
            BacktestTrade(
                market_slug=market.slug,
                end_time=market.end_time,
                outcome_name=intent.outcome_name,
                winning_outcome=winning_outcome,
                entry_price=intent.price,
                stake=Decimal(str(intent.usd_size)),
                shares=Decimal(str(intent.shares)),
                pnl=pnl,
            ),
            None,
        )

    def _first_signal_in_strategy_window(self, market: Market) -> TradeIntent | None | object:
        start = market.end_time - timedelta(seconds=self.config.max_seconds_to_close)
        end = market.end_time - timedelta(seconds=self.config.min_seconds_to_close)
        history_by_outcome: dict[str, tuple[str, tuple[tuple[datetime, float], ...]]] = {}
        for outcome in market.outcomes:
            prices = self.history.prices(outcome.token_id, start=start, end=end)
            if prices:
                history_by_outcome[outcome.name] = (outcome.token_id, prices)
        if not history_by_outcome:
            return _MISSING_HISTORY

        timestamps = sorted(
            {
                timestamp
                for _, prices in history_by_outcome.values()
                for timestamp, _ in prices
                if self.config.min_seconds_to_close
                <= (market.end_time - timestamp).total_seconds()
                <= self.config.max_seconds_to_close
            }
        )
        for timestamp in timestamps:
            quotes: list[Quote] = []
            for outcome_name, (token_id, prices) in history_by_outcome.items():
                price = _latest_price_at_or_before(prices, timestamp)
                if price is None:
                    continue
                quotes.append(
                    Quote(
                        token_id=token_id,
                        outcome_name=outcome_name,
                        ask=price,
                        seconds_to_close=(market.end_time - timestamp).total_seconds(),
                    )
                )
            intent = self.strategy.evaluate(market, tuple(quotes), now=timestamp)
            if intent is not None:
                return intent
        return None


def print_report(report: BacktestReport) -> None:
    print(report.to_text())
    if report.trades:
        print("\nLast 10 trades:")
        for trade in report.trades[-10:]:
            print(
                f"{trade.end_time.isoformat()} {trade.market_slug} "
                f"buy={trade.outcome_name} winner={trade.winning_outcome} "
                f"price={trade.entry_price:.4f} pnl={trade.pnl:.4f}"
            )


def _latest_price_at_or_before(
    prices: tuple[tuple[datetime, float], ...],
    timestamp: datetime,
) -> float | None:
    selected: float | None = None
    for price_time, price in prices:
        if price_time <= timestamp:
            selected = price
        else:
            break
    return selected


def _winning_outcome(market: Market) -> str:
    resolved = [outcome for outcome in market.outcomes if outcome.price is not None]
    if not resolved:
        raise ValueError(f"Market {market.slug} has no resolved outcome prices")
    winner = max(resolved, key=lambda outcome: outcome.price or 0.0)
    return winner.name


def _trade_pnl(intent: TradeIntent, winning_outcome: str) -> Decimal:
    stake = Decimal(str(intent.usd_size))
    if intent.outcome_name != winning_outcome:
        return -stake
    payout = Decimal(str(intent.shares))
    return payout - stake
