"""Read-only source comparison. No application import or configured DB access."""

import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
OUT = Path(__file__).resolve().parent
BASE = "446ee9e649ad91406d66cb5b0c43990f3be590db"
ENV = {"PATH": "/usr/bin:/bin", "PYTHONDONTWRITEBYTECODE": "1"}


def command(args, **kwargs):
    return subprocess.run(args, cwd=ROOT, env=ENV, text=True, capture_output=True, check=False, **kwargs)


def main():
    changed = command(["git", "diff", "--name-only", BASE, "HEAD"]).stdout.splitlines()
    files = [p for p in changed if p.endswith(".py") and p.startswith(("src/", "tests/"))]
    args = [sys.executable, "-m", "ruff", "check", "--output-format", "json"]
    current = json.loads(command([*args, *files]).stdout)
    baseline = []
    for file in files:
        old = command(["git", "show", f"{BASE}:{file}"])
        if old.returncode:
            continue
        baseline.extend(json.loads(command([*args, "--stdin-filename", file, "-"], input=old.stdout).stdout))
    for name, result in (("ruff-final", current), ("ruff-final-baseline", baseline)):
        (OUT / f"{name}.json").write_text(json.dumps(result, indent=2) + "\n")

    def key(item):
        return str(Path(item["filename"]).relative_to(ROOT)), item["code"], item["message"]

    cur, old = Counter(map(key, current)), Counter(map(key, baseline))
    result = {"base": BASE, "files": files, "current": sum(cur.values()), "baseline": sum(old.values()),
              "added": list((cur - old).elements()), "removed": list((old - cur).elements())}
    (OUT / "ruff-final-comparison.json").write_text(json.dumps(result, indent=2) + "\n")
    assert not result["added"], result
    print(json.dumps(result))


if __name__ == "__main__":
    main()
