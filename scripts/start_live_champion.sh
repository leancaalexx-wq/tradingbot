#!/usr/bin/env bash
set -euo pipefail

missing=0
for name in POLYMARKET_PRIVATE_KEY POLYMARKET_FUNDER_ADDRESS; do
  if [[ -z "${!name:-}" ]]; then
    echo "Missing required environment variable: ${name}" >&2
    missing=1
  fi
done

if [[ "${LIVE_TRADING:-}" != "true" ]]; then
  echo "LIVE_TRADING must be set to true for live deployment." >&2
  missing=1
fi

if [[ "${DRY_RUN:-}" != "false" ]]; then
  echo "DRY_RUN must be set to false for live deployment." >&2
  missing=1
fi

if [[ "$missing" -ne 0 ]]; then
  cat >&2 <<'EOF'

Refusing to start live trading.

Example:
  export POLYMARKET_PRIVATE_KEY='...'
  export POLYMARKET_FUNDER_ADDRESS='0x...'
  export LIVE_TRADING=true
  export DRY_RUN=false
  export STAKE_USDC=100
  scripts/start_live_champion.sh
EOF
  exit 1
fi

export BOT_EVENT_LOG="${BOT_EVENT_LOG:-runtime/live-bot-events.jsonl}"

exec python3 -m polymarket_bot \
  --champion-profile \
  --stake "${STAKE_USDC:-100}" \
  --live \
  --log-level "${LOG_LEVEL:-INFO}"
