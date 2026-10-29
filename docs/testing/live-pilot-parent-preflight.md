# Parent live-pilot preflight — 2026-10-28

Reviewed integration: `e4eeccb8eb65b224c52e32522b7680cb93470a70`.
User-approved envelope and autonomous continuation are retained in
[live-pilot-plan.md](../product/category-discovery/live-pilot-plan.md).

> Historical receipt: the app-specific approval/human-intervention conclusion below
> is superseded by the 2026-10-29 correction at the end. Counts remain historical.

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


## Existing deployment reconciliation — 2026-10-28

Buyer explicitly requested continuing until human intervention is necessary.
Read-only investigation followed the documented deployed PriceRecon route.
Direct SSH via configured `docker-app-vm` (192.168.10.251:22) timed out; no
authentication/config changes or host scan followed. Existing `proxmox` alias
worked; VM101 status running and QEMU guest-agent ping succeeded. Guest-agent
Python performed bounded Docker metadata/file-name inspection, not app startup.

Observed deployment: `/srv/docker-state/stacks/pricerecon` exists; running
`pricerecon` container has EBAY_APP_ID=true and EBAY_CERT_ID=true. Only booleans
were returned; values were never printed, exported, copied, used in an API call,
or stored in this repository. Mount destinations include `/app/pricerecon.db`
and `/app/config.yml`; neither production DB nor config contents were read.
The separate postgres container's eBay fields are absent, as expected.

Targeted approval/entitlement/contract/review filename inspection in the known
stack returned only unrelated AliExpress and browser-contract source/test files,
not an eBay provider approval or transient-use record. The repository's named
source-access records document successful old probes but explicitly leave the
app/use/retention issue unresolved. This bounded inventory does not claim the
approval is absent from the owner's email or eBay account.

**Human intervention now needed:** locate the existing application's eBay
production/Browse approval or account record and the applicable use agreement
covering this private transient comparison. No new app or duplicate account is
requested. A non-secret approval/use document or an already accessible signed-in
account view can resolve this; a fresh buyer authorization cannot create provider
approval. Credentials already have a deployment route, so do not ask the buyer
to paste them. Once actual evidence is available, review its app/use/retention
scope, inject existing credentials through a private route and run the already
approved envelope. If the existing application lacks the required provider
approval, that provider/account step belongs to the owner; no outreach/account
changes were made or implied here. All live request counters remain zero and
the shared grant remains unconsumed.


## Superseding primary-evidence correction — 2026-10-29

The earlier request to locate an app-specific approval/account/email record was
overbroad for standard search and single getItem. The exact eBay staff replies and
API licence now support a concrete external evidence review, as documented in the
[current plan](../product/category-discovery/live-pilot-plan.md#corrected-endpointuse-interpretation--2026-10-29)
and [manifest contract](../product/category-discovery/live-pilot-runner.md).
No additional buyer/provider approval ceremony is required for those endpoints.
This does not grant restricted getItems/watchCount access, history or aggregates.

Child changed only local source/tests/docs. Public documentation reads are separate
from the pilot budget; no token/search/detail calls, credentials, production reads
or modifications, accounts/outreach, fallback, push or PR occurred in this child.
The parent retains the actual app fingerprint/session review and live execution.
