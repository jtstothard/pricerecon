"""One bounded independent check of the closed temporary copy boundary.

No private database reads: observe connection closure and byte copies at their
external edges, and verify retained settings/candidates through the public API.
"""

import asyncio
import hashlib
import json
import shutil
import sqlite3
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from tests.monitoring import watch_workflow

OUT = Path(__file__).resolve().parent
connections = []
copies = []
api_roundtrips = []
real_connect = sqlite3.connect
real_copy = shutil.copy2
real_get = watch_workflow.get


class TrackedConnection(sqlite3.Connection):
    closed = False

    def close(self):
        super().close()
        self.closed = True


def connect(*args, **kwargs):
    kwargs['factory'] = TrackedConnection
    connection = real_connect(*args, **kwargs)
    connections.append(connection)
    return connection


def copy(source, destination, **kwargs):
    source, destination = Path(source), Path(destination)
    assert all(connection.closed for connection in connections)
    assert not Path(str(source) + '-wal').exists()
    assert not Path(str(destination) + '-wal').exists()
    before = hashlib.sha256(source.read_bytes()).hexdigest()
    result = real_copy(source, destination, **kwargs)
    after = hashlib.sha256(destination.read_bytes()).hexdigest()
    assert before == after
    copies.append({
        'source': source.name, 'destination': destination.name,
        'open_connections': 0, 'wal_absent': True,
        'source_sha256': before, 'destination_sha256': after,
        'bytes': destination.stat().st_size,
    })
    return result


async def get(client, path):
    value = await real_get(client, path)
    if path == '/api/watches':
        rows = {row['id']: row for row in value['items']}
        assert set(rows) == {7, 8}
        for watch_id, row in rows.items():
            assert row['enabled'] == (watch_id == 7)
            assert row['query'] == 'fallback merchant query'
            assert row['source_queries'] == {'cex': ' (ML05 OR "ML05B") -parts  '}
            assert row['synonym_groups'] == [['ML05', 'ML05B'], ['blue', 'mint']]
            assert row['filters']['price_max'] == '100.00'
            assert row['filters']['spec_match']['excluded_title_terms'] == ['parts']
            assert row['schedule'] == {
                'interval': '30m', 'timezone': 'Europe/London',
                'time_window': {'start': '09:00', 'end': '18:00', 'days': ['mon', 'tue', 'wed']},
            }
            assert row['notifications']['channels'] == ['webhook', 'telegram', 'discord']
            assert row['notifications']['events'] == ['price_drop']
            assert row['notifications']['webhook_url'] == 'https://notify.invalid/hook'
        api_roundtrips.append({'kind': 'legacy', 'enabled_id': 7, 'disabled_id': 8, 'settings_match': True})
    elif path == '/api/discovery/watches':
        api_roundtrips.append({'kind': 'candidates', 'count': len(value['candidates'])})
    return value


with TemporaryDirectory(prefix='pricerecon-offline-', dir='/tmp') as directory:
    storage = Path(directory)
    (storage / '.offline-monitoring').write_text('ticket01-test-storage\n')
    with (
        patch.object(sqlite3, 'connect', connect),
        patch.object(shutil, 'copy2', copy),
        patch.object(watch_workflow, 'get', get),
    ):
        asyncio.run(watch_workflow.recovery(storage))
    assert len(copies) == 4
    # seed() reads the populated feed itself, before recovery() checks it again.
    assert [row['count'] for row in api_roundtrips if row['kind'] == 'candidates'] == [5, 5, 0, 5]
    assert len([row for row in api_roundtrips if row['kind'] == 'legacy']) == 3
    assert all(connection.closed for connection in connections)

receipt = {
    'gate': 'passed', 'copies': copies, 'api_roundtrips': api_roundtrips,
    'all_connections_closed': True, 'temporary_storage_removed': True,
    'scope': 'Closed marked temporary SQLite only; no running/WAL backup or deployment rollback proof',
}
(OUT / 'recovery-copy-probe.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps(receipt, indent=2))
