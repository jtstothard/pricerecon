"""Read-only source/receipt checks and isolated baseline Ruff comparison."""
import collections
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

root = Path.cwd()
artifacts = root / 'docs/testing/artifacts/watch-assessments/merger'
manifest = json.loads((root / 'docs/testing/artifacts/watch-assessments/verification.json').read_text())
source_receipt = {}
for group in ('source_sha256', 'receipt_sha256'):
    for name, digest in manifest[group].items():
        actual = hashlib.sha256((root / name).read_bytes()).hexdigest()
        source_receipt[name] = {'expected': digest, 'actual': actual, 'matches': actual == digest}
assert all(r['matches'] for r in source_receipt.values())
(artifacts / 'source-receipt-hashes.json').write_text(json.dumps(source_receipt, indent=2) + '\n')
original = Path('/Users/jay/.t3/worktrees/pricerecon/t3-7260bb2e')
initial = json.loads(Path('/Users/jay/.scratch/watch-category-discovery-implementation/initial-worktree-manifest.json').read_text())
checks = []
for entry in initial['files']:
    data = (original / entry['path']).read_bytes()
    checks.append({'path': entry['path'], 'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data),
                   'matches': hashlib.sha256(data).hexdigest() == entry['sha256'] and len(data) == entry['bytes']})
assert len(checks) == 77 and all(e['matches'] for e in checks)
(artifacts / 'original-77-hashes.json').write_text(json.dumps(checks, indent=2) + '\n')
files = json.loads((root / 'docs/testing/artifacts/watch-assessments/ruff-comparison.json').read_text())['files']
run = subprocess.run([sys.executable, '-m', 'ruff', 'check', '--output-format=json', '--config', 'lint.isort.known-first-party=["pricerecon"]', *files], capture_output=True, text=True)
current = json.loads(run.stdout)
(artifacts / 'ruff-current.json').write_text(run.stdout)
base = '52104eb3de8e4b7c6ff615763d8ecc3572e4e34d'
with tempfile.TemporaryDirectory(prefix='pricerecon-ruff-baseline-') as temp:
    baseline_root = Path(temp).resolve()
    for name in [*files, 'pyproject.toml']:
        read = subprocess.run(['git', 'show', f'{base}:{name}'], capture_output=True)
        if read.returncode == 0:
            dest = baseline_root / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(read.stdout)
    baseline_files = [f for f in files if (baseline_root / f).exists()]
    run = subprocess.run([sys.executable, '-m', 'ruff', 'check', '--output-format=json', '--config', 'lint.isort.known-first-party=["pricerecon"]', *baseline_files], cwd=baseline_root, capture_output=True, text=True)
    baseline = json.loads(run.stdout)
    for item in baseline:
        item['filename'] = str(Path(item['filename']).relative_to(baseline_root))
for item in current:
    item['filename'] = str(Path(item['filename']).relative_to(root))
# Compare diagnostic identity/content and multiplicity, permitting shifted lines.
def signature(item):
    return item['filename'], item['code'], item['message']
added = collections.Counter(map(signature, current)) - collections.Counter(map(signature, baseline))
summary = {'baseline': base, 'files': files, 'baseline_findings': len(baseline), 'current_findings': len(current),
           'added_findings': [list(k) + [v] for k, v in added.items()]}
(artifacts / 'ruff-baseline.json').write_text(json.dumps(baseline, indent=2) + '\n')
(artifacts / 'ruff-comparison.json').write_text(json.dumps(summary, indent=2) + '\n')
assert not added, summary
# Retain exact whitespace diagnostics without rewriting raw evidence.
for label, args in [('diff-all', []), ('diff-source', [':(exclude)docs/testing/artifacts/**'])]:
    result = subprocess.run(['git', 'diff', '--check', base, '81f18ab', '--', '.', *args], capture_output=True, text=True)
    (artifacts / f'{label}.txt').write_text(result.stdout + result.stderr)
    print(label, result.returncode)
print(json.dumps({'source_and_receipt_hashes': len(source_receipt), 'original_hashes': len(checks), **summary}, indent=2))
