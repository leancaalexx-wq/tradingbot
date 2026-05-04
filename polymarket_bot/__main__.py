from __future__ import annotations

import argparse
import logging
import sys

from dotenv import load_dotenv

from decimal import Decimal

from .backtest import Backtester, print_report
from .config import BotConfig
from .runner import BotRunner


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Trade Polymarket BTC 5-minute Up/Down markets with a late-entry strategy."
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Place real orders. Defaults to paper mode unless POLYMARKET_LIVE=true is also set.",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run one evaluation cycle and exit.",
    )
    parser.add_argument(
        "--backtest",
        action="store_true",
        help="Run a historical backtest instead of live/paper polling.",
    )
    parser.add_argument(
        "--backtest-days",
        type=int,
        default=7,
        help="Number of trailing days to backtest.",
    )
    parser.add_argument(
        "--capital",
        type=float,
        default=1000.0,
        help="Initial USDC capital for backtests.",
    )
    parser.add_argument(
        "--backtest-workers",
        type=int,
        default=16,
        help="Concurrent workers for fetching historical backtest prices.",
    )
    parser.add_argument(
        "--poll-seconds",
        type=float,
        default=None,
        help="Override polling interval.",
    )
    parser.add_argument(
        "--stake",
        type=float,
        default=None,
        help="Override max USDC stake per market.",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging verbosity.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    load_dotenv()
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    config = BotConfig.from_env()
    if args.live:
        config = config.with_overrides(live_trading=True)
    if args.poll_seconds is not None:
        config = config.with_overrides(poll_seconds=args.poll_seconds)
    if args.stake is not None:
        config = config.with_overrides(stake_usdc=Decimal(str(args.stake)))
    config.validate()

    if args.backtest:
        report = Backtester(config).run(
            days=args.backtest_days,
            initial_capital=Decimal(str(args.capital)),
            workers=args.backtest_workers,
        )
        print_report(report)
        return 0

    runner = BotRunner(config)
    runner.run(once=args.once)
    return 0


if __name__ == "__main__":
    sys.exit(main())
