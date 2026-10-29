# Standard eBay endpoint evidence correction — 2026-10-29

Base: clean integration `4707d37`; `git merge integration/watch-category-discovery`
reported already up to date before editing. Work performed directly in the clean
integration checkout. No reset/clean, sibling edits, push or PR.

## Corrected result

The manifest now requires `endpoint_access` and `transient_use`, not fictional
app-specific approval. Endpoint evidence accepts only either exact eBay Developer
Support staff URL listed in the runner contract; transient-use evidence accepts
only the exact API licence URL. These URLs identify sources, not permissions
minted by the runner. Parent review still assesses source content and binds its
exact saved bytes, actual app fingerprint, purpose, current envelope and session
expiry. Existing missing/changed/oversized/path checks and no-force stay intact.
Historical parent approval/email/account blockers are explicitly superseded for
standard search and single getItem. Restricted getItems/watchCount, persistent
history, category aggregates and public commingling remain outside this pilot.

## Evidence handoff

External prepared directory: `/var/folders/kc/hjd9zkys3ts402ygmnrh89j40000gn/T/pricerecon-pilot-public-evidence-vl9p16_g`.
`review.template.json` includes exact hashes for attributed public-source extracts
and the current plan hash. App fingerprint and session values are deliberately
unfilled and will fail validation until the parent supplies actual values via the
existing authorized route. The files are extracts/summaries of successful web
reader output, not complete HTML or fictional test evidence. Parent may inspect
and use these bytes or replace them with its reviewed full captures and rehash.

Documentation accounting in this child: three successful public page opens
(two staff replies and API licence), two licence find operations; one separate
attempted direct public HTML GET returned 403, with no saved response body.
No provider offer acquisition, token/search/detail requests or pilot budget spent.
No credential values/presence discovery, production access/modification, account,
outreach, source fallback, live grant consumption or native activation by child.

## Verification

Read engineering standard, glossary and TDD skill. Existing review-manifest and
public CLI seams were used. Red: updated standard-endpoint manifest failed under
the old kind/issuer rules. Green: it passes with current rules. Negative tests
reject arbitrary/altered/lookalike URLs, generic Buy requirements, swapped source
kinds and historical app-approval assertions. App/envelope/expiry, changed/missing
documents, no-force, single grant, actual controlled UI/cleanup remain tested.
Restricted batch-item and watch-count requests are rejected before transport.

- 49 passed: `tests/test_live_pilot.py tests/test_pilot_activation.py
  tests/test_ebay_oauth.py tests/test_ebay_startup_burst.py
  tests/test_ebay_secret_logging.py` (11 existing warnings).
- Full-source mypy: success, 127 source files.
- Focused ruff check and `git diff --check`: passed.
- Python: existing `t3-7260bb2e/.venv/bin/python`, `PYTHONPATH=src`.

Controlled tests prove source behavior, not live provider/buyer acceptance.
Parent alone performs the authorized one-off run after merger using the existing
deployed credential route; no additional approval ceremony is required.
