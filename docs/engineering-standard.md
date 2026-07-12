# PriceRecon engineering standard

This document is the repo-native standard for how PriceRecon work should be built, validated, and shipped.

It is intentionally PriceRecon-specific:

- the product is a market recon system, not a generic web app
- the hardest failure modes are source drift, brittle parsing, and false confidence in connector output
- the important proof is not just that code compiles, but that it behaves against deterministic fixtures and, when possible, live sources

## Principles

### 1. Explicit validation boundaries

Validate everything at the edge of the system:

- parse raw source data into typed models as early as possible
- isolate failures to the smallest unit that can fail
- keep bad listings, bad responses, and bad sources from silently contaminating downstream state

If a boundary is uncertain, make it explicit in code and tests.

### 2. Zero unchecked escape hatches

Do not introduce new unchecked shortcuts to get work passing:

- no `Any` where a concrete type is available
- no `type: ignore` unless the reason is documented and local
- no blind casts around connector payloads or normalized listings

If an escape hatch is unavoidable, it should be temporary, narrow, and justified in the change itself.

### 3. Deterministic plus live proof

PriceRecon changes should be backed by both:

- deterministic tests for repeatable behavior
- live proof when the change touches real-source behavior, browser automation, or connector assumptions

Do not treat one as a substitute for the other when the change crosses a source boundary.

### 4. Shrinking baseline

The first successful snapshot is a baseline, not a feature.

- establish the baseline cleanly
- only emit diff events after the baseline exists
- prefer incremental, bounded changes to broad rewrites

When something regresses, reduce the baseline impact before expanding scope.

### 5. No untestable feature work

If a change cannot be tested, it is not ready.

Every feature or connector change should have a clear verification path:

- unit or integration tests for the deterministic path
- fixture coverage for parsing and diff behavior
- live confirmation when the feature depends on a real source, session, or browser

## Canonical quality entrypoints

Run quality checks from the repo root with the repo's own tools:

- `python -m pytest`
- `python -m ruff check .`
- `python -m mypy src/pricerecon`

Use the narrowest command that proves the change, then widen only if needed. For connector work, prefer the relevant test module plus any affected source-level checks.

## What good PriceRecon work looks like

- connector changes validate input shape and failure modes
- diff-engine changes preserve the baseline-first contract
- tests cover both success and failure paths
- docs explain how the change is verified, not just what it does
- reviewable work stays small enough that proof is easy to inspect

## Where this standard shows up in the repo

- `CONTRIBUTING.md` — contributor expectations and PR checklist
- `README.md` — entry-point summary and documentation map
- `docs/connector-development.md` — connector-specific implementation guidance
