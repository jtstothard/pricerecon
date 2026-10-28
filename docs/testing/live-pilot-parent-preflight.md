# Parent live-pilot preflight — 2026-10-28

Reviewed integration: `e4eeccb8eb65b224c52e32522b7680cb93470a70`.
User-approved envelope and autonomous continuation are retained in
[live-pilot-plan.md](../product/category-discovery/live-pilot-plan.md).

## Actual result

Parent invoked the merged executable with existing project Python and
`PYTHONPATH=src`: `python -m pricerecon.pilot --execute`.

```json
{"schema":"pricerecon.watch-pilot.v1","state":"blocked","gates":["ebay_app_approval_unproven","ebay_transient_retention_unproven","backup_exclusion_unproven"],"requests":0}
```

This is a real parent preflight outcome, not a live API attempt. Backup exclusion
is not tested by the no-review fast path; it is not an observed exclusion failure.
Local environment presence only: EBAY_APP_ID=false, EBAY_CERT_ID=false. No secret
values were read or printed. Shared live grant marker is absent/unconsumed.
Repository named approval/entitlement/pilot files supply historical access
receipts and policy requirements, not a genuine app-specific permission document
or active-session review that can substantiate it. The previous successful API
probe and fictional test documents were not promoted into that evidence.
No token/search/detail/provider call, production DB operation, buyer-fixture
change, account operation or notification was made. No request budget was spent.

## Implemented versus external

The original twelve tickets are accepted within their defined offline scope.
The approved pilot runner is implemented, independently reviewed and merged;
131 candidate tests, 24 merged tests, full-source mypy and focused lint/diff checks
are recorded in [merger recheck](live-pilot-merger-recheck.md).
All four review findings are repaired. Eligible execution, transient UI, caps,
source normalization and cleanup are covered by controlled tests, not live proof.

Live pilot execution remains blocked on genuine existing app approval/intended
use and transient capture/display/deletion evidence. Credentials can be injected
through the existing authorized route once that evidence is established. Codex
has session approval; no further routine buyer approval is requested. Do not
forge provider evidence, consume the grant speculatively or replace the approved
route with a different source. Retained private comparison walkthrough remains
synthetic and no production activation occurred.

## Cleanup

Removed the three clean, merged implementation worktrees: t3-916dd165,
t3-b4328045 and t3-1b33f8ff, preserving branches/commits. Inspected ignored
contents: tool/Python/build caches and a zero-byte ordinary pricerecon.db in the
first checkout (no tables, no symlink, single link). No untracked user contents
were removed. Main, integration, original dirty planning and unrelated research
checkouts are retained. Integration is clean after this receipt commit.
