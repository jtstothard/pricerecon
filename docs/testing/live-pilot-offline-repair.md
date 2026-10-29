# Offline repair after the first bounded pilot — 2026-10-29

Based on integration `598d2dd` and the parent's
[first-run receipt](live-pilot-first-run.md). The parent receipt is unchanged.
The actual live grant remains consumed. This work made no live requests, read no
credentials/accounts, and changed no integration or production state.

## Candidate selection

The eBay pilot now chooses detail inspections using normalized title tokens:
Addiesdive, exact AD2066, mint and green; Casio plus the entire exact
MTP-B145D-2A2VEF reference, permitting spaces/hyphens between reference components.
Reference boundaries reject AD20660 and extended/different Casio suffixes.
Explicit strap/parts/accessory titles are excluded. There is no broader fallback.
The first two eligible candidates per subject are inspected; all five page leads
can still be retained. A title is only an inspection hint. The existing evidence
normalizer and qualification path remain the authority for identity and cost.

## Operator stop

The worker owns SIGINT/SIGTERM and cancels acquisition/UI work. Uvicorn does not
capture and re-raise those signals; cancellation closes its server before receipt
emission. Only a cancellation caused by that explicit stop becomes
`operator_stopped`; unrelated cancellation and arbitrary errors still propagate.
The outer CLI forwards signals to its supervisor. The supervisor forwards a stop
to the owned worker group and drains the sanitized receipt within at most two
seconds and the original deadline. A noncooperating worker is killed and reports
`operator_stop_failed`. Deadline/session loss still kill the group and clean the
marked directory; neither creates restart authority.

The supervisor only accepts counters from a zero-exit worker and its existing
allowlist. No merchant data, raw errors, IDs, titles, credentials or tokens are
forwarded. Consumed markers survive cleanup. SIGKILL/host failure cannot guarantee
cleanup or recover terminal counters.

## Verification and limits

TDD reproduced missing detail selection for reordered/punctuated titles and
missing terminal output after signals before applying fixes. Controlled tests use
normal connector search, worker CLI, real loopback uvicorn, supervisor and outer
CLI. They verify both signals, terminal counters, removed storage, closed listener,
non-restartable synthetic consumption, exact-reference rejection, two-detail caps,
abnormal-exit rejection, deadline and disconnect cleanup.

Existing activation CLI proof now controls its fixture grant path rather than
assuming the machine's real grant is unconsumed. It never resets the real marker.
The first broad test attempt also exposed the documented TMPDIR=/tmp requirement
for marked cross-process storage; final commands use it.

Validation uses the existing `t3-7260bb2e/.venv/bin/python`, `PYTHONPATH=src`, and
`TMPDIR=/tmp`. Frontend build is required for the unchanged application UI.
The dated outcome of each check is recorded in the results section below.

Offline proof does not establish provider title coverage, useful live detail
results, exact identity, an obtainable UK offer, delivered total, coupon success,
history or savings. A further live run needs separate scope and authorization;
this repair neither asks for one nor restores the consumed grant.

Commands:

```sh
TMPDIR=/tmp PYTHONPATH=src python -m pytest tests/test_live_pilot.py tests/test_pilot_activation.py tests/test_source_evidence_workflow.py tests/test_collection_workflow.py tests/test_discovery_workflow.py tests/test_shared_grant_workflow.py tests/test_ebay_oauth.py tests/test_ebay_startup_burst.py tests/test_ebay_secret_logging.py tests/test_rate_limiter.py -q --disable-warnings
PYTHONPATH=src python -m mypy src/pricerecon
python -m ruff check src/pricerecon/pilot.py src/pricerecon/pilot_bounds.py src/pricerecon/pilot_worker.py src/pricerecon/pilot_ui.py src/pricerecon/pilot_supervisor.py tests/test_live_pilot.py tests/test_pilot_activation.py
npm run build --prefix frontend
git diff --check
```

The touched eBay adapter has 23 existing Ruff findings. Comparing against
`git show 598d2dd:src/pricerecon/connectors/ebay.py` through Ruff's stdin interface
produced the same 23 rule/message pairs; this change adds none. The narrow pilot
lint command above passes without suppressions.

## Results — 2026-10-29

All commands ran in the repair worktree on `t3/pilot-search-signal-receipts`,
offline, against integration tip `598d2dd`. No live or network request to any
merchant or provider was made; no pilot worker or UI server was started; the
consumed grant marker was left untouched.

- `python -m pytest tests/test_live_pilot.py tests/test_pilot_activation.py
  tests/test_source_evidence_workflow.py tests/test_collection_workflow.py
  tests/test_discovery_workflow.py tests/test_shared_grant_workflow.py
  tests/test_ebay_oauth.py tests/test_ebay_startup_burst.py
  tests/test_ebay_secret_logging.py tests/test_rate_limiter.py -q
  --disable-warnings` (with `TMPDIR=/tmp PYTHONPATH=src`): **195 passed**,
  0 failed, 0 errors in 89.30 s; 11 warnings reported (summary suppressed by
  `--disable-warnings`, not inspected further).
- `python -m mypy src/pricerecon`: **Success: no issues found in 127 source
  files.** Mypy also printed a configuration note that several per-module
  `tests.*` sections in `pyproject.toml` are unused; the check itself passed.
- `python -m ruff check src/pricerecon/pilot.py src/pricerecon/pilot_bounds.py
  src/pricerecon/pilot_worker.py src/pricerecon/pilot_ui.py
  src/pricerecon/pilot_supervisor.py tests/test_live_pilot.py
  tests/test_pilot_activation.py`: **All checks passed.** The stdin comparison
  above was re-run during this recording: `598d2dd` and the working-tree
  `connectors/ebay.py` both produce the same 23 findings with identical
  rule/message pairs (empty diff).
- `npm run build --prefix frontend`: **succeeded** — `tsc` clean, vite built
  648 modules (index JS 687.15 kB, CSS 91.48 kB) in ~0.7 s, exiting with
  vite's advisory that some chunks exceed 500 kB after minification. That
  advisory predates this repair and the application UI is unchanged by it.
- `git diff --check`: clean (no whitespace-error output) before commit.

These results cover offline fixtures and builds only. They do not establish
provider title coverage, live detail results, identity, an obtainable UK offer,
delivered total, coupon success, history or savings, and they cannot prove the
SIGKILL/host-failure path where cleanup and terminal counters are not
guaranteed (see limits above and in the first-run receipt).
