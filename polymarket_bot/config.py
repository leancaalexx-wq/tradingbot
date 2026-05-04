from __future__ import annotations

import os
from dataclasses import dataclass, replace
from decimal import Decimal


def _bool_env(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "on"}


def _decimal_env(name: str, default: str) -> Decimal:
    return Decimal(os.getenv(name, default))


def _float_env(name: str, default: str) -> float:
    return float(os.getenv(name, default))


def _int_env(name: str, default: str) -> int:
    return int(os.getenv(name, default))


OPTIMIZED_PROFILE = {
    "min_entry_price": Decimal("0.70"),
    "max_entry_price": Decimal("0.90"),
    "min_expected_profit_usdc": Decimal("0.05"),
    "min_seconds_to_close": 5,
    "max_seconds_to_close": 180,
}


@dataclass(frozen=True)
class BotConfig:
    gamma_base_url: str = "https://gamma-api.polymarket.com"
    clob_base_url: str = "https://clob.polymarket.com"
    series_slug: str = "btc-up-or-down-5m"
    min_entry_price: Decimal = Decimal("0.80")
    max_entry_price: Decimal = Decimal("0.85")
    min_expected_profit_usdc: Decimal = Decimal("0.10")
    stake_usdc: Decimal = Decimal("1.00")
    min_seconds_to_close: int = 15
    max_seconds_to_close: int = 90
    poll_seconds: float = 5.0
    request_timeout_seconds: float = 10.0
    event_log_path: str = "runtime/bot-events.jsonl"
    live_trading: bool = False
    dry_run: bool = True
    private_key: str | None = None
    funder_address: str | None = None
    chain_id: int = 137

    @classmethod
    def from_env(cls) -> "BotConfig":
        live_trading = _bool_env("LIVE_TRADING") or _bool_env("POLYMARKET_LIVE")
        return cls(
            gamma_base_url=os.getenv("GAMMA_BASE_URL", cls.gamma_base_url),
            clob_base_url=os.getenv("CLOB_BASE_URL", cls.clob_base_url),
            series_slug=os.getenv("POLYMARKET_SERIES_SLUG", cls.series_slug),
            min_entry_price=_decimal_env("MIN_ENTRY_PRICE", str(cls.min_entry_price)),
            max_entry_price=_decimal_env("MAX_ENTRY_PRICE", str(cls.max_entry_price)),
            min_expected_profit_usdc=_decimal_env(
                "MIN_EXPECTED_PROFIT_USDC", str(cls.min_expected_profit_usdc)
            ),
            stake_usdc=_decimal_env("STAKE_USDC", str(cls.stake_usdc)),
            min_seconds_to_close=_int_env("MIN_SECONDS_TO_CLOSE", str(cls.min_seconds_to_close)),
            max_seconds_to_close=_int_env("MAX_SECONDS_TO_CLOSE", str(cls.max_seconds_to_close)),
            poll_seconds=_float_env("POLL_SECONDS", str(cls.poll_seconds)),
            request_timeout_seconds=_float_env(
                "REQUEST_TIMEOUT_SECONDS", str(cls.request_timeout_seconds)
            ),
            event_log_path=os.getenv("BOT_EVENT_LOG", cls.event_log_path),
            live_trading=live_trading,
            dry_run=not live_trading or _bool_env("DRY_RUN", "true"),
            private_key=os.getenv("POLYMARKET_PRIVATE_KEY"),
            funder_address=os.getenv("POLYMARKET_FUNDER_ADDRESS"),
            chain_id=_int_env("POLYMARKET_CHAIN_ID", str(cls.chain_id)),
        )

    def with_overrides(
        self,
        *,
        live_trading: bool | None = None,
        poll_seconds: float | None = None,
        stake_usdc: Decimal | None = None,
        min_entry_price: Decimal | None = None,
        max_entry_price: Decimal | None = None,
        min_expected_profit_usdc: Decimal | None = None,
        min_seconds_to_close: int | None = None,
        max_seconds_to_close: int | None = None,
    ) -> "BotConfig":
        return replace(
            self,
            live_trading=self.live_trading if live_trading is None else live_trading,
            dry_run=self.dry_run if live_trading is None else not live_trading,
            poll_seconds=self.poll_seconds if poll_seconds is None else poll_seconds,
            stake_usdc=self.stake_usdc if stake_usdc is None else stake_usdc,
            min_entry_price=self.min_entry_price if min_entry_price is None else min_entry_price,
            max_entry_price=self.max_entry_price if max_entry_price is None else max_entry_price,
            min_expected_profit_usdc=(
                self.min_expected_profit_usdc
                if min_expected_profit_usdc is None
                else min_expected_profit_usdc
            ),
            min_seconds_to_close=(
                self.min_seconds_to_close if min_seconds_to_close is None else min_seconds_to_close
            ),
            max_seconds_to_close=(
                self.max_seconds_to_close if max_seconds_to_close is None else max_seconds_to_close
            ),
        )

    def validate(self) -> None:
        if not Decimal("0") < self.min_entry_price <= self.max_entry_price < Decimal("1"):
            raise ValueError("Entry prices must satisfy 0 < MIN_ENTRY_PRICE <= MAX_ENTRY_PRICE < 1")
        if self.stake_usdc <= 0:
            raise ValueError("STAKE_USDC must be positive")
        if self.min_expected_profit_usdc < 0:
            raise ValueError("MIN_EXPECTED_PROFIT_USDC cannot be negative")
        if self.min_seconds_to_close < 0 or self.max_seconds_to_close <= self.min_seconds_to_close:
            raise ValueError("Close window must satisfy 0 <= MIN_SECONDS_TO_CLOSE < MAX_SECONDS_TO_CLOSE")
        if self.poll_seconds <= 0:
            raise ValueError("POLL_SECONDS must be positive")
        if self.request_timeout_seconds <= 0:
            raise ValueError("REQUEST_TIMEOUT_SECONDS must be positive")
        if self.live_trading and self.dry_run:
            raise ValueError("LIVE_TRADING=true requires DRY_RUN=false")
        if self.live_trading and (not self.private_key or not self.funder_address):
            raise ValueError("Live trading requires POLYMARKET_PRIVATE_KEY and POLYMARKET_FUNDER_ADDRESS")


def apply_optimized_profile(config: BotConfig) -> BotConfig:
    return config.with_overrides(**OPTIMIZED_PROFILE)
