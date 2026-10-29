# Bounded pilot runner — executable activation, 2026-10-28

The eligible path is implemented for parent review. No live token, search or detail
request has been made. Candidate input is `c8e745c245a0fe0535b1023fafc30367c9d4f605`;
parent integration is `5e26693cbe3f088392f4ed0727ee69c1ccdf3c3f`. Both histories
are retained. The approved [plan](live-pilot-plan.md) remains the envelope.

## Commands

Use the existing dependency environment and this checkout's absolute `src` on
`PYTHONPATH`. Build the unchanged frontend first (`npm run build --prefix frontend`).

```sh
# Zero provider calls; missing evidence yields blocked, requests:0.
PYTHONPATH=src python -m pricerecon.pilot
PYTHONPATH=src python -m pricerecon.pilot --execute

# Synthetic supervised normal acquisition; choose a NEW /tmp directory.
PYTHONPATH=src python -m pricerecon.pilot --offline-check /tmp/pricerecon-pilot-offline-UNIQUE

# Validate session evidence review, credential presence and build without executing.
PYTHONPATH=src python -m pricerecon.pilot \
  --review /external/review.json

# PARENT ONLY after review: existing authorized secret route injects the documented
# EBAY_APP_ID and EBAY_CERT_ID environment variables in memory. No values in argv.
PYTHONPATH=src python -m pricerecon.pilot --execute \
  --review /external/review.json
```

The last command performs macOS exclusion checks before consuming the grant or
making provider calls, then invokes `acquire_once` with the real HTTPX transport.
`acquire_once` invokes ordinary `execute_discovery` → `acquire_sources` → eBay
connector/evidence normalizer → normal identity/cost projection and SQLite capture.
No synthetic data enters that path. There is no force flag or alternative source.

During execution open **http://127.0.0.1:8878/discover**; the existing comparison and
product UI reads only the temporary database. Port 8878 must be free. No application
lifespan, scheduler, watch executor or notification transport is started. Only GET
routes are mounted; mutation/export/acquisition routes are unavailable. Host and
Origin checks reject foreign origins. CSP blocks remote images and connections.
Responses are `no-store`; the session script clears the page at deadline or server
loss. A blocked preflight starts no server. Stop with Ctrl-C or let the bounded
session expire; the independent supervisor removes the entire marked run directory.

## Active-session evidence review

The parent reviews endpoint-specific eBay staff guidance and API licence transient-use/retention
source content in the approved active session, then supplies the review manifest
and exact document files. No outside reviewer or signing infrastructure is needed.
The manifest is an auditable review record, never provider permission itself.
Buyer approval of the pilot does not establish eBay entitlement. Standard search and single getItem need no separate app approval under the exact
staff guidance below. Restricted getItems/watchCount are excluded. Tests use
fictional document bytes and credentials, never provider permission.

External `review.json` is strict JSON with these fields:

| Field | Required binding |
| --- | --- |
| `schema` | `pricerecon.pilot-review.v1` |
| `app_sha256` | SHA256 of the exact existing app ID supplied by the secret route |
| `purpose` | `watch-pilot-2026-10-28-once` |
| `envelope_sha256` | SHA256 of the exact approved `live-pilot-plan.md` bytes |
| `reviewer` | Non-secret parent/session review reference |
| `reviewed_at` | Timezone-aware actual review time, not in the future |
| `source_use` | `eBay Browse UK transient comparison display` |
| `expires_at` | Timezone-aware expiry of this session review/source permission |
| `operator_started_at` | Actual attended execution/review start; timezone-aware, no future timestamp |
| `retention_seconds` | Source-permitted session retention, integer 1–1200; never inferred from buyer approval |
| `documents` | Exactly two entries, kinds `endpoint_access` and `transient_use` |

Each document has `reviewed_scope` (what the source content actually permits), `file` (relative to the external manifest directory), `sha256`
(exact reviewed bytes), and `issuer` (the exact reviewed public source URL).
For `endpoint_access`, only these eBay Developer Support staff replies are accepted:

- https://community.ebay.com/forum/browse-57957/topic/browse-api-468324/
- https://community.ebay.com/forum/search-api-57966/topic/request-app-check-access-for-account-in-browse-prod-467069/

For `transient_use`, only https://developer.ebay.com/join/api-license-agreement
is accepted. No arbitrary forum post, generic Buy requirement, URL prefix or
app-specific approval assertion substitutes for those documents. An issuer URL
alone is not evidence: the exact reviewed bytes must exist and match their hashes.
Missing, changed, oversized or escaping document paths fail.

`reviewed_scope` records the parent's interpretation, not a provider grant:
standard search/single getItem with client-credentials OAuth only; necessary
limited intermediate copies under licence §3.1; private one-off display and deletion
when no longer needed, bounded by 1200 seconds and the shorter session deadline.
No category averages/aggregates, history, public commingling, getItems or watchCount.
Listing display must stay within the six-hour freshness rule (§8.1.3); this is not
an archive licence. The minimal durable receipt contains no merchant content.

