"""Database schema and initialization."""

import json
import sqlite3
from pathlib import Path

DB_PATH = Path("pricerecon.db")


def get_db_path() -> Path:
    """Get the database file path."""
    return DB_PATH


def _seed_sources(conn: sqlite3.Connection) -> None:
    """Seed the sources table with discovered connectors if empty."""
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM sources")
    if cursor.fetchone()[0] > 0:
        return

    try:
        from pricerecon.connectors import discover_connectors

        # Entry-point-based connectors (covers all connector classes including
        # Reddit, HUKD, retailers, AliExpress, etc.)
        connectors = discover_connectors()

        for cid, cls in connectors.items():
            # Instantiate to read source_role
            try:
                instance = cls()
                role = instance.source_role.value if hasattr(instance.source_role, 'value') else str(instance.source_role)
                name = getattr(instance, 'display_name', cid)
            except Exception:
                role = "retailer"
                name = cid
            cursor.execute(
                "INSERT OR IGNORE INTO sources (connector_id, source_type, config_json, enabled) VALUES (?, ?, ?, 1)",
                (cid, role, json.dumps({"name": name})),
            )
    except Exception as e:
        # Don't crash init if connector discovery fails
        print(f"Warning: failed to seed sources: {e}")


def init_db(path: Path | None = None) -> None:
    """Initialize the SQLite database with all required tables.

    Args:
        path: Database file path (default: pricerecon.db)
    """
    if path is None:
        path = DB_PATH

    conn = sqlite3.connect(path)
    cursor = conn.cursor()

    # Create tables
    cursor.executescript(
        """
        -- Watches: watch configurations
        CREATE TABLE IF NOT EXISTS watches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            query TEXT NOT NULL,
            category TEXT,
            config_json TEXT NOT NULL,
            last_check_at TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        -- Sources: connector configurations
        CREATE TABLE IF NOT EXISTS sources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            connector_id TEXT NOT NULL UNIQUE,
            source_type TEXT NOT NULL,
            config_json TEXT NOT NULL,
            enabled INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        -- Listings: current snapshot of listings per watch
        CREATE TABLE IF NOT EXISTS listings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            watch_id INTEGER NOT NULL,
            source TEXT NOT NULL,
            source_listing_id TEXT NOT NULL,
            title_raw TEXT NOT NULL,
            price TEXT NOT NULL,
            currency TEXT NOT NULL,
            url TEXT NOT NULL,
            timestamp_seen TEXT NOT NULL,
            listing_json TEXT NOT NULL,
            UNIQUE(watch_id, source, source_listing_id),
            FOREIGN KEY (watch_id) REFERENCES watches(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_listings_watch ON listings(watch_id);
        CREATE INDEX IF NOT EXISTS idx_listings_source ON listings(source, source_listing_id);

        -- Price history: time series of price + stock
        CREATE TABLE IF NOT EXISTS price_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            listing_key TEXT NOT NULL,
            watch_id INTEGER NOT NULL,
            price TEXT NOT NULL,
            currency TEXT NOT NULL,
            stock_state TEXT,
            in_stock INTEGER,
            timestamp TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (watch_id) REFERENCES watches(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_price_history_listing ON price_history(listing_key);
        CREATE INDEX IF NOT EXISTS idx_price_history_watch ON price_history(watch_id);

        -- Events: diff engine events
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            watch_id INTEGER NOT NULL,
            event_type TEXT NOT NULL,
            listing_key TEXT,
            severity TEXT NOT NULL,
            event_json TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (watch_id) REFERENCES watches(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_events_watch ON events(watch_id);
        CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type);

        -- Notifications: sent notification log
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER NOT NULL,
            channel TEXT NOT NULL,
            status TEXT NOT NULL,
            message TEXT,
            error_message TEXT,
            sent_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (event_id) REFERENCES events(id)
        );

        CREATE INDEX IF NOT EXISTS idx_notifications_event ON notifications(event_id);

        -- Connector configs: per-connector settings
        CREATE TABLE IF NOT EXISTS connector_configs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            connector_id TEXT NOT NULL UNIQUE,
            config_json TEXT NOT NULL,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        -- Deal signals: signal source posts (Reddit, HUKD)
        CREATE TABLE IF NOT EXISTS deal_signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,
            signal_id TEXT NOT NULL,
            title TEXT NOT NULL,
            url TEXT,
            price TEXT,
            posted_at TEXT,
            signal_json TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(source, signal_id)
        );

        CREATE INDEX IF NOT EXISTS idx_deal_signals_source ON deal_signals(source);

        -- Connector health: structured degraded states for each connector
        CREATE TABLE IF NOT EXISTS connector_health (
            connector_id TEXT PRIMARY KEY,
            status TEXT NOT NULL,
            last_error TEXT,
            details_json TEXT NOT NULL DEFAULT '{}',
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_connector_health_status ON connector_health(status);

        -- Schema migrations: schema version tracking
        CREATE TABLE IF NOT EXISTS schema_migrations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            version TEXT NOT NULL UNIQUE,
            applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            description TEXT
        );

        -- Insert initial schema version
        INSERT OR IGNORE INTO schema_migrations (version, description)
        VALUES ('1.0', 'Initial schema');
        """
    )

    conn.commit()
    _seed_sources(conn)
    conn.commit()
    conn.close()