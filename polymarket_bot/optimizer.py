from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from itertools import product

from .backtest import PriceHistoryClient
from .config import BotConfig
from .gamma import GammaClient
from .models import Market

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class StrategyParameters:
    min_entry_price: Decimal
    max_entry_price: Decimal
    min_expected_profit_usdc: Decimal
    min_seconds_to_close: int
    max_seconds_to_close: int

    def apply_to(self, config: BotConfig) -> BotConfig:
        return replace(
            config,
            min_entry_price=self.min_entry_price,
            max_entry_price=self.max_entry_price,
            min_expected_profit_usdc=self.min_expected_profit_usdc,
            min_seconds_to_close=self.min_seconds_to_close,
            max_seconds_to_close=self.max_seconds_to_close,
        )


@dataclass(frozen=True)
class SimulationReport:
    parameters: StrategyParameters
    initial_capital: Decimal
    final_capital: Decimal
    markets_seen: int
    trades: int
    wins: int
    losses: int
    missing_history: int

    @property
    def pnl(self) -> Decimal:
        return self.final_capital - self.initial_capital

    @property
    def win_rate(self) -> float:
        return self.wins / self.trades if self.trades else 0.0

    def summary(self) -> str:
        params = self.parameters
        return (
            f"pnl={self.pnl:.2f} final={self.final_capital:.2f} "
            f"trades={self.trades} wins/losses={self.wins}/{self.losses} "
            f"win_rate={self.win_rate:.2%} "
            f"entry={params.min_entry_price}-{params.max_entry_price} "
            f"profit_floor={params.min_expected_profit_usdc} "
            f"window={params.min_seconds_to_close}-{params.max_seconds_to_close}s"
        )


@dataclass(frozen=True)
class OptimizationReport:
    train: SimulationReport
    validation: SimulationReport
    candidates_tested: int

    def to_text(self) -> str:
        return "\n".join(
            [
                "Optimization report",
                f"Candidates tested: {self.candidates_tested}",
                f"Best train:        {self.train.summary()}",
                f"Validation:        {self.validation.summary()}",
                "",
                "Use these env vars to run the selected profile:",
                f"MIN_ENTRY_PRICE={self.train.parameters.min_entry_price}",
                f"MAX_ENTRY_PRICE={self.train.parameters.max_entry_price}",
                f"MIN_EXPECTED_PROFIT_USDC={self.train.parameters.min_expected_profit_usdc}",
                f"MIN_SECONDS_TO_CLOSE={self.train.parameters.min_seconds_to_close}",
                f"MAX_SECONDS_TO_CLOSE={self.train.parameters.max_seconds_to_close}",
            ]
        )


@dataclass(frozen=True)
class LoadedMarket:
    market: Market
    histories: dict[str, tuple[str, tuple[tuple[datetime, float], ...]]]

    @property
    def winner(self) -> str | None:
        resolved = [outcome for outcome in self.market.outcomes if outcome.price is not None]
        if not resolved:
            return None
        return max(resolved, key=lambda outcome: outcome.price or 0.0).name


class StrategyOptimizer:
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

    def optimize(
        self,
        *,
        days: int,
        validation_days: int,
        initial_capital: Decimal,
        workers: int = 32,
    ) -> OptimizationReport:
        end_time = datetime.now(UTC)
        start_time = end_time - timedelta(days=days)
        validation_start = end_time - timedelta(days=validation_days)
        markets = self.gamma.closed_markets(start=start_time, end=end_time)
        candidates = tuple(default_parameter_grid(self.config.stake_usdc))
        max_window = max(candidate.max_seconds_to_close for candidate in candidates)
        min_window = min(candidate.min_seconds_to_close for candidate in candidates)
        loaded = self._load_markets(
            markets,
            min_seconds_to_close=min_window,
            max_seconds_to_close=max_window,
            workers=workers,
        )
        train_markets = tuple(item for item in loaded if item.market.end_time < validation_start)
        validation_markets = tuple(item for item in loaded if item.market.end_time >= validation_start)
        if not train_markets or not validation_markets:
            raise RuntimeError("Not enough market history for train/validation optimization.")

        best_train: SimulationReport | None = None
        for candidate in candidates:
            report = simulate_loaded_markets(
                train_markets,
                parameters=candidate,
                initial_capital=initial_capital,
                stake=self.config.stake_usdc,
            )
            if best_train is None or _score(report) > _score(best_train):
                best_train = report

        assert best_train is not None
        validation = simulate_loaded_markets(
            validation_markets,
            parameters=best_train.parameters,
            initial_capital=initial_capital,
            stake=self.config.stake_usdc,
        )
        return OptimizationReport(
            train=best_train,
            validation=validation,
            candidates_tested=len(candidates),
        )

    def _load_markets(
        self,
        markets: list[Market],
        *,
        min_seconds_to_close: int,
        max_seconds_to_close: int,
        workers: int,
    ) -> tuple[LoadedMarket, ...]:
        with ThreadPoolExecutor(max_workers=max(1, workers)) as executor:
            futures = {
                executor.submit(
                    self._load_market,
                    market,
                    min_seconds_to_close=min_seconds_to_close,
                    max_seconds_to_close=max_seconds_to_close,
                ): market
                for market in markets
            }
            loaded: list[LoadedMarket] = []
            for future in as_completed(futures):
                market = futures[future]
                try:
                    loaded.append(future.result())
                except Exception:
                    LOGGER.exception("Failed loading market history for %s", market.slug)
        return tuple(sorted(loaded, key=lambda item: item.market.end_time))

    def _load_market(
        self,
        market: Market,
        *,
        min_seconds_to_close: int,
        max_seconds_to_close: int,
    ) -> LoadedMarket:
        start = market.end_time - timedelta(seconds=max_seconds_to_close)
        end = market.end_time - timedelta(seconds=min_seconds_to_close)
        histories: dict[str, tuple[str, tuple[tuple[datetime, float], ...]]] = {}
        for outcome in market.outcomes:
            prices = self.history.prices(outcome.token_id, start=start, end=end)
            if prices:
                histories[outcome.name] = (outcome.token_id, prices)
        return LoadedMarket(market=market, histories=histories)


