# Reddit acquisition lane benchmark

`scripts/reddit_lane_benchmark.py` compares bounded, read-only Reddit acquisition lanes without changing PriceRecon configuration or writing watches/database state.

## Fixed workload

- Subreddit: `hardwareswapuk`
- Comparison query: `RTX`
- Limit: `25`
- Execution: one sequential attempt per lane: RSS → official OAuth (unavailable) → rAPI browser-session → Camofox snapshot → optional CloakBrowser
- Safe result fields: Reddit `id`, `title`, `permalink`, `created_utc`; plus latency, count, relevance, status, and failure taxonomy.

## Build/load rAPI

rAPI is an incomplete browser-side TypeScript/IIFE library. Build it outside this repository, then pass the generated bundle:

```bash
git clone --depth 1 https://github.com/Littux-Dustux/rAPI.git /tmp/rapi-src
cd /tmp/rapi-src
npm install --ignore-scripts
npm install --no-save typescript
npm run build
cd /home/hermes/pricerecon
python3 scripts/reddit_lane_benchmark.py --query RTX --limit 25 \
  --rapi-bundle /tmp/rapi-src/dist/main.global.js > /tmp/reddit-lanes.json
```

The rAPI lane evaluates one GET-only listing expression in a temporary authenticated Camofox tab. The adapter exposes no click, type, press, cookie, or session-management operation and closes the temporary tab in all cases. The benchmark projects the page result to safe fields before printing it.

## Lane semantics

- **RSS** uses the existing `TemplateConnector` RSS implementation and Reddit normalizer/filter.
- **official OAuth** is explicitly labeled unavailable. No official Reddit API credentials are installed or tested; this is not the rAPI lane.
- **rAPI browser-session** loads the built rAPI IIFE into the authenticated Reddit Camofox page and calls its listing reader. It requires both the bundle and the configured Camofox endpoint/profile.
- **Camofox snapshot** uses the existing authenticated-profile snapshot parser. It is distinct from rAPI and reports snapshot-parser results only.
- **CloakBrowser** remains an optional named external-browser lane and is not substituted for Camofox.

`ok` means listings were returned; `healthy_empty` means the lane completed with zero matches; `unavailable` means a prerequisite was absent and the lane was not tested. CAPTCHA, OTP, login, blocked, or expired-profile responses remain failures and are not bypassed.

## Safety / interpretation

The JSON never prints user IDs, session keys, cookies, authorization headers, credential values, or endpoint query strings. This is a bounded acquisition benchmark, not a throughput test. Compare lanes using the same query/limit and timestamp; an unconfigured or unavailable lane is not a failed live test.
