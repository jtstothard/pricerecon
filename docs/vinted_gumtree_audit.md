"""Documentation: Vinted and Gumtree Connector Integration Audit

This document records the reconciliation outcome for task t_78df61d0.

## Audit Findings (2026-07-14)

The completed task t_bfc7c7ed claimed Vinted and Gumtree connectors were
integrated, but the actual repo state showed:

1. Connector implementations existed as untracked files:
   - src/pricerecon/connectors/vinted.py (untracked)
   - src/pricerecon/connectors/gumtree.py (untracked)

2. pyproject.toml had entry points registered but was uncommitted

3. __init__.py fallback list included 'vinted' and 'gumtree' (uncommitted)

4. Test files existed in repo root (non-standard location):
   - test_vinted_gumtree.py (untracked)
   - verify_vinted_gumtree.py (untracked)
   - seed_vinted_gumtree.py (untracked)

5. Live verification returned 0 listings, indicating HTML selectors need
   refinement for actual website DOM structures.

## Resolution

### INTEGRATED (KEEP)

The following artifacts are production-ready and have been integrated:

1. **Connector implementations**
   - src/pricerecon/connectors/vinted.py
   - src/pricerecon/connectors/gumtree.py
   - Both use browser-assisted HTML parsing via BrowserClient
   - Source role: MARKETPLACE
   - Proper deduplication and condition parsing

2. **Entry points registration**
   - pyproject.toml lines 98-99:
     - vinted = "pricerecon.connectors.vinted:VintedConnector"
     - gumtree = "pricerecon.connectors.gumtree:GumtreeConnector"

3. **Fallback registration**
   - src/pricerecon/connectors/__init__.py lines 55-56 added to fallback list

4. **Unit tests**
   - tests/test_vinted.py (6 tests, pytest-structured)
   - tests/test_gumtree.py (6 tests, pytest-structured)
   - All 12 tests pass deterministically with mock HTML

### DISCARDED (REMOVE)

The following artifacts were not production-ready and have been removed:

1. **Root-level test scripts** (non-standard, inconsistent with project structure)
   - test_vinted_gumtree.py (removed)
   - verify_vinted_gumtree.py (removed)
   - seed_vinted_gumtree.py (removed)

### DEFERRED (FUTURE WORK)

1. **Live verification**: HTML selectors need refinement for actual Vinted and
   Gumtree DOM structures. Current selectors are generic and return 0 listings.

## Verification

- Connector registration: PASS (both discoverable via entry points)
- Unit tests: PASS (12/12 tests with mock HTML)
- Integration: PASS (proper file placement and imports)
- Live verification: DEFERRED (requires DOM analysis, 0 listings currently)

## Related Tasks

- Parent: t_bfc7c7ed (Implement missing Vinted + Gumtree connectors)
- This task: t_78df61d0 (Reconcile Vinted/Gumtree board claim with real repo state)

## Files Changed

- src/pricerecon/connectors/vinted.py (added)
- src/pricerecon/connectors/gumtree.py (added)
- tests/test_vinted.py (added)
- tests/test_gumtree.py (added)
- pyproject.toml (entry points added)
- src/pricerecon/connectors/__init__.py (fallback list updated)