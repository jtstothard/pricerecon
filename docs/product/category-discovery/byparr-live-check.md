# Existing Byparr service: bounded live check

Date: 2026-10-27. Operator: jtstothard / Codex. User authority: “I think we already use byparr on our proxmox server. I approve you running this now.” This authorises the bounded existing-service test discussed in the thread, superseding the earlier exclusion of solver execution for this test. It does not require or imply installation, replacement, scheduler execution or account access.

## Confirmed deployment

Proxmox `proxmox1`, VM **101 / docker-app-vm**, is running PriceRecon and Byparr. Direct SSH to the VM timed out once; its Proxmox guest agent provided the container inventory and executed the bounded probes. No VM, network, container or application configuration was changed.

Byparr container identity:

- Name: `byparr`.
- Image reference: `ghcr.io/thephaseless/byparr@sha256:874f719518f617d03a60e03411fc5d090647e1a877041e81f8dc965927c7deb6`.
- Local image ID: `sha256:c6dc8e0e49d7d2668aee1879dedade605d50afe322164ee70f1e22f3d6b3695f`.
- Network: `media_back`; port published at `192.168.10.251:8191`.

PriceRecon's deployed environment sets `PRICERECON_FLARESOLVERR_URL=http://byparr:8191/v1`. Its mounted configuration separately contains `http://localhost:8191/v1`; do not confuse that file value or the worktree's localhost setting with the endpoint used in this probe. The probe explicitly used the deployed environment endpoint through the existing client; it does not prove every connector resolves configuration identically.

Deployed and worktree `pricerecon/connectors/flaresolverr.py` SHA-256 both equal `606f35549d32cc6999e3fe7837d778784dceef8928e7384b5d9eed000b2b1aa9`. The test invoked that deployed `FlareSolverrClient.request_html`, without calling application monitoring, scheduler, database writes or notifications.

## Receipts

| Probe | Result | What it establishes |
| --- | --- | --- |
| Local worktree endpoint `http://localhost:8191/` | URL connection error | No local service verified. This does not describe the VM's Byparr service. |
| From deployed PriceRecon, GET Byparr `/openapi.json` | HTTP 200; paths `/health`, `/v1`, `/load`; request fields `cmd`, `url`, `maxTimeout`, `blockMedia`, `returnOnlyCookies` | Existing service reachable and exposes expected minimal request shape. API metadata version `0.1.0` is not accepted as the Byparr release version. No `/health` call made, because upstream health logic can fetch an external page. |
| Existing client → Byparr → `https://example.com` | Returned 1,989 HTML characters; expected `Example Domain` marker present; maxTimeout 20,000 ms, client timeout 30 s | Real client-to-service-to-page retrieval works for the control. No evidence that a challenge was encountered or solved. |
| Existing client → Byparr → `https://www.aliexpress.com/robots.txt` | Started **10:04:17.056778 UTC**, elapsed **2.82 s**; returned 3,051 HTML characters; maxTimeout 25,000 ms, client timeout 35 s | The previously unreadable robots document is technically accessible through this existing route. Generic rules restrict `/search/*` and other paths; rules for GPTBot and several named crawlers disallow all paths. User-agent-specific rules are not conflated with a blanket ban on every browser. No watch search or offer was acquired. |

Checks completed by **10:05:08 UTC**. Control and schema individual start/end timestamps were not recorded. Tool-call history in this conversation is the execution record; no raw merchant content, cookies, headers, secrets or page archives were saved in the repository.

The current client returns only rendered HTML. It does not expose the final merchant URL, merchant status, challenge outcome or selected variant, and therefore cannot establish those receipt fields from success alone. No network-interception claim is made.

## Browser and session implications

The VM also has a running `cloakbrowser` container; its readiness and session behaviour were not tested. The deployed PriceRecon config declares a named Camofox backend for Facebook only, with explicit `user_id` and `session_key` option keys, and no global browser default. Its private option values were not printed or used. This does not establish three fully configured watch browser routes.

The running Byparr request schema has no named-session field or session-management paths. No persistent connector-session support was demonstrated. Continue with the agreed **Camofox, Playwright and CloakBrowser** choices and **separate connector/merchant sessions** as design requirements; Byparr's one-shot retrieval is not evidence these requirements are met.

## Consequence

**No Byparr replacement or install is needed to test the existing adapter: it already works against the deployed Byparr endpoint.** This supersedes speculation that a provider switch must happen before testing.

The source ticket remains open. Solver connectivity and basic HTML compatibility are now demonstrated; watch discovery, merchant identity, selected configuration, UK destination, price/stock/cost fields, access/retention terms and repeated monitoring are not qualified. The next source test must choose a permitted discovery/detail route, preserve final URL/status evidence and satisfy any required agent identification. A solver result does not establish Web Bot Auth or change source access conditions. No repeat sweep of the 12 previously blocked hosts was attempted.
