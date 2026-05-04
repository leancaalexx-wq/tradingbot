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
