"""Read-only content audit of ticket12 source and evidence; no application imports."""

import hashlib
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
OUT = Path(__file__).resolve().parent
ARTIFACTS = OUT.parent
BASE = '9ce8d31236192a8e6b98152a835ff68b4dd03bda'
SOURCE = '5dc96638a298635fafb3c07dfaf9a88e87331459'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(argv, **kwargs):
    return subprocess.run(argv, cwd=ROOT, text=True, capture_output=True, check=False, **kwargs)


manifest = Path('/Users/jay/.scratch/watch-category-discovery-implementation/initial-worktree-manifest.json')
original = Path('/Users/jay/.t3/worktrees/pricerecon/t3-7260bb2e')
entries = json.loads(manifest.read_text())['files']
assert len(entries) == 77
for row in entries:
    path = original / row['path']
    assert path.stat().st_size == row['bytes'] and sha(path) == row['sha256'], row['path']

verification = json.loads((ARTIFACTS / 'verification.json').read_text())
verified_maps = {}
for field, prefix in [('source_sha256', ROOT), ('artifact_sha256', ARTIFACTS)]:
    for name, expected in verification[field].items():
        assert sha(prefix / name) == expected, name
    verified_maps[field] = len(verification[field])
provenance = json.loads((ARTIFACTS / 'provenance.json').read_text())['source_and_build_sha256']
for name, expected in provenance.items():
    assert sha(ROOT / name) == expected, name
browser = json.loads((ARTIFACTS / 'browser/provenance.json').read_text())
assert sha(ROOT / 'tests/monitoring/watch_workflow_browser.py') == browser['current_driver_sha256']
# The prior driver bytes are not retained. Verify the current bytes; do not
# manufacture a historical file from the implementer's storage-change note.

inspection = json.loads((ARTIFACTS / 'screenshot-inspection.json').read_text())
assert len(inspection['screenshots']) == 19
for name, expected in inspection['screenshots'].items():
    assert sha(ARTIFACTS / 'browser' / name) == expected, name

changed = run(['git', 'diff', '--name-only', BASE, SOURCE]).stdout.splitlines()
files = [name for name in changed if name.endswith('.py')] + [str(path.relative_to(ROOT)) for path in sorted(OUT.glob('*.py'))]
args = [sys.executable, '-m', 'ruff', 'check', '--output-format', 'json']
result = run([*args, *files])
assert result.returncode in (0, 1), result.stderr
current = json.loads(result.stdout)
baseline = []
for name in files:
    blob = run(['git', 'show', f'{BASE}:{name}'])
    if blob.returncode == 0:
        result = run([*args, '--stdin-filename', name, '-'], input=blob.stdout)
        assert result.returncode in (0, 1), result.stderr
        baseline += json.loads(result.stdout)


def key(row):
    return str(Path(row['filename']).relative_to(ROOT)), row['code'], row['message']


added = list((Counter(map(key, current)) - Counter(map(key, baseline))).elements())
(OUT / 'ruff.json').write_text(json.dumps({'files': files, 'current': current, 'baseline': baseline, 'added': added}, indent=2) + '\n')
assert not added, added
receipt = {
    'base': BASE, 'source': SOURCE, 'initial_manifest': str(manifest),
    'initial_manifest_sha256': sha(manifest), 'initial_entries': 77, 'all_original_hashes_and_lengths_match': True,
    'verified_maps': verified_maps, 'provenance_hashes_matched': len(provenance),
    'browser_tested_hash_documented_only': browser['tested_driver_sha256'],
    'browser_post_run_change': 'Implementer documents storage-only change; prior driver bytes unavailable for independent diff',
    'screenshots_hash_matched_and_visually_inspected': 19,
    'ruff_added': 0,
}
(OUT / 'evidence-audit.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps(receipt, indent=2))
