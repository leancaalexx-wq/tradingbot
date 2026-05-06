from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class Side(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


@dataclass(frozen=True)
class Outcome:
    name: str
    token_id: str
    price: float | None = None


@dataclass(frozen=True)
class Market:
    slug: str
    question: str
    end_time: datetime
    outcomes: tuple[Outcome, ...]

    @property
    def seconds_to_close(self) -> float:
        return (self.end_time - datetime.now(timezone.utc)).total_seconds()

    def seconds_to_close_at(self, now: datetime) -> float:
        return (self.end_time - now).total_seconds()


@dataclass(frozen=True)
class Quote:
    token_id: str
    outcome_name: str
    ask: float
    seconds_to_close: float


@dataclass(frozen=True)
class TradeIntent:
    market_slug: str
    outcome_name: str
    token_id: str
    side: Side
    price: float
    usd_size: float
    shares: float
    reason: str


@dataclass(frozen=True)
class TradeResult:
    intent: TradeIntent
    order_id: str | None
    status: str
    detail: str


@dataclass
class BotState:
    traded_markets: set[str] = field(default_factory=set)

    def has_traded(self, market_slug: str) -> bool:
        return market_slug in self.traded_markets

    def record(self, market_slug: str) -> None:
        self.traded_markets.add(market_slug)
