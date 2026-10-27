"""Changed-file lint and read-only protected-checkout receipts; no app imports."""

import hashlib
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
BASE = "9ce8d31236192a8e6b98152a835ff68b4dd03bda"
FILES = [
    str(Path(__file__).relative_to(ROOT)),
    "tests/test_watch_workflow.py",
    "tests/monitoring/discovery_ui_server.py",
] + [str(p.relative_to(ROOT)) for p in ROOT.glob("tests/monitoring/watch_workflow*.py")]


def run(command, **kwargs):
    return subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False, **kwargs)


args = [sys.executable, "-m", "ruff", "check", "--output-format", "json"]
current = json.loads(run([*args, *FILES]).stdout)
baseline = []
for path in FILES:
    blob = run(["git", "show", f"{BASE}:{path}"])
    if blob.returncode == 0:
        baseline += json.loads(
            run([*args, "--stdin-filename", path, "-"], input=blob.stdout).stdout
        )


def key(row):
    return str(Path(row["filename"]).relative_to(ROOT)), row["code"], row["message"]


added = list((Counter(map(key, current)) - Counter(map(key, baseline))).elements())
for name, content in (
    ("ruff-current", current),
    ("ruff-baseline", baseline),
    (
        "ruff-comparison",
        {
            "base": BASE,
            "files": FILES,
            "current": len(current),
            "baseline": len(baseline),
            "added": added,
        },
    ),
):
    (OUT / f"{name}.json").write_text(json.dumps(content, indent=2) + "\n")
assert not added
original = Path("/Users/jay/.t3/worktrees/pricerecon/t3-7260bb2e")
manifest = ROOT / "docs/testing/artifacts/watch-assessments/merger/original-77-hashes.json"
checked = []
for item in json.loads(manifest.read_text()):
    payload = (original / item["path"]).read_bytes()
    checked.append(
        {
            "path": item["path"],
            "sha256": hashlib.sha256(payload).hexdigest(),
            "bytes": len(payload),
            "matches": len(payload) == item["bytes"]
            and hashlib.sha256(payload).hexdigest() == item["sha256"],
        }
    )
assert len(checked) == 77 and all(item["matches"] for item in checked)
integration = Path("/Users/jay/.t3/worktrees/pricerecon/watch-category-integration")
protected = {
    "schema_version": 1,
    "original_77_files": checked,
    "original_manifest_sha256": hashlib.sha256(manifest.read_bytes()).hexdigest(),
    "integration_head": run(["git", "-C", str(integration), "rev-parse", "HEAD"]).stdout.strip(),
    "integration_status": run(["git", "-C", str(integration), "status", "--porcelain"]).stdout,
}
assert protected["integration_head"] == BASE and not protected["integration_status"]
(OUT / "protected-worktrees.json").write_text(json.dumps(protected, indent=2) + "\n")
print(json.dumps({"ruff_added": 0, "protected_original_files": 77, "integration_clean_at": BASE}))
