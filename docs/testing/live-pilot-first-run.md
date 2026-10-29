# First bounded live pilot — 2026-10-29

Source: integration f61fa3c49229e3629f1b6b7eef80be8adca5ad2d, independently
reviewed with zero Standards/Spec blockers and49tests. Endpoint-specific staff
guidance and licence review corrected the overbroad app-approval gate. Existing
deployed app credentials were passed from VM101 through the existing encrypted
Proxmox guest-agent/SSH route into the local runner environment in memory only.
No credential values were printed, put in argv, copied to files or committed.

Actual preflight: credentials present, no gates, ready_for_exclusion_check,
zero requests at preflight. Actual worker consumed the shared one-off grant and
served the existing read-only comparison/product application on loopback8878.
Source/use review and macOS exclusion checks necessarily passed before acquisition.

## Observed result

Two search pages returned five retained leads each. Both outcomes were partial,
next-page present/not followed. Aggregate reported discovered totals exceeded the
five inspected page results; no completeness/market-best claim follows.
All ten candidate identities remained unresolved; all delivered totals remained
unknown; no selected binding was supported. Zero detail inspections were reported.
One Addiesdive lead title mentioned the model reference, but none of the ten
included the entire query as contiguous text; no Casio title contained the exact
requested suffix. These counts are source-sufficiency diagnostics, not identity
confirmation. No prices/titles/itemIDs/seller data/raw responses are retained here.

A source implementation weakness was observed: detail selection requires the
entire search phrase as a substring. This is stricter than reference-led candidate
selection and skipped a potentially useful detail check. The pilot did not qualify
an obtainable UK offer, prove coupon success, produce history or calibrate savings.

## Stop, receipt limitation and cleanup

Parent sent SIGINT to the exact owned worker after bounded review; did not restart
or retry. The supervisor returned state=failed, duration72.159seconds, log_bytes0,
cleanup=true. Final worker counters were absent from its sanitized output, so this
receipt does NOT claim a fully reconciled provider request count. Two successful
search outcomes are observed; additional/auth counters need a graceful-stop repair
for a complete terminal receipt. This is a pilot instrumentation defect, not a
claim of denied provider access. Actual parent result retained in
[execution JSON](artifacts/live-pilot-runner/parent-execution.json).

Parent separately verified the marked run directory absent and loopback UI stopped.
Grant remains consumed and must not be deleted/reset. No live grant remains for
another run. Production state and buyer synthetic fixture8895 were unchanged.
No real notifications, purchases, account changes, provider contacts, deployments
or paid services occurred. Fix selector and operator-stop receipt offline; do not
rerun live under the consumed grant. Live usefulness remains partial/unproven.
