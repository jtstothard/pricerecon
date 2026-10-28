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

# Validate independent review, credential presence and build without executing.
PYTHONPATH=src python -m pricerecon.pilot \
  --review /external/review.json --reviewer-key /external/reviewer.pem \
  --reviewer-key-sha256 TRUSTED_INDEPENDENT_PEM_SHA256

# PARENT ONLY after review: existing authorized secret route injects the documented
# EBAY_APP_ID and EBAY_CERT_ID environment variables in memory. No values in argv.
PYTHONPATH=src python -m pricerecon.pilot --execute \
  --review /external/review.json --reviewer-key /external/reviewer.pem \
  --reviewer-key-sha256 TRUSTED_INDEPENDENT_PEM_SHA256
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

## Independent review interface

There is **no trusted key bundled in this repo**. The parent must establish the
reviewer's public-key SHA256 through its independent review channel, not copy a pin
from the manifest. The reviewer must examine genuine app-specific eBay approval
and transient-use/retention evidence. A signature authenticates that review; it
cannot create eBay entitlement. Do not sign a locally written assertion as if it
were provider approval. The implementation creates no review, signing key or
entitlement artifact. The controlled tests use explicitly fictional documents.

External `review.json` is strict JSON with these fields:

| Field | Required binding |
| --- | --- |
| `schema` | `pricerecon.pilot-review.v1` |
| `app_sha256` | SHA256 of the exact existing app ID supplied by the secret route |
| `purpose` | `watch-pilot-2026-10-28-once` |
| `envelope_sha256` | SHA256 of the exact approved `live-pilot-plan.md` bytes |
| `expires_at` | Timezone-aware expiry of this independent review/source permission |
| `operator_started_at` | Actual attended execution/review start; timezone-aware, no future timestamp |
| `retention_seconds` | Source-permitted session retention, integer 1–1200; never inferred from buyer approval |
| `documents` | Exactly two entries, kinds `app_approval` and `transient_use` |

Each document has `file` (relative to the external manifest directory), `sha256`
(exact reviewed bytes), and `issuer` (the actual `https://developer.ebay.com/…`
source reference). The app approval evidence must bind the app and intended Browse
UK use; transient-use evidence must cover capture, required normalized fields,
session display, deletion, and the minimal permanent receipt. An issuer URL alone
is not evidence. Missing, changed, oversized or escaping document paths fail.

`review.json.sig` is an external reviewer's RSA/SHA256 signature of the exact raw
manifest bytes, verifiable with `openssl dgst -sha256 -verify reviewer.pem
-signature review.json.sig review.json`. No private review key enters the runner.
Manifest is capped at 16KiB, public key/signature at 8KiB, each reviewed document
at 2MiB. App, purpose, exact envelope, expiry, source retention and operator budget
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

1. Genuine app-specific approval/use/retention documents and independently trusted
   reviewer signature/pin have not been supplied. No entitlement is claimed.
2. Existing local/dev environment presence inspection returned `EBAY_APP_ID=false`,
   `EBAY_CERT_ID=false`. Parent must use the existing documented authorized secret
   route; if needed, parent uses T3 `request_secret`, never raw chat. No production
   commands or production DB reads were used to look for credentials.
3. Parent review and one attended execution under the shared grant remain pending.
   Real provider behavior and buyer usefulness remain unproven until that run.

Backup/temp containment has a working, locally checked path; it is rechecked at
execution. Missing external evidence does not leave activation code unwired.

## Offline verification

TDD red results preceded review resolver and UI implementation. Tests exercise
signed eligible and absent/mismatched/expired/changed evidence, normal connector
and discovery projection, actual macOS exclusion, controlled eligible worker CLI,
read-only UI feed/product route, denied mutation/export/foreign host, memory-only
token, shared non-refilling grant, physical/body limits, cleanup and supervisor
expiry. Controlled eligible flow uses five attempts (token, two searches, two
details); it does not spend the live grant. No live provider calls, push, PR,
deployment, account action or production mutation occurred.

Final checks: **92 passed** in the affected pilot/collection/shared-grant/discovery/
source-evidence/secret-logging regression run. After the final activation/deadline
additions, **19 passed** in both pilot test modules (including a real loopback
server startup under the guard and refusal to reuse the live fixture grant).
Ruff passes all changed Python files; mypy passes all 15 changed source modules;
frontend TypeScript/Vite build and `git diff --check` pass. Existing Pydantic
deprecation warnings remain. No live-source acceptance is inferred.
