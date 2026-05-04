from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from .config import BotConfig
from .models import Market, Quote, Side, TradeIntent


@dataclass(frozen=True)
class SequentialLateEntryStrategy:
    """Buy the current best-priced side late, after price movement reveals direction."""

    config: BotConfig

    def evaluate(
        self,
        market: Market,
        quotes: tuple[Quote, ...],
        *,
        now: datetime | None = None,
    ) -> TradeIntent | None:
        seconds_left = market.seconds_to_close_at(now) if now else market.seconds_to_close
        if seconds_left < self.config.min_seconds_to_close:
            return None
        if seconds_left > self.config.max_seconds_to_close:
            return None

        candidate = self._best_candidate(quotes)
        if candidate is None:
            return None

        price = Decimal(str(candidate.ask))
        if price < self.config.min_entry_price or price > self.config.max_entry_price:
            return None

        shares = self.config.stake_usdc / price
        expected_profit = shares - self.config.stake_usdc
        if expected_profit < self.config.min_expected_profit_usdc:
            return None

        return TradeIntent(
            market_slug=market.slug,
            outcome_name=candidate.outcome_name,
            token_id=candidate.token_id,
            side=Side.BUY,
            price=float(price),
            usd_size=float(self.config.stake_usdc),
            shares=float(shares),
            reason=(
                f"{candidate.outcome_name} ask is {price:.4f}, within "
                f"{self.config.min_entry_price:.2f}-{self.config.max_entry_price:.2f}, "
                f"with {seconds_left:.1f}s left; gross profit if correct is about "
                f"{expected_profit:.4f} USDC"
            ),
        )

    @staticmethod
    def _best_candidate(quotes: tuple[Quote, ...]) -> Quote | None:
        candidates = [quote for quote in quotes if quote.ask is not None]
        if not candidates:
            return None
        return max(candidates, key=lambda quote: quote.ask)
