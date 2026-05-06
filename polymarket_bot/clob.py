from __future__ import annotations

import requests

from .config import BotConfig
from .models import Side, TradeIntent, TradeResult


class PolymarketClobMarketDataClient:
    def __init__(self, base_url: str, timeout_seconds: float = 10.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds

    def best_ask(self, token_id: str) -> float:
        response = requests.get(
            f"{self._base_url}/price",
            params={"token_id": token_id, "side": "BUY"},
            timeout=self._timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()
        if isinstance(payload, dict) and "price" in payload:
            return float(payload["price"])
        return float(payload)


class PaperExecutionClient:
    def buy(self, intent: TradeIntent) -> TradeResult:
        return TradeResult(
            intent=intent,
            order_id="paper",
            status="paper",
            detail="Simulated order only; no funds were used.",
        )


class PolymarketClobExecutionClient:
    """Minimal live execution adapter for py-clob-client.

    The bot defaults to paper mode. Live mode requires explicit environment
    variables and pre-funded/approved Polymarket credentials.
    """

    def __init__(self, config: BotConfig) -> None:
        try:
            from py_clob_client.client import ClobClient
            from py_clob_client.clob_types import OrderArgs
            from py_clob_client.order_builder.constants import BUY
        except ImportError as exc:  # pragma: no cover - optional live dependency
            raise RuntimeError("Install live dependencies with: pip install '.[live]'") from exc

        self._order_args_cls = OrderArgs
        self._buy_side = BUY
        self._client = ClobClient(
            config.clob_base_url,
            key=config.private_key,
            chain_id=config.chain_id,
            funder=config.funder_address,
        )
        self._client.set_api_creds(self._client.create_or_derive_api_creds())

    def buy(self, intent: TradeIntent) -> TradeResult:
        if intent.side is not Side.BUY:
            raise ValueError("Only BUY orders are supported by this strategy")
        order_args = self._order_args_cls(
            price=intent.price,
            size=intent.shares,
            side=self._buy_side,
            token_id=intent.token_id,
        )
        signed_order = self._client.create_order(order_args)
        response = self._client.post_order(signed_order)
        order_id = None
        if isinstance(response, dict):
            order_id = str(response.get("orderID") or response.get("id") or "")
        return TradeResult(
            intent=intent,
            order_id=order_id or None,
            status="live",
            detail=str(response),
        )
