# CloakBrowser content and Camofox session fixes: deployment receipt

Applied 2026-10-27 following the user's instruction: “Agree, fix both cloakbrowser and camofox to be working too.” This specifically authorises the browser/client correction beyond the original planning-only map. Source qualification and the rest of product implementation remain separate.

## Changes

- Retained the existing CloakBrowser wrapper source in [services/cloakbrowser](../../../services/cloakbrowser/README.md), rather than create a second service. The deployed wrapper now returns bounded HTML, truncation state, final URL and main-document status. Query strings/credentials are removed from the returned final URL. It explicitly reports no passive network interception.
- PriceRecon rejects title-only responses as `empty_result`, treats blocked main-document statuses as `blocked`, bounds returned content and preserves status/final-URL/truncation metadata.
- Anonymous Camofox contexts now use a connector/backend/origin-derived `userId`. An unscoped direct caller gets a private random scope. Connector construction passes its own connector identity into the adapter. Different merchants using Shopify therefore do not share the anonymous context by default.
- Camofox no longer performs Reddit-specific repeated snapshot polling on unrelated hosts. Explicitly configured account-profile IDs and tab groups are unchanged; operators remain responsible for dedicating those assigned profiles to the intended connector/merchant. No existing account state was migrated, inspected or reset.

The Camofox server itself already isolates contexts correctly by `userId`; the fault was PriceRecon's shared anonymous default. No Camofox server update/restart or new login was necessary.

## Deterministic verification

Before correction, the new tests failed on the actual symptoms: missing wrapper HTML, title-only adapter success, and identical anonymous Camofox IDs. After correction:

- **69 focused Python tests passed** across adapter, registry, connector migration, Reddit/profile bridge and new readiness regression tests.
- **2 Node wrapper tests passed**, including usable HTML/final URL/status and explicit large-page truncation.
- **54 focused tests passed against an isolated deployment-specific package**, which retained production's existing concurrency guards.
- Mypy passed for both changed Python source modules. New test lint and `git diff --check` passed. The touched existing modules retain **20 pre-existing Ruff findings**, verified against their HEAD versions with no new diagnostic code/message pairs; these were not suppressed or removed.

The fresh local test environment initially resolved selectolax 1.0.2, whose removed legacy parser prevents this repository's tests from collecting. Local verification used compatible selectolax 0.4.13. Project dependency declarations and production dependency versions were not changed. The staged images were thin layers over the exact existing images, with no dependency/browser downloads.

## Preserve deployed source differences

Production's external-browser module contains concurrency controls absent from this worktree's HEAD. They were preserved by applying the small correction onto the deployed source, not replacing it with the worktree file. The deployment-specific tests exercised that merged candidate. Host source hashes were checked immediately before replacement, as were the old container image IDs; cutover included an automatic rollback path if image recreation failed.

Updated existing source files on Proxmox VM 101:

| Path | Deployed SHA-256 |
| --- | --- |
| `/srv/docker-state/stacks/cloakbrowser/server.mjs` | `8ea6ab18085d5dc5af425672bd436a7221bb31b14fd6e918eefc26a98a6aa0d9` |
| `/srv/docker-state/stacks/pricerecon/src/pricerecon/connectors/base.py` | `275c3d6f9aacc724b79494af10945e8170136de32ee3c3ca05f99216a27630c8` |
| `/srv/docker-state/stacks/pricerecon/src/pricerecon/connectors/external_browser.py` | `9929b3aa0e06ffccf1ef805427d3a28ccd451fa74218d8b0d5e1d32bbe7076fc` |

| Existing service | Previous image ID | Applied image ID |
| --- | --- | --- |
| `cloakbrowser` | `sha256:181ff445710747ebd136e9c189d8e047bbfe6bc3a3f41c62e32be22dfad0151e` | `sha256:9962badf9a04500590d1c02a191e98749e275a5f492e9d5f0ce601f1e667930d` |
| `pricerecon` | `sha256:61b37601b1ff922b42b8a25e0754f4896cc119592ee0a39cef9c2594a29101d0` | `sha256:4c0be3053937ac1cec0acb5dfd7032b869f5e009b509aef77d641dab453d3655` |

Only these two services were recreated with `compose up --no-deps --no-build --pull never`. Their existing Compose files, environment, account configuration, volumes, database and scheduler settings were not changed. Normal PriceRecon startup resumed its existing scheduler; no manual monitoring run or notification test was triggered. Prior image IDs remain available for rollback. Rollback would restore both service image aliases and the three source preimages before recreating the services; no rollback was required.

The initial staging build used raw image IDs in `FROM`, which Docker interpreted as registry references and rejected. No running service changed. Corrected staging used the existing local image tags after verifying their IDs; both builds then succeeded. No registry authentication or dependency update was attempted.

## Live verification

Staged checks first proved the changes before cutover. CloakBrowser returned 1,989 HTML characters and HTTP 200 at 10:22:49 UTC. An initial Camofox check expected the heading `Example Domain`, but its network route returned different legitimate example-domain text; the diagnostic expectation failed. Rather than depend on that third-party response, subsequent Camofox content/isolation tests used the owned PriceRecon page.

At **10:24:59.630–10:25:00.667 UTC**, a separate Camofox isolation probe created only new test users, used synthetic cookie/local-storage markers, and showed:

- Different `userId` values did not share either marker.
- A different tab group under the same `userId` retained both markers, confirming tab groups are not context boundaries.
- Both test sessions were closed successfully.

This probe used the service's existing API key **inside its own container** for its protected evaluation/cleanup endpoints. The key was not printed, copied to this checkout, exported to another service or used for account access. No new authentication flow was introduced.

After cutover, the existing deployed PriceRecon connector configuration interface and adapter produced:

| UTC | Backend | Result |
| --- | --- | --- |
| **10:27:03.065609** | CloakBrowser through `http://gluetun:9378` | `degradation=none`, expected control marker, **1,989 HTML characters**, main status **200**, final URL `https://example.com/`, interception explicitly false. |
| **10:27:03.761234** | Camofox through `http://<private-host>:9377` | `degradation=none`, expected owned PriceRecon-page marker, **4,725 snapshot characters**, connector-scoped anonymous identity. No HTML, status or final-URL metadata is claimed for this snapshot-only route. |

CloakBrowser health reported `activeSessions=0` after its post-deployment probe. All other Camofox test-only contexts were then closed by their exact generated IDs; Camofox health reported `ok=true`, browser connected and `activeSessions=0`. The temporary staged wrapper container was removed. No existing account session was selected or deleted.

## Acceptance limits

Both browser paths now supply their documented content type through the deployed PriceRecon adapter, and anonymous connector/merchant session assignment is corrected. This is **browser integration acceptance**, not qualification of AliExpress, Militado, another merchant, a selected watch configuration, UK costs or recurring price history. Camofox snapshots are not HTML or passive network captures. CloakBrowser's normal endpoint remains fresh-context-per-call, not a persistent profile service. No global browser default or new connector route was switched on.

The broader source ticket remains open. Working browser infrastructure does not by itself satisfy source access requirements such as Web Bot Auth or historical-content retention rights. No commits, pushes or PRs were created.