A concrete external manifest can now use saved copies of those actual public
documents: `endpoint_access` points to either staff page, `transient_use` to the
licence, each with its exact file SHA256. Bind `app_sha256` to the actual existing
app in the parent's authorized credential route (not a sample fingerprint), and
`envelope_sha256` to the current plan bytes. Supply actual attended session times,
reviewer reference, expiry and retention. No email/account approval or extra review
service is required. Do not reuse fictional test bytes as public evidence.

Manifest is capped at 16KiB and each reviewed document at 2MiB. App, purpose, exact envelope, expiry, source retention and operator budget
are checked again in the supervisor/worker before acquisition. Absent or invalid
review never triggers credential acquisition or provider calls. The ordinary
source/policy receipt carries the review digest rather than an invented authority.

## Concrete current-platform containment

Only macOS `/private/tmp/pricerecon-pilot-<unique>.noindex` is supported for live
storage. It sits outside this repository, home/cloud-sync roots and repo artifact
pipelines. Before any merchant data exists, the worker applies the Time Machine
exclusion xattr and verifies `/usr/bin/tmutil isexcluded` reports `[Excluded]`.
Spotlight exclusion uses macOS's `.noindex` directory convention. The worker checks
actual running process executable names, configured user/system launchd jobs and user crontab for restic, borg, rclone, Arq, Backblaze,
Dropbox, OneDrive, Syncthing, Duplicati and Carbonite. A detected tool blocks until
its applicable exclusion is implemented; hypothetical pipelines are not blockers.
This scope does not claim omniscience about unknown custom backup jobs. The parent
must not execute under an additional known exporter/indexer outside this scope.
No confidential data is written outside the temporary root.

Current-machine verification applied/queried the exclusion on a new empty temp
directory and removed it: Time Machine excluded; `.noindex` path; no listed
third-party backup/sync process or configured launchd/cron job detected. `tmutil addexclusion` initially timed out;
the implementation instead writes the standard exclusion xattr using `/usr/bin/xattr`
and verifies with `tmutil isexcluded`. It makes no infrastructure changes.

All original caps remain: two exact queries, five leads per page, two details per
subject, seven eBay attempts including one memory-only token, no retry/fallback,
redirect, concurrent request, browser acquisition, AI, paid route, scheduler or
notification. Streaming bodies: 2MiB/response and 8MiB aggregate; normalized reports:
2MiB; logs: 1MiB; DB: 32MiB; physical run directory: below 50MiB. SQLite routes use
the bounded connection boundary, memory journals/temp tables, capped pages, denied
ATTACH/storage pragmas. The audit guard denies other writes, subprocesses and
network egress except resolved api.ebay.com:443 and the loopback UI listener.
Raw responses and credentials stay in memory. Production DB/config is never read.

The shorter of 1200 seconds, external retention, review expiry and remaining
1800-second operator window bounds the worker and independent supervisor. Session
loss stops the process group. The durable exclusive, fsynced consumed marker is
`~/.local/state/pricerecon/watch-pilot-2026-10-28.consumed`, contains no merchant or
secret data, survives run cleanup, and is shared across directories and restarts.
No CLI override/refill is available. Interruption or failure after consumption
requires the parent to report the consumed grant, never delete it to retry.
Host failure/SIGKILL of the cleanup owner cannot establish deletion or restart rights.

## Actual remaining external prerequisites

1. Parent records review of the actual allowlisted staff guidance and API licence
   through the existing active-session manifest. This records standard endpoint
   access and bounded use interpretation, not a new app-specific grant.
2. Existing authorized `EBAY_APP_ID` and `EBAY_CERT_ID` credentials, supplied via
   the documented secret route. The runner checks presence only during preflight;
   no production DB or credential discovery is required. Parent uses T3
   `request_secret` if needed, never raw chat.
3. A frontend build and supported macOS temporary-storage/exclusion checks at
   activation, plus an unconsumed one-off grant and an attended execution.
   Real provider behavior and buyer usefulness remain unproven until that run.

Missing evidence returns a blocked preflight; it cannot be bypassed with a force
flag. Source-only verification does not satisfy these live prerequisites.

## Offline verification

Review-fix TDD reproduced the session-review gate, terminal UI exposure,
discarded detail evidence, and per-item failures before changing implementation.
Tests use normal acquisition/public CLI and read-only API seams with controlled
provider transports. The eligible worker test controls the platform-exclusion
edge; it does not claim native exclusion acceptance. It exercises actual loopback
UI startup and normal feed/product reads without spending the live grant.

Second-query 403, 429, HTTP failure and response cap controls follow a successful
first capture and prohibit UI creation, then verify the entire run directory is
removed. Malformed summary/detail and mismatched-detail controls preserve valid
siblings, mark receipt completeness partial, and count only accepted detail
evidence. Detail item specifics retain seller provenance and cannot establish a
manufacturer definition, selected variation or delivered total.

See `docs/testing/artifacts/live-pilot-review-fixes/verification.json` for the
current source-only checks. No live-source acceptance is inferred.

## First-run follow-up — 2026-10-29

The [actual first-run receipt](../../testing/live-pilot-first-run.md) supersedes
historical unconsumed/not-started status above. The grant is consumed; these
commands do not authorize another live run. See the
[offline selector and operator-stop repair](../../testing/live-pilot-offline-repair.md)
for source verification and remaining live limitations.
