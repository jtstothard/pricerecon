# eBay OAuth diagnostic correction

Applied 2026-10-27 under the user's explicit approval to fix the eBay helper. The browser/source qualification effort remains separate.

## Correction

The helper constructed a credential-pair cache key and copied it into an unbounded diagnostic registry and INFO logs, including the concurrent-waiter path. It could also expose provider response bodies, transport exception text or invalid persisted-token validation input.

The fix removes the unused tracking registry/function and all tracking calls, replaces the wait message with a generic event, and sanitizes auth errors to status/type information. Stored-token/config parse warnings no longer stringify invalid input. The normal coordinator still deduplicates token fetches; token storage and cached-token use are unchanged. HTTP/transport/schema failure handling keeps its intended bounded retry behaviour; unexpected exception categories are not broadly swallowed. No credentials were replaced or rotated.

Source: [eBay connector](../../../src/pricerecon/connectors/ebay.py). Regression coverage: [secret-safe OAuth tests](../../../tests/test_ebay_secret_logging.py).

## Verification

New tests first failed against synthetic credentials on the actual success/waiter and error paths. After the fix, **24 focused tests passed**, including new secret-safe diagnostics, existing OAuth/token storage, concurrent startup deduplication and browser-connector compatibility coverage. A test-only fixture isolates the coordinator's event-loop state; production lock/retry logic was not replaced to make tests pass.

Mypy passed for the changed module. New-test lint and diff whitespace checks passed. Existing module Ruff findings decreased from 26 to 25 with no new diagnostic code/message pairs; no suppressions were added.

A staged runtime check used the actual candidate module with networking disabled and synthetic HTTP responses. Three concurrent callers caused one fetch; success/waiter logs and provider-error text contained no synthetic auth material. The removed registry was absent. The same deployed-module check passed after cutover. **No new real eBay API request** was needed for these checks and no production token store was touched by them.

## Deployment

Only PriceRecon was recreated; the previously fixed browser services and their configuration remained intact. Source was checked against its expected preimage before atomic replacement. The candidate image was a thin source-only layer over the existing image, with no dependency update. Cutover had a guarded source/image rollback path, which was not needed.

- Host source: `/srv/docker-state/stacks/pricerecon/src/pricerecon/connectors/ebay.py`.
- Previous source SHA-256: `c4362e47ac1e4594a27031b7f27458b1bab501b8c49e07a313bda066698df0b1`.
- Applied/deployed source SHA-256: `e5fa4b073d7f0daf17fe05282843a1b0505633b64e594cd7db549991c72f147c`.
- Previous image: `sha256:4c0be3053937ac1cec0acb5dfd7032b869f5e009b509aef77d641dab453d3655`.
- Applied image: `sha256:90c84edd8d69d2bcacf6b433601a0de230d457622503f520c447f8b15f6f745d`.

Existing Compose/environment/database/scheduler settings were not changed. Normal startup resumed the existing scheduler; no manual watch/notification run was triggered. Temporary image-build files were removed; the prior image remains available for rollback. No commit, push or PR was created.

This prevents the identified future diagnostic emissions. Historical production logs were not inspected, erased or certified free of credentials; the source finding alone does not prove what those logs retained. No credential rotation or log-retention change was performed.
