"""Temporary storage and controlled external edges for application workflows.

Use in a fresh child process: audit guards intentionally cannot be removed.
Never import the application before entering this context.
"""

import asyncio
import importlib
import json
import os
import sqlite3
import sys
from contextlib import ExitStack, asynccontextmanager, closing
from datetime import UTC, datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory, gettempdir
from unittest.mock import patch

import httpx


class IsolationViolation(BaseException):
    """Bypass broad application exception handlers when an edge escapes."""


class Clock:
    def __init__(self):
        self.now = datetime(2026, 10, 27, 12, tzinfo=UTC)

    def advance(self, hours=1):
        self.now += timedelta(hours=hours)


class MonitoringHarness:
    def __init__(self, *, storage_root=None):
        self.storage_root = storage_root
        self.clock = Clock()
        self.outcomes = {"cex": [], "scan": []}
        self.searches = []
        self.reports = {}
        self.report_overrides = {}
        self.deliveries = []
        self.blocked_edges = []
        self.search_started = asyncio.Event()

    def __enter__(self):
        if any(name.startswith("pricerecon.") for name in sys.modules):
            raise RuntimeError("MonitoringHarness requires a fresh process before app imports")
        self.stack = ExitStack()
        if self.storage_root is None:
            self.root = Path(
                self.stack.enter_context(TemporaryDirectory(prefix="pricerecon-offline-"))
            ).resolve()
        else:
            self.root = self.storage_root.resolve()
            if (
                not self.root.is_relative_to(Path(gettempdir()).resolve())
                or not self.root.name.startswith("pricerecon-offline-")
                or (self.root / ".offline-monitoring").read_text() != "ticket01-test-storage\n"
            ):
                raise RuntimeError("Shared storage must be a marked temporary test directory")
        self.database = self.root / "pricerecon.db"
        previous_cwd = Path.cwd()
        self.stack.callback(os.chdir, previous_cwd)
        os.chdir(self.root)
        self.stack.enter_context(patch.dict(os.environ, {}, clear=True))

        def guard(event, args):
            if event == "sqlite3.connect":
                if Path(args[0]).resolve() == self.database:
                    return
            elif event not in {
                "socket.connect",
                "socket.connect_ex",
                "socket.getaddrinfo",
                "socket.gethostbyname",
                "socket.gethostbyaddr",
                "socket.sendto",
                "subprocess.Popen",
                "os.system",
                "os.posix_spawn",
            }:
                return
            self.blocked_edges.append(event)
            raise IsolationViolation(f"Offline monitoring blocked {event}")

        sys.addaudithook(guard)
        real_connect = sqlite3.connect

        def connect(*args, **kwargs):
            connection = real_connect(*args, **kwargs)
            connection.create_function(
                "current_timestamp",
                0,
                lambda: self.clock.now.isoformat(),
            )
            return connection

        self.stack.enter_context(patch.object(sqlite3, "connect", connect))

        async def block_async_http(*args, **kwargs):
            self.blocked_edges.append("httpx.async_transport")
            raise IsolationViolation("Offline monitoring blocked real HTTP transport")

        def block_sync_http(*args, **kwargs):
            self.blocked_edges.append("httpx.sync_transport")
            raise IsolationViolation("Offline monitoring blocked real HTTP transport")

        self.stack.enter_context(
            patch.object(
                httpx.AsyncHTTPTransport,
                "handle_async_request",
                block_async_http,
            )
        )
        self.stack.enter_context(
            patch.object(
                httpx.HTTPTransport,
                "handle_request",
                block_sync_http,
            )
        )

        # libcurl performs native I/O outside Python's socket audit events.
        from curl_cffi import AsyncCurl, Curl
        from curl_cffi.requests import AsyncSession, Session

        def block_curl(*args, **kwargs):
            self.blocked_edges.append("curl_cffi.transport")
            raise IsolationViolation("Offline monitoring blocked native curl transport")

        async def block_async_curl(*args, **kwargs):
            block_curl()

        for owner, method, replacement in (
            (Session, "request", block_curl),
            (AsyncSession, "request", block_async_curl),
            (Curl, "perform", block_curl),
            (AsyncCurl, "add_handle", block_curl),
        ):
            self.stack.enter_context(patch.object(owner, method, replacement))

        from pricerecon.connectors.browser_client import BrowserClient

        async def block_browser(*args, **kwargs):
            self.blocked_edges.append("browser.start")
            raise IsolationViolation("Offline monitoring blocked browser startup")

        self.stack.enter_context(patch.object(BrowserClient, "start", block_browser))

        from pricerecon import connectors
        from pricerecon.models import SourceType

        harness = self

        def connector_for(source):
            class ControlledConnector:
                source_role = SourceType.RETAILER

                async def initialize(self):
                    pass

                async def cleanup(self):
                    pass

                async def search_with_evidence(self, query, filters=None):
                    from pricerecon.models.qualification import EvidenceSearchReport

                    if source in harness.report_overrides:
                        return harness.report_overrides[source]
                    return EvidenceSearchReport(
                        listings=await self.search(query, filters),
                        evidence=harness.reports.get(source, []),
                    )

                async def search(self, query, filters=None):
                    harness.searches.append((source, query, filters))
                    harness.search_started.set()
                    outcome = harness.outcomes[source]
                    if isinstance(outcome, Exception):
                        raise outcome
                    return outcome

            return ControlledConnector

        self.stack.enter_context(
            patch.object(
                connectors,
                "discover_connectors",
                lambda: {source: connector_for(source) for source in self.outcomes},
            )
        )
        self.application = importlib.import_module("pricerecon.app")
        from pricerecon.api import watches
        from pricerecon.core import (
            connector_health,
            diff_engine,
            discovery,
            exact_tracking,
            notifications,
            schedule,
            scheduler,
            watch_executor,
        )
        from pricerecon.db import corrections as correction_storage
        from pricerecon.db import discovery as discovery_storage
        from pricerecon.db import history as history_storage
        from pricerecon.db import tracking as tracking_storage

        clock = self.clock

        class ControlledDatetime(datetime):
            @classmethod
            def now(cls, tz=None):
                return clock.now.astimezone(tz) if tz else clock.now.replace(tzinfo=None)

        for module in (
            self.application,
            discovery_storage,
            history_storage,
            correction_storage,
            discovery,
            exact_tracking,
            tracking_storage,
            watches,
            notifications,
            watch_executor,
            diff_engine,
            connector_health,
            schedule,
        ):
            self.stack.enter_context(patch.object(module, "datetime", ControlledDatetime))

        async def webhook(url, payload):
            self.deliveries.append(("webhook", url, payload))
            return True

        async def telegram(token, chat_id, message):
            self.deliveries.append(("telegram", chat_id, message))
            return True

        async def discord(url, message):
            self.deliveries.append(("discord", url, message))
            return True

        for name, transport in (
            ("send_webhook", webhook),
            ("send_telegram", telegram),
            ("send_discord", discord),
        ):
            self.stack.enter_context(patch.object(notifications, name, transport))
        self.scheduler_module = scheduler
        return self

    def __exit__(self, *exc):
        return self.stack.__exit__(*exc)

    def seed_legacy(self, watches):
        """Seed the pre-migration watches table; observe results only via the API."""
        with closing(sqlite3.connect(self.database)) as connection, connection:
            connection.execute("""
                CREATE TABLE watches (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE, query TEXT NOT NULL, category TEXT,
                    config_json TEXT NOT NULL, last_check_at TEXT,
                    created_at TEXT NOT NULL, updated_at TEXT NOT NULL
                )
            """)
            for watch_id, watch in watches:
                config = {
                    key: value
                    for key, value in watch.items()
                    if key not in {"name", "query", "category"}
                }
                connection.execute(
                    "INSERT INTO watches VALUES (?, ?, ?, ?, ?, NULL, ?, ?)",
                    (
                        watch_id,
                        watch["name"],
                        watch["query"],
                        watch.get("category"),
                        json.dumps(config),
                        "2026-01-01T09:00:00+00:00",
                        "2026-01-02T09:00:00+00:00",
                    ),
                )

    @asynccontextmanager
    async def session(self, *, automatic_checks=False):
        from pricerecon.core.scheduler import WatchScheduler

        scheduler = WatchScheduler() if automatic_checks else WatchScheduler(automatic_checks=False)
        with patch.object(self.scheduler_module, "_global_scheduler", scheduler):
            async with (
                self.application.app.router.lifespan_context(self.application.app),
                httpx.AsyncClient(
                    transport=httpx.ASGITransport(app=self.application.app),
                    base_url="http://offline.test",
                ) as client,
            ):
                yield client, scheduler
