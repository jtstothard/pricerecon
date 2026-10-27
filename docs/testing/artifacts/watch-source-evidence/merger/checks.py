"""Offline merger check commands; no application imports."""
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[5]
OUT = Path(__file__).resolve().parent
PYTHON = "/Users/jay/.t3/worktrees/pricerecon/t3-7260bb2e/.venv/bin/python"
ENV = {"PATH": "/Users/jay/.nvm/versions/node/v24.14.1/bin:/usr/bin:/bin", "PYTHONDONTWRITEBYTECODE": "1", "PYTHONPATH": f"{ROOT}/src:{ROOT}"}
receipt = json.loads((OUT.parent / "verification.json").read_text())
checks = []
for name, args in [
    ("mypy", next(c["command"][5:] for c in receipt["checks"] if c["name"] == "mypy final")),
    ("frontend-tests", ["npm", "--prefix", "frontend", "run", "test", "--", "--run"]),
    ("eslint", ["npm", "--prefix", "frontend", "run", "lint"]),
]:
    result = subprocess.run(args, cwd=ROOT, env=ENV, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    (OUT / f"{name}.log").write_text(result.stdout)
    checks.append({"name": name, "command": args, "environment": ENV, "exit_code": result.returncode, "artifact": f"{name}.log"})
    print(name, result.returncode, flush=True)
(OUT / "checks.json").write_text(json.dumps(checks, indent=2) + "\n")
static = (OUT.parent / "verify_static.py").read_text().replace('OUT = Path(__file__).resolve().parent', f'OUT = Path({str(OUT)!r})')
static = static.replace("sys.executable", repr(PYTHON))
exec(compile(static, str(OUT.parent / "verify_static.py"), "exec"), {"__name__": "__main__", "__file__": str(OUT.parent / "verify_static.py")})
