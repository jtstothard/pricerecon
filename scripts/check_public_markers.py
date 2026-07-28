"""Fail if private deployment or task identifiers re-enter tracked files."""

from __future__ import annotations

import subprocess
import sys

MARKERS = (
    "***REMOVED***",
    "192.168.10.",
    "***REMOVED***",
    "***REMOVED***",
    "***REMOVED***",
    "***REMOVED***",
    "***REMOVED***",
)

tracked = (
    subprocess.run(["git", "ls-files", "-z"], check=True, capture_output=True, text=False)
    .stdout.decode()
    .split("\0")
)
violations: list[str] = []
for path in filter(None, tracked):
    if path == "scripts/check_public_markers.py" or path.startswith("tests/fixtures/"):
        continue
    try:
        text = open(path, encoding="utf-8").read()
    except (OSError, UnicodeDecodeError):
        continue
    for line_number, line in enumerate(text.splitlines(), 1):
        if any(marker in line for marker in MARKERS):
            violations.append(f"{path}:{line_number}: {line.strip()}")

if violations:
    print("Private deployment/location markers found in tracked files:")
    print("\n".join(violations))
    sys.exit(1)
print("Public marker scan passed")
