from datetime import UTC, datetime

from polymarket_bot.gamma import parse_market


def test_parse_market_accepts_gamma_json_strings() -> None:
    market = parse_market(
        {
            "slug": "btc-test",
            "question": "BTC Up or Down?",
            "endDate": "2026-05-04T10:45:00Z",
            "outcomes": '["Up","Down"]',
            "clobTokenIds": '["token-up","token-down"]',
            "outcomePrices": '["0.82","0.18"]',
        }
    )

    assert market is not None
    assert market.slug == "btc-test"
    assert market.end_time == datetime(2026, 5, 4, 10, 45, tzinfo=UTC)
    assert market.outcomes[0].name == "Up"
    assert market.outcomes[0].token_id == "token-up"


def test_parse_market_rejects_missing_token_ids() -> None:
    assert parse_market({"outcomes": '["Up","Down"]', "endDate": "2026-05-04T10:45:00Z"}) is None


def test_parse_market_accepts_gamma_lists() -> None:
    market = parse_market(
        {
            "slug": "btc-test",
            "endDateIso": "2026-05-04T10:45:00+00:00",
            "outcomes": ["Up", "Down"],
            "clobTokenIds": ["token-up", "token-down"],
        }
    )

    assert market is not None
    assert [outcome.name for outcome in market.outcomes] == ["Up", "Down"]
