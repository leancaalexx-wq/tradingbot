from __future__ import annotations

import logging
import time

from .clob import PaperExecutionClient, PolymarketClobExecutionClient, PolymarketClobMarketDataClient
from .config import BotConfig
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
        self._traded_markets: set[str] = set()

    def run(self, once: bool = False) -> None:
        LOGGER.info("Starting in %s mode", "LIVE" if self.config.live_trading else "PAPER")
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
            return None

        if signal.market_slug in self._traded_markets:
            LOGGER.info("Already traded %s; skipping duplicate order", signal.market_slug)
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
        self._traded_markets.add(signal.market_slug)
        return signal
