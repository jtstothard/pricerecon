"""Fail if private deployment or task identifiers re-enter tracked files."""

from __future__ import annotations

import subprocess
import sys

PRIVATE_MARKERS = (
    "***REMOVED***",
    "192.168.10.",
    "***REMOVED***",
    "***REMOVED***",
    "***REMOVED***",
    "***REMOVED***",
    "***REMOVED***",
)

# Host and network names from the PR #142 adversarial review (B1-related
# topology finding). Names of this deployment only: container, image and
# product component names (cloakbrowser, gluetun, camofox, searxng) are
# public software names and deliberately NOT markers.
HOST_AND_NETWORK_MARKERS = (
    "proxmox1",
    "docker-app-vm",
    "media-vm",
    "media_back",
)

MARKERS = PRIVATE_MARKERS + HOST_AND_NETWORK_MARKERS

# Decision of 2026-10-29 (PR #142 adversarial review): the host/network names
# above already appear in exactly these tracked files, and those existing
# mentions are accepted as-is. Any other file — new or previously clean —
# introducing one of them fails the scan. Mentions are matched
# case-insensitively, so a capitalized variant is not a bypass.
ACCEPTED_MENTIONS = {
    "docs/FLARESOLVERR_DEPLOYMENT.md": {"media_back"},
    "docs/product/category-discovery/browser-readiness-check.md": {"media-vm"},
    "docs/product/category-discovery/byparr-live-check.md": {
        "proxmox1",
        "docker-app-vm",
        "media_back",
    },
    "docs/product/category-discovery/source-qualification-decision.md": {"media_back"},
    "docs/testing/live-pilot-parent-preflight.md": {"docker-app-vm"},
    "scripts/check_flaresolverr.sh": {"media_back"},
}


def line_markers(path: str, line: str) -> list[str]:
    """Return the markers one line of one tracked file trips, if any.

    Existing accepted mentions (see ACCEPTED_MENTIONS) do not count as
    violations for the host/network names.
    """
    hits = [marker for marker in PRIVATE_MARKERS if marker in line]
    lowered = line.lower()
    hits += [
        marker
        for marker in HOST_AND_NETWORK_MARKERS
        if marker in lowered and marker not in ACCEPTED_MENTIONS.get(path, ())
    ]
    return hits


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
        hits = line_markers(path, line)
        if hits:
            violations.append(f"{path}:{line_number}: [{', '.join(hits)}] {line.strip()}")

if violations:
    print("Private deployment/location markers found in tracked files:")
    print("\n".join(violations))
    sys.exit(1)
print("Public marker scan passed")
