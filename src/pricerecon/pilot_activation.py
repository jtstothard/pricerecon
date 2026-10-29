"""Auditable parent-session review of endpoint-access and transient-use provider evidence.

This records a review, never creates provider permission. The parent reviews
source document content and supplies the manifest through the approved session.
No external reviewer, signing service or key infrastructure is required.
"""

import hashlib
import os
import plistlib
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

PURPOSE = "watch-pilot-2026-10-28-once"
PLAN = Path(__file__).resolve().parents[2] / "docs/product/category-discovery/live-pilot-plan.md"
GRANT = Path.home() / ".local/state/pricerecon/watch-pilot-2026-10-28.consumed"


class ReviewError(ValueError):
    """Sanitized fail-closed external prerequisite."""


# Exact reviewed primary sources only; this is not trust in arbitrary forum posts.
ENDPOINT_ACCESS_SOURCES = frozenset(
    {
        "https://community.ebay.com/forum/browse-57957/topic/browse-api-468324/",
        "https://community.ebay.com/forum/search-api-57966/topic/request-app-check-access-for-account-in-browse-prod-467069/",
    }
)
TRANSIENT_USE_SOURCE = "https://developer.ebay.com/join/api-license-agreement"


class Document(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["endpoint_access", "transient_use"]
    file: str = Field(min_length=1, max_length=200)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    reviewed_scope: str = Field(min_length=1, max_length=2000)
    issuer: str = Field(min_length=1, max_length=1000)


class ReviewedEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal["pricerecon.pilot-review.v1"] = Field(alias="schema")
    app_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    purpose: Literal["watch-pilot-2026-10-28-once"]
    envelope_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    reviewer: str = Field(min_length=1, max_length=200)
    source_use: Literal["eBay Browse UK transient comparison display"]
    reviewed_at: datetime
    expires_at: datetime
    operator_started_at: datetime
    retention_seconds: int = Field(strict=True, ge=1, le=1200)
    documents: list[Document] = Field(min_length=2, max_length=2)

    def remaining_seconds(self) -> float:
        now = datetime.now(UTC)
        return min(
            1200,
            self.retention_seconds,
            (self.expires_at - now).total_seconds(),
            1800 - (now - self.operator_started_at).total_seconds(),
        )


def envelope_digest() -> str:
    return hashlib.sha256(PLAN.read_bytes()).hexdigest()


def bounded_read(path: Path, cap: int) -> bytes:
    with path.open("rb") as stream:
        data = stream.read(cap + 1)
    if len(data) > cap:
        raise ReviewError("review_size_denied")
    return data


def resolve_review(manifest: Path, app_id: str) -> ReviewedEvidence:
    """Bind the session review to exact documents, app, purpose and finite use.

    Hashes establish document integrity, not entitlement. The reviewer must
    assess the staff guidance for standard search/getItem and licence terms for
    necessary intermediate copies/private display with prompt deletion. This is
    not app-specific approval, restricted endpoint access or a history grant.
    """
    try:
        raw = bounded_read(manifest, 16384)
        review = ReviewedEvidence.model_validate_json(raw)
        now = datetime.now(UTC)
        if (
            not app_id
            or review.app_sha256 != hashlib.sha256(app_id.encode()).hexdigest()
            or review.envelope_sha256 != envelope_digest()
            or review.reviewed_at.tzinfo is None
            or review.reviewed_at > now
            or review.reviewed_at > review.expires_at
            or review.expires_at.tzinfo is None
            or review.operator_started_at.tzinfo is None
            or review.operator_started_at > now
            or review.remaining_seconds() <= 0
            or {doc.kind for doc in review.documents} != {"endpoint_access", "transient_use"}
        ):
            raise ReviewError("review_binding_or_expiry_invalid")
        for doc in review.documents:
            allowed = (
                ENDPOINT_ACCESS_SOURCES
                if doc.kind == "endpoint_access"
                else frozenset({TRANSIENT_USE_SOURCE})
            )
            if doc.issuer not in allowed:
                raise ReviewError("review_document_source_invalid")
            path = (manifest.parent / doc.file).resolve()
            if not path.is_relative_to(manifest.parent.resolve()) or path == manifest.resolve():
                raise ReviewError("review_document_path_invalid")
            if hashlib.sha256(bounded_read(path, 2 * 1024 * 1024)).hexdigest() != doc.sha256:
                raise ReviewError("review_document_changed")
        return review
    except (OSError, subprocess.SubprocessError, ValidationError, TypeError) as exc:
        raise ReviewError("external_review_unverifiable") from exc


def credential_metadata() -> dict[str, bool]:
    """Only presence metadata from the documented local/dev environment route."""
    return {name: bool(os.environ.get(name)) for name in ("EBAY_APP_ID", "EBAY_CERT_ID")}


def prepare_excluded_root(root: Path) -> dict[str, str]:
    """Current supported platform: macOS local /private/tmp, no cloud/repo roots.

    Time Machine exclusion is set and queried before any confidential writes.
    Spotlight's .noindex directory convention is required. Active known third
    party backup/sync tooling blocks pending its specific exclusion adapter;
    this is a scoped inspection, not a claim about all conceivable pipelines.
    """
    if sys.platform != "darwin" or root.parent.resolve() != Path("/private/tmp"):
        raise ReviewError("macos_private_tmp_required")
    if not root.name.startswith("pricerecon-pilot-") or not root.name.endswith(".noindex"):
        raise ReviewError("spotlight_noindex_required")
    processes = subprocess.run(
        ["/bin/ps", "-axo", "comm="], capture_output=True, text=True, timeout=5, check=True
    ).stdout.lower()
    tools = (
        "restic",
        "borg",
        "rclone",
        "arq",
        "backblaze",
        "dropbox",
        "onedrive",
        "syncthing",
        "duplicati",
        "carbonite",
    )
    if any(tool in processes for tool in tools):
        raise ReviewError("active_backup_sync_tool_needs_exclusion_adapter")
    # Include configured launchd jobs, which can run during the session even
    # when their executable was absent from the process snapshot. Only inspect
    # tooling metadata; never retain or print job arguments/environment values.
    for directory in (
        Path.home() / "Library/LaunchAgents",
        Path("/Library/LaunchAgents"),
        Path("/Library/LaunchDaemons"),
    ):
        if not directory.exists():
            continue
        for job in directory.glob("*.plist"):
            try:
                config = plistlib.loads(bounded_read(job, 131072))
                if not isinstance(config, dict):
                    raise ReviewError("launch_tool_inventory_unverifiable")
                command = str(config.get("Program", "")) + str(config.get("ProgramArguments", []))
                if any(tool in (job.name + command).lower() for tool in tools):
                    raise ReviewError("configured_backup_sync_tool_needs_exclusion_adapter")
            except (OSError, plistlib.InvalidFileException) as exc:
                raise ReviewError("launch_tool_inventory_unverifiable") from exc
    cron = subprocess.run(
        ["/usr/bin/crontab", "-l"],
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
    )
    if cron.returncode not in (0, 1) or len(cron.stdout) > 131072:
        raise ReviewError("cron_tool_inventory_unverifiable")
    if any(tool in cron.stdout.lower() for tool in tools):
        raise ReviewError("configured_backup_sync_tool_needs_exclusion_adapter")
    subprocess.run(
        [
            "/usr/bin/xattr",
            "-wx",
            "com.apple.metadata:com_apple_backup_excludeItem",
            plistlib.dumps("com.apple.backupd", fmt=plistlib.FMT_BINARY).hex(),
            str(root),
        ],
        capture_output=True,
        timeout=5,
        check=True,
    )
    result = subprocess.run(
        ["/usr/bin/tmutil", "isexcluded", str(root)],
        capture_output=True,
        text=True,
        timeout=5,
        check=True,
    )
    if not result.stdout.startswith("[Excluded]"):
        raise ReviewError("time_machine_exclusion_unverified")
    return {
        "time_machine": "excluded",
        "spotlight": ".noindex",
        "location": "local_private_tmp",
        "active_third_party_backup_sync": "none_detected",
        "configured_launchd_cron_backup_sync": "none_detected",
    }
