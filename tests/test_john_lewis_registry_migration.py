import json
import sqlite3

from pricerecon.connectors import canonical_connector_id, discover_connectors
from pricerecon.db.schema import init_db


def test_legacy_john_lewis_id_is_canonicalized():
    assert canonical_connector_id("john_lewis") == "johnlewis"
    assert "johnlewis" in discover_connectors()


def test_init_db_repairs_legacy_source_and_watch_ids(tmp_path):
    db_path = tmp_path / "registry.db"
    conn = sqlite3.connect(db_path)
    conn.executescript(
        """
        CREATE TABLE sources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            connector_id TEXT NOT NULL UNIQUE,
            source_type TEXT NOT NULL,
            config_json TEXT NOT NULL,
            enabled INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE watches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            query TEXT NOT NULL,
            category TEXT,
            config_json TEXT NOT NULL,
            last_check_at TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        INSERT INTO sources (connector_id, source_type, config_json)
        VALUES ('john_lewis', 'retailer', '{"name":"john_lewis"}');
        INSERT INTO watches (name, query, config_json)
        VALUES ('legacy', 'laptop', '{"sources":[{"connector":"john_lewis"}],"source_queries":{"john_lewis":"laptop"}}');
        """
    )
    conn.commit()
    conn.close()

    init_db(db_path)

    conn = sqlite3.connect(db_path)
    source = conn.execute("SELECT connector_id, config_json FROM sources").fetchall()
    watch_config = conn.execute("SELECT config_json FROM watches").fetchone()[0]
    conn.close()

    assert source == [("johnlewis", '{"name": "johnlewis"}')]
    config = json.loads(watch_config)
    assert config["sources"] == [{"connector": "johnlewis"}]
    assert config["source_queries"] == {"johnlewis": "laptop"}
