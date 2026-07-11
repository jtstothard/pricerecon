from __future__ import annotations

import sqlite3
from pathlib import Path

from pricerecon.cli import main
from pricerecon.db.schema import init_db


def test_cli_export_watch_history_stdout(tmp_path, monkeypatch, capsys):
    db_path = tmp_path / "pricerecon.db"
    monkeypatch.setenv("PRICERECON_DATABASE_PATH", str(db_path))
    monkeypatch.chdir(tmp_path)
    init_db(db_path)

    conn = sqlite3.connect(db_path)
    conn.execute(
        """INSERT INTO watches (name, query, category, config_json, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (
            "Watch",
            "rtx 4090",
            "gpu",
            '{"sources": [], "filters": {}, "schedule": {}, "grouping": {}, "notifications": {}, "enabled": true, "status": "active"}',
            "2026-07-11T00:00:00",
            "2026-07-11T00:00:00",
        ),
    )
    watch_id = conn.execute("SELECT id FROM watches WHERE name = 'Watch'").fetchone()[0]
    conn.execute(
        """INSERT INTO price_history (listing_key, watch_id, price, currency, stock_state, in_stock, timestamp)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        ("listing-1", watch_id, "599.99", "GBP", "in_stock", 1, "2026-07-11T00:00:00"),
    )
    conn.commit()
    conn.close()

    main(["export", str(watch_id), "--format", "csv"])
    out = capsys.readouterr().out
    assert "listing-1" in out
    assert "599.99" in out
    assert "watch_id" in out.splitlines()[0]
