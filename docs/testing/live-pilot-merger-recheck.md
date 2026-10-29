# Sole merger recheck — 2026-10-28

Candidate `2e35d725eec94b1fa9bec954e29f606cf137f4fc` was independently reviewed
against `5e26693cbe3f088392f4ed0727ee69c1ccdf3c3f`, using the two original
review reports, approved live-pilot plan, runner and repair receipts,
CONTRIBUTING and engineering standard. No delegates were used.

## Standards

No concrete blocker found. The malformed-summary, malformed-detail and mismatched
detail controls retain valid siblings, report partial coverage, count accepted
details separately from attempted requests, and never replace rejected details
with summaries. Shared SQLite routing preserves ordinary behavior outside the
isolated context. Acquisition defaults and transport changes were checked with
collection, shared-grant, discovery, rate-limiter and legacy eBay regressions.

## Spec

No concrete blocker found. All four previous findings were independently checked:

- PKI is removed. Active-session review binds exact app, approved envelope,
  purpose, expiry and two actual document files. Hashes prove integrity, not
  entitlement; the parent must read genuine provider content and assess scope.
- Second-query denial/429/failure/body cap skips UI and enters worker cleanup;
  controlled CLI tests verify removal of the marked run directory.
- Matching details enter the normal evidence path with item-detail route,
  endpoint and locators. Seller aspects remain seller assertions; shipping and
  destination evidence do not establish selected variation or delivered total.
- Invalid items retain valid siblings with explicit issues and partial counts.

## Verification and merge

Python: `/Users/jay/.t3/worktrees/pricerecon/t3-7260bb2e/.venv/bin/python`.
Commands below use that interpreter as `python`, from the relevant checkout.

Candidate: **131 passed, 11 warnings**, using:

```sh
TMPDIR=/tmp PYTHONPATH=src python -m pytest -q tests/test_live_pilot.py tests/test_pilot_activation.py tests/test_source_evidence_workflow.py tests/test_collection_workflow.py tests/test_discovery_workflow.py tests/test_shared_grant_workflow.py tests/test_ebay_oauth.py tests/test_ebay_startup_burst.py tests/test_ebay_secret_logging.py tests/test_rate_limiter.py --disable-warnings
PYTHONPATH=src python -m mypy src/pricerecon
python -m ruff check src/pricerecon/pilot.py src/pricerecon/pilot_activation.py src/pricerecon/pilot_bounds.py src/pricerecon/pilot_supervisor.py src/pricerecon/pilot_ui.py src/pricerecon/pilot_worker.py src/pricerecon/db/connection.py tests/test_live_pilot.py tests/test_pilot_activation.py
```

Mypy passed 127 source files; focused Ruff passed. An initial test invocation
named nonexistent `tests/test_ebay_evidence.py` and collected nothing; the corrected
command above passed. This is not a live-source verification claim.

Clean integration at the expected base received a `--no-ff` merge:
`93cc6628d5c0d1a8e32ba3f972cfaec1df91f2ba`. Its tree and candidate tree both
equal `12958186f4992f22bbdf191255401700fd91a009`; exact diff and whitespace
checks passed before this documentation receipt was added.

Merged focused command: **24 passed, 11 warnings**.

```sh
TMPDIR=/tmp PYTHONPATH=src python -m pytest -q tests/test_live_pilot.py tests/test_pilot_activation.py --disable-warnings
```

## Eligibility and remaining live gate

Source/offline implementation is accepted. The original twelve tickets remain
complete only within their accepted offline scope. Live follow-on remains
unexecuted and gated; neither this merge nor fictional test documents grant
provider permission or establish buyer acceptance.

Parent must review genuine app-specific eBay Browse UK approval and transient
capture/display/deletion/minimal-receipt permission. Supply exact reviewed files
and manifest as specified in `docs/product/category-discovery/live-pilot-runner.md`:
app hash, exact plan hash, purpose, session reviewer/time, finite source expiry,
operator start, retention seconds and two document hashes/paths/source references.
Use only the existing authorized secret route for EBAY_APP_ID/EBAY_CERT_ID;
values must not enter argv, logs or receipts. Build the frontend, keep port 8878
free, and verify the one-off grant is unconsumed. The worker must verify actual
macOS exclusions before acquisition; detected backup/sync tooling without an
applicable exclusion blocks execution.

```sh
npm run build --prefix frontend
PYTHONPATH=src python -m pricerecon.pilot --review /external/review.json
# Only after genuine preflight/evidence eligibility, parent executes:
PYTHONPATH=src python -m pricerecon.pilot --execute --review /external/review.json
```

No live provider calls, credential inspection, account/contact action, production
mutation, push or PR occurred in this review. Parent owns genuine preflight and
worktree cleanup. Candidate and original dirty checkout were not edited.
