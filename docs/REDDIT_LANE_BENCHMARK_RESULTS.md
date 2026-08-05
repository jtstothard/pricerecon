# Reddit lane benchmark — live results (2026-08-05)

Workload: subreddit `hardwareswapuk`, limit 5, queries GPU / RTX / "graphics card" / absent term.
Lanes: RSS, official OAuth (not configured), rAPI browser-session, Camofox snapshot, CloakBrowser.

## Per-lane outcome

| Lane | GPU | RTX | graphics card | absent |
|---|---|---|---|---|
| RSS | ok (1) | rate_limited 429 | rate_limited 429 | healthy_empty |
| official OAuth | unavailable (not configured) | unavailable | unavailable | unavailable |
| rAPI browser-session | failed 500 | failed 500 | failed 500 | failed 500 |
| Camofox snapshot | ok (1) | healthy_empty | healthy_empty | healthy_empty |
| CloakBrowser | healthy_empty | healthy_empty | healthy_empty | healthy_empty |

## rAPI browser-session — FAILED (500) — root cause isolated
- `eval(<22KB rAPI IIFE bundle>)` succeeds: `typeof window.rAPI` => `"function"` (Camofox `/evaluate` returns 200).
- Simple arithmetic / async / for-await expressions up to 44KB all return 200. Size is not the limit.
- The failure is `window.rAPI.listing.feed("hardwareswapuk","new",{q:...})` → Camofox `/evaluate` returns HTTP 500 `{"error":"Internal server error"}`.
- Why: rAPI's `listingGenerator` builds the URL from `location.origin + "/r/<sub>.json"` (relative-origin fetch). A hand-written **absolute** `fetch("https://www.reddit.com/r/hardwareswapuk/new.json", ...)` returns 200 JSON in the same Camofox tab, while **relative** `fetch("/r/...json")` fails with `NetworkError`. Camofox's `/evaluate` sandbox does not proxy/patch rAPI's relative-origin fetch, so rAPI's internal network call errors server-side → 500.
- Verdict: rAPI is **infeasible through the Camofox `/evaluate` transport** as wired today. It is neither an rAPI logic bug nor a size limit — it is a transport/sandbox limitation on the library's relative fetch. Fixing it would require either a Camofox endpoint that permits arbitrary in-page network or rewriting rAPI's fetch to absolute URLs inside the adapter.

## CloakBrowser — healthy_empty on all queries — root cause isolated
- CloakBrowser `POST /api/browser/session` for the Reddit search URL returns `navigated:true` but:
  - `title = "Reddit - Prove your humanity"`
  - `html_len=0`, `snapshot_len=0`, `comments=0`.
- CloakBrowser is being served Reddit's **bot-detection / human-verification interstitial** ("Prove your humanity"). It is actively gated by Reddit, so zero posts are parsed. This is not a parser defect; the lane is blocked at the browser level.
- Verdict: CloakBrowser (as deployed in the media-automation stack) is **blocked by Reddit's bot gate** for reddit.com and cannot return listings. Repeated 429s from RSS corroborate aggressive Reddit anti-bot limiting on this exit/ASN.

## Camofox snapshot — working authenticated browser lane
- Returns correct results for a real match (GPU -> 1 post identical to RSS), and correct `healthy_empty` for genuine zero-match queries. Mirrors the reference RSS result on the positive case.
- Latency ~5-9 s vs RSS ~0.2-0.8 s. RSS is much faster when not rate-limited; Camofox is the reliable authenticated fallback when RSS is rate-limited/blocked.

## Recommendation
- Keep **Camofox snapshot** as the sole authenticated browser lane for Reddit (working, verified live).
- Treat **rAPI** as not integrable through the current Camofox `/evaluate` transport without a Camofox-side in-page-network change; do not spend more effort on it as wired.
- Treat **CloakBrowser** as blocked for reddit.com by Reddit's human-verification gate on this ASN; not a viable Reddit lane without a residential-IP / different exit or manual pass of the challenge.
