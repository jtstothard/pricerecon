"""CLI entry point."""

from __future__ import annotations

import argparse
import csv
import io
import json
import sqlite3
import sys
from pathlib import Path

import uvicorn

from pricerecon.config import get_settings
from pricerecon.db.schema import DB_PATH, init_db


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def export_watch_history(watch_id: int, fmt: str = "csv") -> str:
    conn = _connect()
    cursor = conn.cursor()
    cursor.execute(
        """SELECT listing_key, price, currency, stock_state, in_stock, timestamp
           FROM price_history
           WHERE watch_id = ?
           ORDER BY timestamp DESC""",
        (watch_id,),
    )
    rows = cursor.fetchall()
    conn.close()
    items = [
        {
            "watch_id": watch_id,
            "listing_key": row["listing_key"],
            "price": row["price"],
            "currency": row["currency"],
            "stock_state": row["stock_state"],
            "in_stock": row["in_stock"],
            "timestamp": row["timestamp"],
        }
        for row in rows
    ]
    if fmt == "json":
        return json.dumps(items, indent=2)
    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=[
            "watch_id",
            "listing_key",
            "price",
            "currency",
            "stock_state",
            "in_stock",
            "timestamp",
        ],
    )
    writer.writeheader()
    writer.writerows(items)
    return output.getvalue()


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pricerecon")
    subcommands = parser.add_subparsers(dest="command")

    export_parser = subcommands.add_parser("export", help="Export watch price history")
    export_parser.add_argument("watch_id", type=int, help="Watch ID to export")
    export_parser.add_argument("--format", choices=["csv", "json"], default="csv")
    export_parser.add_argument("--out", help="Write to file instead of stdout")
    return parser


def main(argv: list[str] | None = None) -> None:
    """Run the PriceRecon server or CLI command."""
    settings = get_settings()
    argv = list(sys.argv[1:] if argv is None else argv)

    # Ensure we're running from the right directory for imports
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))

    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "export":
        init_db(DB_PATH)
        output = export_watch_history(args.watch_id, args.format)
        if args.out:
            Path(args.out).write_text(output)
        else:
            sys.stdout.write(output)
        return

    uvicorn.run(
        "pricerecon.app:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        log_level=settings.log_level,
    )


if __name__ == "__main__":
    main()
