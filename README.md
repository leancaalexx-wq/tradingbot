# Polymarket BTC 5-minute scalper

Paper-first trading bot for Polymarket Bitcoin 5-minute Up/Down markets.

The implemented strategy waits for a 5-minute BTC market to approach expiry, then buys the
currently favored side when its executable ask is between 0.80 and 0.85 USDC. With a 1 USDC
stake, a correct 0.80-0.85 fill pays roughly 1.17-1.25 USDC gross, before fees/slippage and
before losing trades. This is not guaranteed profit; late favorites can still flip in the final
seconds.

## Safety defaults

- Paper trading is the default.
- One order maximum per market slug per process.
- Live trading requires explicit flags/environment variables and Polymarket credentials.
- The minimum gross profit filter defaults to 0.10 USDC.

## Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

For live order placement, also install:

```bash
pip install -e ".[live]"
```

## Run in paper mode

```bash
polymarket-btc-bot --once
polymarket-btc-bot --stake 1 --poll-seconds 5
```

## Local dashboard

The bot writes structured events to `runtime/bot-events.jsonl` by default. Start the dashboard in a
second terminal to watch paper trades, skipped markets, current asks, and strategy settings:

```bash
polymarket-btc-dashboard --host 0.0.0.0 --port 8080
```

Then open `http://localhost:8080`. The page auto-refreshes every five seconds.

If you want a different event file:

```bash
BOT_EVENT_LOG=runtime/my-bot-events.jsonl polymarket-btc-bot --optimized-profile --stake 100
polymarket-btc-dashboard --event-log runtime/my-bot-events.jsonl
```

## Deploy with Docker

Paper-mode deployment is the default and does not use real funds:

```bash
cp .env.example .env
docker compose up -d --build polymarket-btc-bot
docker compose logs -f polymarket-btc-bot
```

The compose command runs the bundled optimized profile with `STAKE_USDC=100` by default, but
keeps `LIVE_TRADING=false` and `DRY_RUN=true`.

Live deployment is intentionally a separate profile:

```bash
LIVE_TRADING=true DRY_RUN=false \
POLYMARKET_PRIVATE_KEY=... \
POLYMARKET_FUNDER_ADDRESS=... \
docker compose --profile live up -d --build polymarket-btc-bot-live
```

Only use live mode after confirming paper fills and Polymarket balances/allowances.

## Backtest

Run the same entry rules against recent resolved BTC 5-minute markets:

```bash
polymarket-btc-bot --backtest --backtest-days 7 --capital 1000
```

The backtest uses Gamma for resolved markets and CLOB `/prices-history` at 1-minute fidelity for
historical prices inside the configured late-entry window. Treat the result as an approximation:
historical price points are not full order-book snapshots and do not guarantee that the displayed
size was fillable at that price.

Use `--backtest-workers` to control concurrent historical price requests if the API is slow or
rate-limited.

## Optimize parameters

Search a parameter grid on recent history and validate the best candidate on the trailing holdout
period:

```bash
polymarket-btc-bot --optimize --backtest-days 7 --validation-days 2 --capital 1000 --stake 100
```

The bot also includes the latest bundled optimized profile found during development:

```bash
polymarket-btc-bot --optimized-profile --backtest --backtest-days 7 --capital 1000 --stake 100
polymarket-btc-bot --optimized-profile --stake 100
```

Bundled profile:

| Setting | Value |
| --- | --- |
| `MIN_ENTRY_PRICE` | `0.70` |
| `MAX_ENTRY_PRICE` | `0.90` |
| `MIN_EXPECTED_PROFIT_USDC` | `0.05` |
| `MIN_SECONDS_TO_CLOSE` | `5` |
| `MAX_SECONDS_TO_CLOSE` | `180` |

Development walk-forward run with 1000 USDC starting capital and 100 USDC stake:

- Train window: +4997.23 USDC, 997 trades, 83.45% win rate.
- Validation holdout: +2131.20 USDC, 407 trades, 84.77% win rate.
- Full 7-day backtest with bundled profile: +7128.44 USDC, 1404 trades, 83.83% win rate.

Optimization is historical curve fitting. Always compare train and validation results, then run
paper mode before using live funds.

Latest bundled profile:

| Variable | Value |
| --- | --- |
| `MIN_ENTRY_PRICE` | `0.70` |
| `MAX_ENTRY_PRICE` | `0.90` |
| `MIN_EXPECTED_PROFIT_USDC` | `0.05` |
| `MIN_SECONDS_TO_CLOSE` | `5` |
| `MAX_SECONDS_TO_CLOSE` | `180` |

Walk-forward search used 7 trailing days with the last 2 days held out for validation, `1000`
USDC initial capital, and `100` USDC stake per trade. Historical validation result:
`+2131.20` USDC, `407` trades, `84.77%` win rate. Full 7-day run with the selected profile:
`+7128.44` USDC, `1404` trades, `83.83%` win rate. These figures are not live profit
guarantees.

## Configuration

Environment variables:

| Variable | Default | Meaning |
| --- | --- | --- |
| `POLYMARKET_SERIES_SLUG` | `btc-up-or-down-5m` | Gamma event series slug |
| `MIN_ENTRY_PRICE` | `0.80` | Lowest acceptable favored-side ask |
| `MAX_ENTRY_PRICE` | `0.85` | Highest acceptable favored-side ask |
| `MIN_EXPECTED_PROFIT_USDC` | `0.10` | Gross profit filter if the outcome resolves correct |
| `STAKE_USDC` | `1.00` | USDC stake per market |
| `MIN_SECONDS_TO_CLOSE` | `15` | Do not enter in the final seconds below this threshold |
| `MAX_SECONDS_TO_CLOSE` | `90` | Start looking only this close to market expiry |
| `POLL_SECONDS` | `5` | Polling interval |
| `BOT_EVENT_LOG` | `runtime/bot-events.jsonl` | JSONL event log used by the local dashboard |
| `LIVE_TRADING` / `POLYMARKET_LIVE` | `false` | Enables live mode intent |
| `DRY_RUN` | `true` | Must be `false` for live execution |
| `POLYMARKET_PRIVATE_KEY` | unset | Wallet/private key for py-clob-client |
| `POLYMARKET_FUNDER_ADDRESS` | unset | Polymarket proxy/funder address |

## Live trading

Only run live after testing paper behavior and setting Polymarket balances/allowances:

```bash
LIVE_TRADING=true DRY_RUN=false \
POLYMARKET_PRIVATE_KEY=... \
POLYMARKET_FUNDER_ADDRESS=... \
polymarket-btc-bot --live
```

Use small stakes first. This bot does not predict BTC directly; it follows price direction already
visible in the Polymarket order book and accepts the risk that the market reverses before close.
