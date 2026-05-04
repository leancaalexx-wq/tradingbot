from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

import requests

from .models import Market, Outcome


class GammaClient:
    def __init__(self, base_url: str, series_slug: str, timeout_seconds: float = 10.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._series_slug = series_slug
        self._timeout_seconds = timeout_seconds

    def current_market(self) -> Market:
        response = requests.get(
            f"{self._base_url}/events",
            params={
                "slug": self._series_slug,
                "active": "true",
                "closed": "false",
                "limit": "25",
                "order": "endDate",
                "ascending": "true",
            },
            timeout=self._timeout_seconds,
        )
        response.raise_for_status()
        events = response.json()
        if isinstance(events, dict):
            events = events.get("events") or events.get("data") or []

        now = datetime.now(UTC)
        markets: list[Market] = []
        for event in events:
            for raw_market in event.get("markets") or []:
                market = parse_market(raw_market)
                if market and market.end_time > now:
                    markets.append(market)

        if not markets:
            raise RuntimeError(f"No active market found for series slug {self._series_slug!r}.")
        return min(markets, key=lambda market: market.end_time)

    def series_id(self) -> str:
        response = requests.get(
            f"{self._base_url}/series",
            params={"slug": self._series_slug},
            timeout=self._timeout_seconds,
        )
        response.raise_for_status()
        series = response.json()
        if not series:
            raise RuntimeError(f"No Gamma series found for slug {self._series_slug!r}.")
        return str(series[0]["id"])

    def closed_events(
        self,
        *,
        start: datetime,
        end: datetime,
        limit: int = 200,
    ) -> list[dict[str, Any]]:
        series_id = self.series_id()
        events: list[dict[str, Any]] = []
        offset = 0
        while True:
            response = requests.get(
                f"{self._base_url}/events",
                params={
                    "series_id": series_id,
                    "closed": "true",
                    "limit": str(limit),
                    "offset": str(offset),
                    "order": "endDate",
                    "ascending": "true",
                    "end_date_min": _format_datetime(start),
                    "end_date_max": _format_datetime(end),
                },
                timeout=self._timeout_seconds,
            )
            response.raise_for_status()
            page = response.json()
            if not page:
                break
            events.extend(page)
            if len(page) < limit:
                break
            offset += limit
        return events

    def closed_markets(self, *, start: datetime, end: datetime) -> list[Market]:
        markets: list[Market] = []
        for event in self.closed_events(start=start, end=end):
            for raw_market in event.get("markets") or []:
                market = parse_market(raw_market)
                if market and start <= market.end_time <= end:
                    markets.append(market)
        return markets


def parse_market(raw_market: dict[str, Any]) -> Market | None:
    outcomes_raw = _load_json_list(raw_market.get("outcomes"))
    token_ids_raw = _load_json_list(raw_market.get("clobTokenIds"))
    prices_raw = _load_json_list(raw_market.get("outcomePrices"))
    end_value = raw_market.get("endDate") or raw_market.get("endDateIso")

    if not outcomes_raw or not token_ids_raw or not end_value:
        return None

    outcomes: list[Outcome] = []
    for index, name in enumerate(outcomes_raw):
        if index >= len(token_ids_raw):
            continue
        price = None
        if index < len(prices_raw):
            try:
                price = float(prices_raw[index])
            except (TypeError, ValueError):
                price = None
        outcomes.append(Outcome(name=str(name), token_id=str(token_ids_raw[index]), price=price))

    if len(outcomes) < 2:
        return None

    return Market(
        question=str(raw_market.get("question") or raw_market.get("title") or "BTC 5m Up/Down"),
        slug=str(raw_market.get("slug") or raw_market.get("conditionId") or ""),
        end_time=_parse_datetime(str(end_value)),
        outcomes=tuple(outcomes),
    )


def winning_outcome(raw_market: dict[str, Any]) -> str | None:
    outcomes_raw = _load_json_list(raw_market.get("outcomes"))
    prices_raw = _load_json_list(raw_market.get("outcomePrices"))
    if not outcomes_raw or not prices_raw or len(outcomes_raw) != len(prices_raw):
        return None

    best_index: int | None = None
    best_price = -1.0
    for index, price_raw in enumerate(prices_raw):
        try:
            price = float(price_raw)
        except (TypeError, ValueError):
            continue
        if price > best_price:
            best_index = index
            best_price = price

    if best_index is None or best_price < 0.99:
        return None
    return str(outcomes_raw[best_index])


def _load_json_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            decoded = json.loads(value)
        except json.JSONDecodeError:
            return []
        return decoded if isinstance(decoded, list) else []
    return []


def _parse_datetime(value: str) -> datetime:
    normalized = value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _format_datetime(value: datetime) -> str:
    return value.astimezone(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