def default_parameter_grid(stake: Decimal) -> tuple[StrategyParameters, ...]:
    min_entries = [Decimal(value) for value in ("0.55", "0.60", "0.65", "0.70", "0.75", "0.80")]
    max_entries = [Decimal(value) for value in ("0.75", "0.80", "0.85", "0.90", "0.95")]
    profit_floors = [Decimal(value) for value in ("0.05", "0.10", "0.15", "0.20", "0.25")]
    min_seconds = [5, 10, 15, 30]
    max_seconds = [45, 60, 90, 120, 180]
    candidates: list[StrategyParameters] = []
    for min_entry, max_entry, profit_floor, min_sec, max_sec in product(
        min_entries,
        max_entries,
        profit_floors,
        min_seconds,
        max_seconds,
    ):
        if min_entry > max_entry or min_sec >= max_sec:
            continue
        # Keep profit floors feasible for the candidate's minimum accepted price.
        if (stake / min_entry) - stake < profit_floor:
            continue
        candidates.append(
            StrategyParameters(
                min_entry_price=min_entry,
                max_entry_price=max_entry,
                min_expected_profit_usdc=profit_floor,
                min_seconds_to_close=min_sec,
                max_seconds_to_close=max_sec,
            )
        )
    return tuple(candidates)


def simulate_loaded_markets(
    loaded_markets: tuple[LoadedMarket, ...],
    *,
    parameters: StrategyParameters,
    initial_capital: Decimal,
    stake: Decimal,
) -> SimulationReport:
    capital = initial_capital
    trades = 0
    wins = 0
    losses = 0
    missing_history = 0

    for loaded in loaded_markets:
        if capital < stake:
            break
        if not loaded.histories:
            missing_history += 1
            continue
        winner = loaded.winner
        if winner is None:
            missing_history += 1
            continue
        signal = _first_signal(loaded, parameters=parameters, stake=stake)
        if signal is None:
            continue

        outcome_name, price = signal
        trades += 1
        if outcome_name == winner:
            wins += 1
            capital += (stake / Decimal(str(price))) - stake
        else:
            losses += 1
            capital -= stake

    return SimulationReport(
        parameters=parameters,
        initial_capital=initial_capital,
        final_capital=capital,
        markets_seen=len(loaded_markets),
        trades=trades,
        wins=wins,
        losses=losses,
        missing_history=missing_history,
    )


def print_optimization_report(report: OptimizationReport) -> None:
    print(report.to_text())


def _first_signal(
    loaded: LoadedMarket,
    *,
    parameters: StrategyParameters,
    stake: Decimal,
) -> tuple[str, float] | None:
    timestamps = sorted(
        {
            timestamp
            for _, prices in loaded.histories.values()
            for timestamp, _ in prices
            if parameters.min_seconds_to_close
            <= (loaded.market.end_time - timestamp).total_seconds()
            <= parameters.max_seconds_to_close
        }
    )
    for timestamp in timestamps:
        best: tuple[str, float] | None = None
        for outcome_name, (_, prices) in loaded.histories.items():
            price = _latest_price_at_or_before(prices, timestamp)
            if price is None:
                continue
            if best is None or price > best[1]:
                best = (outcome_name, price)
        if best is None:
            continue
        price_decimal = Decimal(str(best[1]))
        if price_decimal < parameters.min_entry_price or price_decimal > parameters.max_entry_price:
            continue
        expected_profit = (stake / price_decimal) - stake
        if expected_profit < parameters.min_expected_profit_usdc:
            continue
        return best
    return None


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


def _score(report: SimulationReport) -> tuple[Decimal, int, float]:
    return (report.pnl, report.trades, report.win_rate)
