from __future__ import annotations

import logging
import time

from .clob import PaperExecutionClient, PolymarketClobExecutionClient, PolymarketClobMarketDataClient
from .config import BotConfig
from .events import EventLogger
from .gamma import GammaClient
from .models import Quote, TradeIntent
from .strategy import SequentialLateEntryStrategy

LOGGER = logging.getLogger(__name__)


class BotRunner:
    def __init__(self, config: BotConfig) -> None:
        config.validate()
        self.config = config
        self.gamma = GammaClient(
            config.gamma_base_url,
            config.series_slug,
            timeout_seconds=config.request_timeout_seconds,
        )
        self.market_data = PolymarketClobMarketDataClient(
            config.clob_base_url,
            timeout_seconds=config.request_timeout_seconds,
        )
        self.strategy = SequentialLateEntryStrategy(config)
        self.execution = (
            PolymarketClobExecutionClient(config)
            if config.live_trading and not config.dry_run
            else PaperExecutionClient()
        )
        self.events = EventLogger(config.event_log_path)
        self._traded_markets: set[str] = set()

    def run(self, once: bool = False) -> None:
        LOGGER.info("Starting in %s mode", "LIVE" if self.config.live_trading else "PAPER")
        self.events.write(
            "status",
            mode="LIVE" if self.config.live_trading else "PAPER",
            stake_usdc=float(self.config.stake_usdc),
            min_entry_price=float(self.config.min_entry_price),
            max_entry_price=float(self.config.max_entry_price),
            min_seconds_to_close=self.config.min_seconds_to_close,
            max_seconds_to_close=self.config.max_seconds_to_close,
        )
        while True:
            self.run_once()
            if once:
                return
            time.sleep(self.config.poll_seconds)

    def run_once(self) -> TradeIntent | None:
        market = self.gamma.current_market()
        quotes = tuple(
            Quote(
                token_id=outcome.token_id,
                outcome_name=outcome.name,
                ask=self.market_data.best_ask(outcome.token_id),
                seconds_to_close=market.seconds_to_close,
            )
            for outcome in market.outcomes
        )

        signal = self.strategy.evaluate(market, quotes)
        if signal is None:
            LOGGER.info(
                "No trade for %s: %.0fs left, asks=%s",
                market.slug,
                market.seconds_to_close,
                {quote.outcome_name: quote.ask for quote in quotes},
            )
            self.events.write(
                "no_trade",
                market_slug=market.slug,
                question=market.question,
                seconds_to_close=market.seconds_to_close,
                asks={quote.outcome_name: quote.ask for quote in quotes},
            )
            return None

        if signal.market_slug in self._traded_markets:
            LOGGER.info("Already traded %s; skipping duplicate order", signal.market_slug)
            self.events.write(
                "duplicate_skip",
                market_slug=signal.market_slug,
                outcome=signal.outcome_name,
                price=signal.price,
            )
            return None

        LOGGER.info(
            "Trade signal: buy %s at %.4f for $%.2f (%s)",
            signal.outcome_name,
            signal.price,
            signal.usd_size,
            signal.reason,
        )
        result = self.execution.buy(signal)
        LOGGER.info("Order result: %s %s", result.status, result.detail)
        self.events.write(
            "trade",
            market_slug=signal.market_slug,
            outcome=signal.outcome_name,
            side=signal.side.value,
            price=signal.price,
            stake_usdc=signal.usd_size,
            shares=signal.shares,
            reason=signal.reason,
            execution_status=result.status,
            execution_detail=result.detail,
        )
        self._traded_markets.add(signal.market_slug)
        return signal
