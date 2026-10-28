# Bounded pilot runner — implementation receipt, 2026-10-28

Status: offline containment prepared for parent review. Live acquisition is blocked.
The buyer-approved numerical plan is [live-pilot-plan.md](live-pilot-plan.md).
Integration input: `5e26693cbe3f088392f4ed0727ee69c1ccdf3c3f`.
No live provider documentation, credential, token, search, detail, browser, production,
VM, notification, account or purchase requests were made by this implementation.
No push, PR or deployment was performed.

## Commands

Use an existing Python environment with the repository dependencies; set
`PYTHONPATH` to this checkout's absolute `src` directory when running elsewhere.

```sh
PYTHONPATH=src python -m pricerecon.pilot
PYTHONPATH=src python -m pricerecon.pilot --execute
PYTHONPATH=src python -m pricerecon.pilot --offline-check /tmp/pricerecon-pilot-offline-UNIQUE
```

Default and `--execute` currently return the same zero-request blocked preflight.
They do not load credentials, create storage, or spend the shared live grant.
`--offline-check` is explicitly synthetic. It starts a separate deadline/cleanup
owner and exercises the ordinary `acquire_sources` lifecycle, eBay connector,
Browse evidence normalizer and OperatingPolicy/DurableAdmission ledger. It is
not live evidence or a replacement raw API probe. A consumed tombstone survives
outside the deleted run directory; the same run path cannot be resumed/refilled.
Different synthetic test directories are independent offline fixtures, not new
live grants. The production scheduler and buyer walkthrough fixture are untouched.

## Enforced offline

- Exact queries: `Addiesdive AD2066 Mint Green`, `Casio MTP-B145D-2A2VEF`.
  One search page of five leads each; up to two details per subject selected by
  exact query text, new condition and fixed-price evidence, never price ranking.
  Search text does not prove selected variation. Details validate the same item;
  neither detail presence nor GBP display upgrades identity or UK delivered cost.
- One memory-only token shared by both connector lifecycles; seven eBay attempts,
  two pages, four details, zero retries/fallbacks, parallel requests, browsers,
  AI routes, notifications or recurring refresh. HTTP redirects/non-2xx stop the
  lane. Only HTTPS api.ebay.com token, exact search and admitted item routes pass.
  Environment proxies are disabled. No production connector config is inherited.
- Response bodies are streamed in 64KiB chunks, limited to 2MiB per response and
  8MiB aggregate. Non-identity content encodings are rejected before decoding to
  avoid decompression amplification. An over-limit chunk is counted as observed
  bytes and refused before accumulation; no retry follows. Normalized report
  bytes are limited to 2MiB aggregate before release to acquisition callers.
- The isolated SQLite boundary limits the only database to 32MiB (8192 4KiB
  pages), uses memory journals/temp tables and rejects ATTACH or storage pragma
  changes. Python file writes/new directories/links/renames and external process
  creation are denied after setup. The marked run directory therefore has one
  capped DB plus its small marker, below the 50MiB ceiling; no disk logs, token
  store, WAL, exports or raw response archives. Audit guards reject alternate DB
  paths and direct SQLite connections outside the bounded connection boundary.
- Each sequential source attempt reserves 600 seconds in the existing ledger;
  the whole process is bounded to 1200 seconds by a separate supervisor even if
  the event loop stalls. The supervisor kills the worker process group and
  removes marked DB/WAL/temp storage at expiry/failure. It stops when its invoking
  CLI process disappears. Host failure/SIGKILL of the cleanup owner cannot prove
  deletion and never establishes permission to restart.
- Worker logs are disabled. Supervisor output is capped to 1MiB in memory and
  only known receipt states and nonnegative aggregate counters are forwarded.
  No arbitrary exception/provider text crosses the permanent receipt boundary.

## Prerequisites still absent

The repository records requirements and previous source checks, not app-specific
entitlement. Preflight truthfully returns:

```json
{"schema":"pricerecon.watch-pilot.v1","state":"blocked","gates":["ebay_app_approval_unproven","ebay_transient_retention_unproven","backup_exclusion_unproven"],"requests":0}
```

Parent must independently establish all of the following before live activation:

| Required evidence | What must be established |
| --- | --- |
| Existing app identity and approval/contract pointer | The existing production app is approved for this Browse UK intended use; prior HTTP success is insufficient |
| Source-specific transient use/retention pointer | Capture, session display, necessary normalized fields, permitted duration, deletion and minimal permanent receipt are covered; 20 minutes is only the buyer ceiling |
| Actual backup/export/index exclusion proof | The eventual marked temporary path is excluded from every applicable repository/backup/export/index pipeline; `gitignore` or Time Machine alone is insufficient |
| Active owner and elapsed operator effort | Session remains attended and execution/review stay within the 30-minute allowance |
| One shared live grant | Durable consumed marker/receipt and fixed scope survive deletion; no parallel parent/child run or second grant after interruption |

There is deliberately no local approval JSON, evidence string, boolean or CLI
force switch that can turn these unknowns green. The checked-in CLI has no live
activation resolver yet: its only executable worker entry is the controlled
synthetic proof. `acquire_once` accepts an explicit source, transport and policy
and uses the real application seam, but is not itself a live authorization API.
After actual source evidence is reviewed, the parent must wire/verify the eligible
live activation to that seam, bind credential acquisition through the existing
secret route, and establish backup/session/grant evidence. Do not call the worker
with a live transport to bypass preflight. This remaining activation work is
**blocked**, not complete, and the pilot has not acquired or displayed offers.
No local private offer UI or buyer/live usefulness proof is claimed.

## Verification

Public test seams: blocked CLI/preflight, controlled HTTP transport, public eBay
connector lifecycle, ordinary acquisition lifecycle with marked temporary SQLite,
SQLite connection boundary, and process supervisor. These implement the seams
explicitly requested in the task. The TDD skill and engineering standard were read;
red results were observed before implementing the missing boundaries.

Validation: **108 passed** across pilot, collection, shared-grant, discovery,
source-evidence, eBay secret-logging and rate-limiter modules with `TMPDIR=/tmp`.
The final expanded pilot module separately passed **12 tests**, including the
exact documented `/tmp` CLI command. The single earlier sanitized-temp mismatch
passed its targeted rerun; no assertion or safety check was weakened. Mypy passes
all 11 changed source files. New files/tests pass Ruff and Black; existing touched
files retain **34 baseline Ruff findings, zero added**. Whitespace checks pass.

Minimal retained receipts: [blocked preflight](../../testing/artifacts/live-pilot-runner/preflight.json),
[controlled supervised run](../../testing/artifacts/live-pilot-runner/offline-receipt.json),
and [verification summary](../../testing/artifacts/live-pilot-runner/verification.json).
These contain no merchant data or credentials. The regression run's macOS temporary-directory mismatch was
rechecked with `TMPDIR=/tmp`, matching the child harness's sanitized environment.
Source terms, actual backup exclusions, real auth/normalization, UI usefulness and
operator-time observation remain unproven by these controlled tests.
