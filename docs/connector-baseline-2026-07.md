# Disabled connector baseline — live read-only probe

- **Issue:** [#57](https://github.com/jtstothard/pricerecon/issues/57)
- **Probe date:** 2026-07-28
- **Query:** `RTX 5070`
- **Method:** direct HTTPS request, `urllib`, 30-second timeout, Mozilla-compatible user agent, redirects followed; response body parsed with BeautifulSoup using the connector's configured card selector. No connector execution or configuration mutation was performed.
- **Important:** each timestamp below is the start time of that connector's probe. A timeout or HTTP error is recorded as observed; no successful classification is inferred from prior evidence.

## Results

| Connector | URL | HTTP status | Response classification | Selector parse result | Blocker class | Evidence timestamp (UTC) |
|---|---|---:|---|---|---|---|
| ccl | `https://www.cclonline.com/search/RTX%205070` | 403 | Cloudflare challenge/block page (`Just a moment...`) | No matches for `article, .product, .product-item, .search-result` | Cloudflare | 2026-07-28T20:42:03.589925Z |
| ebuyer | `https://www.ebuyer.com/searchresults?descriptionfilter=RTX%205070` | **probe failed** | Read timeout (`TimeoutError: The read operation timed out`); no response body | Not exercised against a response; 0 local matches | Probe failure / unavailable evidence | 2026-07-28T20:42:03.716509Z |
| scan | `https://www.scan.co.uk/search?q=RTX%205070` | 200 | HTML response, title `Search results for 'RTX 5070' \| SCAN UK`; not identified as a challenge page | **Matched 26** `li.product` cards | None observed in this direct probe | 2026-07-28T20:42:33.798173Z |
| overclockers | `https://www.overclockers.co.uk/search/?query=RTX%205070` | 403 | Cloudflare challenge/block page | No matches for `article, .product, .product-card, .search-result` | Cloudflare | 2026-07-28T20:42:34.023197Z |
| box | `https://www.box.co.uk/search?search=RTX%205070` | 404 | `404 Not Found` error page | No matches for `article, .product, .product-card, .search-result` | HTTP error / endpoint response | 2026-07-28T20:42:34.077324Z |
| currys | `https://www.currys.co.uk/search?q=RTX%205070` | 403 | HTTP 403 response; body did not expose configured product tiles | No matches for `.product-tile` | Cloudflare / access denied | 2026-07-28T20:42:35.468744Z |
| ao | `https://www.ao.com/uk/search?search=RTX%205070` | 403 | Cloudflare challenge/block page (`Just a moment...`) | No matches for `article, .product, .product-card, .search-result` | Cloudflare | 2026-07-28T20:42:35.572504Z |
| aria | `https://www.aria.co.uk/` | 200 | Business closure notice; title `Aria PC - Message to our customers` | No matches for `article, .product, .product-item, .search-result` | Business closed | 2026-07-28T20:42:35.620585Z |

## Interpretation

- **Directly usable evidence in this pass:** `scan` returned HTTP 200 and 26 configured card matches. This confirms the direct endpoint was reachable at probe time, but does not by itself prove every field selector parses or that the configured FlareSolverr lane succeeds.
- **Blocked:** `ccl`, `overclockers`, and `ao` returned Cloudflare challenge responses. `currys` returned HTTP 403 with no configured product-tile matches.
- **Endpoint/error:** `box` returned HTTP 404 and no configured card matches.
- **Closed:** `aria` returned its customer-closure page and no product cards.
- **Unknown:** `ebuyer` timed out before a response was received. This artifact deliberately does not reuse an earlier successful or failed classification.

## Configuration integrity

The eight connector templates were not modified by this probe. Existing `disabled: true` state was left unchanged wherever present (including `ao` and `aria`; no enablement or retirement action was taken). Only this evidence document is part of the resulting change.

## Reproduction

```bash
python3 - <<'PY'
# Direct read-only probe: query RTX 5070, follow redirects, 30s timeout,
# preserve status/body, then parse the configured card selector.
PY
```

The command used for this run was executed from the repository with Python's `urllib` and BeautifulSoup. The raw response bodies were not committed; this report records the observed status, classification, selector result, blocker class, and timestamp required for the baseline.
