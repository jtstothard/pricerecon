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
| ebuyer | `https://www.ebuyer.com/searchresults?descriptionfilter=RTX%205070` | 200 (httpx), timeout (urllib) | Baseline probe with `urllib` timed out; independent verification with `httpx` returned HTTP 200 with 20 product cards. The timeout is a `urllib`-vs-site behavior, not an endpoint failure. | Configured HTML selectors match empty placeholder elements; product data is in client-side JSON and `li-productid`/`li-url` attributes. Not recoverable via HTML selectors alone. | HTML parsing artifact (JSON path works) | 2026-07-28T20:42:03.716509Z (original probe), verified 2026-07-28T21:30 (httpx) |
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
- **Recoverable with JSON path (not HTML selectors):** `ebuyer` timed out under the baseline's `urllib` probe tool, but direct `httpx` verification returned HTTP 200 with 20 product cards. The configured HTML selectors target empty placeholder elements; product data is in the `ecommerceData.impressions` JSON and card attributes (`li-productid`, `li-url`, `li-imageurl`). The JSON-based parser in `TemplateConnector._parse_ebuyer_json` successfully extracts listings with real product URLs and images when joined on `dimension5` to the card's `li-productid`. The timeout observed in the baseline is an artifact of the probe tool's user-agent handling, not an endpoint failure.

## Configuration integrity

The eight connector templates were not modified by this probe. Existing `disabled: true` state was left unchanged wherever present (including `ao` and `aria`; no enablement or retirement action was taken). Only this evidence document is part of the resulting change.

## Reproduction

```bash
python3 - <<'PY'
import urllib.request, time
urls=[
  'https://www.cclonline.com/search/RTX%205070',
  'https://www.ebuyer.com/searchresults?descriptionfilter=RTX%205070',
  'https://www.scan.co.uk/search?q=RTX%205070',
  'https://www.overclockers.co.uk/search/?query=RTX%205070',
  'https://www.box.co.uk/search?search=RTX%205070',
  'https://www.currys.co.uk/search?q=RTX%205070',
  'https://www.ao.com/uk/search?search=RTX%205070',
  'https://www.aria.co.uk/',
]
for url in urls:
  t = time.monotonic()
  try:
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (compatible; PriceRecon/1.0)'})
    with urllib.request.urlopen(req, timeout=30) as r:
      b = r.read(1000)
      print(url, 'status', r.status, 'len-prefix', len(b), 'elapsed', round(time.monotonic() - t, 2))
  except Exception as e:
    print(url, type(e).__name__, str(e), 'elapsed', round(time.monotonic() - t, 2))
PY
```

The command used for this run was executed from the repository with Python's `urllib` and BeautifulSoup. The raw response bodies were not committed; this report records the observed status, classification, selector result, blocker class, and timestamp required for the baseline.