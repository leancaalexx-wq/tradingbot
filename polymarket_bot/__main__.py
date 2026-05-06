from __future__ import annotations

import argparse
import logging
import sys

from dotenv import load_dotenv

from decimal import Decimal

from .backtest import Backtester, print_report
from .config import (
    BotConfig,
    apply_aggressive_profile,
    apply_champion_profile,
    apply_optimized_profile,
)
from .dashboard import run_dashboard
from .optimizer import StrategyOptimizer, print_optimization_report
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
        "--optimize",
        action="store_true",
        help="Search strategy parameters on historical data and validate them out-of-sample.",
    )
    parser.add_argument(
        "--optimized-profile",
        action="store_true",
        help="Use the bundled optimized BTC 5m profile from the latest walk-forward search.",
    )
    parser.add_argument(
        "--aggressive-profile",
        action="store_true",
        help="Use the high-frequency profile that aims to enter almost every BTC 5m market.",
    )
    parser.add_argument(
        "--champion-profile",
        action="store_true",
        help="Use the best validation-tested profile from the broad strategy search.",
    )
    parser.add_argument(
        "--dashboard",
        action="store_true",
        help="Run the local web dashboard instead of the trading loop.",
    )
    parser.add_argument(
        "--dashboard-host",
        default="127.0.0.1",
        help="Dashboard bind host.",
    )
    parser.add_argument(
        "--dashboard-port",
        type=int,
        default=8765,
        help="Dashboard bind port.",
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
        "--validation-days",
        type=int,
        default=2,
        help="Trailing days reserved for optimizer validation.",
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
    selected_profiles = [
        args.optimized_profile,
        args.aggressive_profile,
        args.champion_profile,
    ]
    if sum(1 for selected in selected_profiles if selected) > 1:
        raise SystemExit(
            "Choose only one of --optimized-profile, --aggressive-profile, or --champion-profile"
        )
    if args.optimized_profile:
        config = apply_optimized_profile(config)
    if args.aggressive_profile:
        config = apply_aggressive_profile(config)
    if args.champion_profile:
        config = apply_champion_profile(config)
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

    if args.optimize:
        report = StrategyOptimizer(config).optimize(
            days=args.backtest_days,
            validation_days=args.validation_days,
            initial_capital=Decimal(str(args.capital)),
            workers=args.backtest_workers,
        )
        print_optimization_report(report)
        return 0

    if args.dashboard:
        run_dashboard(
            event_log_path=config.event_log_path,
            host=args.dashboard_host,
            port=args.dashboard_port,
        )
        return 0

    runner = BotRunner(config)
    runner.run(once=args.once)
    return 0


if __name__ == "__main__":
    sys.exit(main())
