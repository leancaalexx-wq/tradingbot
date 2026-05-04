from __future__ import annotations

import argparse
import html
import json
from collections import Counter
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any


DEFAULT_EVENT_LOG = "runtime/bot-events.jsonl"


def read_events(path: Path, limit: int = 200) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()[-limit:]
    events: list[dict[str, Any]] = []
    for line in lines:
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            events.append(payload)
    return events


def render_dashboard(events: list[dict[str, Any]], event_log_path: Path) -> str:
    counts = Counter(str(event.get("type", "unknown")) for event in events)
    latest = events[-1] if events else {}
    trades = [event for event in events if event.get("type") == "trade"]
    no_trades = [event for event in events if event.get("type") == "no_trade"]

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta http-equiv="refresh" content="5">
  <title>Polymarket BTC Bot Dashboard</title>
  <style>
    body {{ background: #0f172a; color: #e2e8f0; font-family: Arial, sans-serif; margin: 0; }}
    header {{ padding: 24px; background: #111827; border-bottom: 1px solid #334155; }}
    main {{ padding: 24px; display: grid; gap: 20px; }}
    .cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 16px; }}
    .card {{ background: #1e293b; border: 1px solid #334155; border-radius: 12px; padding: 16px; }}
    .label {{ color: #94a3b8; font-size: 13px; }}
    .value {{ font-size: 28px; font-weight: bold; margin-top: 8px; }}
    table {{ width: 100%; border-collapse: collapse; background: #1e293b; border-radius: 12px; overflow: hidden; }}
    th, td {{ border-bottom: 1px solid #334155; padding: 10px; text-align: left; vertical-align: top; }}
    th {{ background: #111827; color: #cbd5e1; }}
    code {{ color: #bae6fd; }}
    .trade {{ color: #86efac; }}
    .no_trade {{ color: #fcd34d; }}
    .duplicate_skip {{ color: #c4b5fd; }}
    .status {{ color: #93c5fd; }}
    .small {{ color: #94a3b8; font-size: 12px; }}
  </style>
</head>
<body>
  <header>
    <h1>Polymarket BTC 5m Bot Dashboard</h1>
    <div class="small">Auto-refresh every 5s. Event log: <code>{html.escape(str(event_log_path))}</code></div>
  </header>
  <main>
    <section class="cards">
      {card("Total events", len(events))}
      {card("Paper trades", len(trades))}
      {card("No trade", len(no_trades))}
      {card("Last event", html.escape(str(latest.get("type", "none"))))}
    </section>
    <section>
      <h2>Event counts</h2>
      <table>
        <tr><th>Type</th><th>Count</th></tr>
        {''.join(f"<tr><td>{html.escape(k)}</td><td>{v}</td></tr>" for k, v in sorted(counts.items()))}
      </table>
    </section>
    <section>
      <h2>Latest activity</h2>
      <table>
        <tr><th>Time</th><th>Type</th><th>Market</th><th>Details</th></tr>
        {''.join(render_event_row(event) for event in reversed(events[-50:]))}
      </table>
    </section>
  </main>
</body>
</html>"""


def card(label: str, value: object) -> str:
    return (
        '<div class="card">'
        f'<div class="label">{html.escape(label)}</div>'
        f'<div class="value">{value}</div>'
        "</div>"
    )


def render_event_row(event: dict[str, Any]) -> str:
    event_type = html.escape(str(event.get("type", "unknown")))
    market = html.escape(str(event.get("market_slug", "")))
    details = dict(event)
    details.pop("timestamp", None)
    details.pop("type", None)
    details.pop("market_slug", None)
    return (
        f'<tr class="{event_type}">'
        f"<td>{html.escape(str(event.get('timestamp', '')))}</td>"
        f"<td>{event_type}</td>"
        f"<td>{market}</td>"
        f"<td><code>{html.escape(json.dumps(details, sort_keys=True))}</code></td>"
        "</tr>"
    )


class DashboardHandler(BaseHTTPRequestHandler):
    event_log_path = Path(DEFAULT_EVENT_LOG)

    def do_GET(self) -> None:
        if self.path not in {"/", "/index.html"}:
            self.send_error(404)
            return
        events = read_events(self.event_log_path)
        body = render_dashboard(events, self.event_log_path).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        return


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Local dashboard for Polymarket bot JSONL events.")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--event-log", default=DEFAULT_EVENT_LOG)
    args = parser.parse_args(argv)

    DashboardHandler.event_log_path = Path(args.event_log)
    server = ThreadingHTTPServer((args.host, args.port), DashboardHandler)
    print(f"Dashboard running at http://{args.host}:{args.port}")
    print(f"Reading events from {DashboardHandler.event_log_path}")
    server.serve_forever()
    return 0


def run_dashboard(*, event_log_path: str, host: str, port: int) -> None:
    DashboardHandler.event_log_path = Path(event_log_path)
    server = ThreadingHTTPServer((host, port), DashboardHandler)
    print(f"Dashboard running at http://{host}:{port}")
    print(f"Reading events from {DashboardHandler.event_log_path}")
    server.serve_forever()


if __name__ == "__main__":
    raise SystemExit(main())
