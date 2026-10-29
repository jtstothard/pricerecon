"""SQLite connection boundary; isolated pilot limits never affect normal storage."""

import sqlite3
from contextvars import ContextVar
from pathlib import Path

isolated_database: ContextVar[Path | None] = ContextVar("isolated_database", default=None)
opening_isolated_connection: ContextVar[bool] = ContextVar(
    "opening_isolated_connection", default=False
)


def connect(database: str | Path) -> sqlite3.Connection:
    isolated = isolated_database.get()
    if isolated is not None and Path(database).resolve() != isolated:
        raise RuntimeError("pilot_database_escape")
    token = opening_isolated_connection.set(isolated is not None)
    try:
        connection = sqlite3.connect(database)
    finally:
        opening_isolated_connection.reset(token)
    if isolated is not None:
        connection.execute("PRAGMA page_size=4096")
        connection.execute("PRAGMA journal_mode=MEMORY")
        connection.execute("PRAGMA temp_store=MEMORY")
        connection.execute("PRAGMA max_page_count=8192")

        def authorize(
            action: int,
            first: str | None,
            second: str | None,
            database_name: str | None,
            trigger: str | None,
        ) -> int:
            if action == sqlite3.SQLITE_ATTACH:
                return sqlite3.SQLITE_DENY
            if (
                action == sqlite3.SQLITE_PRAGMA
                and second is not None
                and first
                in {
                    "page_size",
                    "journal_mode",
                    "temp_store",
                    "max_page_count",
                    "writable_schema",
                }
            ):
                return sqlite3.SQLITE_DENY
            return sqlite3.SQLITE_OK

        connection.set_authorizer(authorize)
    return connection
