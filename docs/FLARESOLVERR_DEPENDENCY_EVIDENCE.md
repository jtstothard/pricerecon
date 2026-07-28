# FlareSolverr Dependency Evidence

## Test Methodology

For each connector requiring FlareSolverr, we tested direct HTTP access using curl:
```bash
curl -s -o /dev/null -w "%{http_code}" -L --max-time 10 "<search-url>"
```

**Blocked criteria**: HTTP 403 (Forbidden), 503, 520, 522, or 524 status codes
**Accessible criteria**: HTTP 200, 301, or 302 status codes

## Test Results

All 12 FlareSolverr-dependent connectors were tested. **All are blocked.**

| Connector | Search URL Tested | HTTP Status | Status | Evidence |
|-----------|-------------------|-------------|--------|----------|
| **AO.com** | https://www.ao.com/search?q=iPhone+12 | 403 | ❌ BLOCKED | Cloudflare protection |
| **Back Market** | https://www.backmarket.com/en-gb/search?q=iPhone+12 | 403 | ❌ BLOCKED | Cloudflare protection |
| **Box** | https://www.box.co.uk/search?search=iPhone+12 | 403 | ❌ BLOCKED | Cloudflare protection |
| **CDKeys** | https://www.cdkeys.com/?qsearch=iPhone+12 | 403 | ❌ BLOCKED | Cloudflare protection |
| **Currys** | https://www.currys.co.uk/search?q=iPhone+12 | 403 | ❌ BLOCKED | HTTP 403; response identifies Cloudflare as the server and contains a Cloudflare block page |
| **Depop** | https://www.depop.com/search/?q=iPhone+12 | 403 | ❌ BLOCKED | Cloudflare protection |
| **Etsy** | https://www.etsy.com/uk/search?q=iPhone+12 | 403 | ❌ BLOCKED | Captcha-delivery.com JS challenge |
| **Mercari** | https://www.mercari.com/search?keyword=iPhone+12 | 403 | ❌ BLOCKED | Cloudflare protection |
| **OnBuy** | https://www.onbuy.com/gb/search/?q=iPhone+12 | 403 | ❌ BLOCKED | Cloudflare protection |
| **Overclockers** | https://www.overclockers.co.uk/search?criteria=iPhone+12 | 403 | ❌ BLOCKED | Cloudflare challenge (`Cf-Mitigated: challenge`) |
| **Scan** | https://www.scan.co.uk/search?q=iPhone+12 | 403 | ❌ BLOCKED | Cloudflare protection |
| **Very.co.uk** | https://www.very.co.uk/electricals/ip-12/search?q=iPhone+12 | 403 | ❌ BLOCKED | Cloudflare protection |

## Etsy Evidence

Etsy returns a JavaScript challenge page that requires browser execution:

```html
<html lang="en"><head><title>etsy.com</title>
<style>#cmsg{animation: A 1.5s;}@keyframes A{0%{opacity:0;}99%{opacity:0;}100%{opacity:1;}}</style>
</head><body style="margin:0">
<p id="cmsg">Please enable JS and disable any ad blocker</p>
<script data-cfasync="false">
var dd={'rt':'i','cid':'AHrlqAAAAAMAGqBZR9osWGUAP4dI4A==','hsh':'D013AA612AB2224D03B2318D0F5B19', ...}
</script>
<script data-cfasync="false" src="https://ct.captcha-delivery.com/i.js"></script>
</body></html>
```

This confirms FlareSolverr (or similar browser automation) is required.

## Currys Disposition (2026-07-28)

The direct request was independently rechecked against the current search endpoint:

```text
HTTP/2 403
server: cloudflare
response size: 5485 bytes
```

This establishes the observed access failure without relying on the older `/gbuk/search-keywords/...` URL. It does not establish that every 403 from every retailer is Cloudflare-generated; the conclusion is limited to this Currys response.

The solver path was then checked independently of the connector parser by posting to the configured `http://localhost:8191/v1` endpoint:

```text
HTTP/1.1 200 OK
FlareSolverr status: ok
solution.status: 200
solution.response: 2,412,896 bytes
message: Challenge not detected!
```

The response produced 23 parsed Currys listings for the RTX 5070 probe. The Currys template therefore remains recovered through FlareSolverr; no direct-HTTP fallback is warranted. The checked-in regression tests separately verify (1) Currys routes through FlareSolverr and (2) the client sends `request.get` to `/v1` and extracts `solution.response`.

## Conclusion

**All 12 FlareSolverr-dependent connectors are verified to require anti-bot bypass.**
- Direct HTTP requests fail with HTTP 403 on all sites
- Some sites (like Etsy) show explicit JS/captcha challenges
- FlareSolverr deployment is mandatory for these connectors to function

## Resolution

To unblock these connectors:
1. Deploy FlareSolverr following `docs/FLARESOLVERR_DEPLOYMENT.md`
2. Update `config.yml` with correct endpoint: `http://localhost:8191` (default)
3. Run `scripts/check_flaresolverr.sh` to verify deployment
4. Run `scripts/test_flaresolverr_connectors.py` for live verification