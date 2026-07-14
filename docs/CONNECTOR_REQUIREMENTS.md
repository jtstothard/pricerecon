# Connector Requirements

This document shows which PriceRecon connectors require FlareSolverr (anti-bot bypass) and which work with direct HTTP requests.

## FlareSolverr-Required Connectors (12)

These sites block simple HTTP requests with anti-bot protection (Cloudflare, DDoS-GUARD, etc.). FlareSolverr is **required** for these to work.

| Connector | Site | Protection | Notes |
|-----------|------|------------|-------|
| AO.com | ao.com | High (Cloudflare) | Fully blocked on direct requests |
| Back Market | backmarket.com | High (Cloudflare) | Fully blocked on direct requests |
| Box | box.co.uk | High (Cloudflare) | Fully blocked on direct requests |
| CDKeys | cdkeys.com | High (Cloudflare) | Fully blocked on direct requests |
| Currys | currys.co.uk | High (Cloudflare) | Fully blocked on direct requests |
| Depop | depop.com | High (Cloudflare) | Fully blocked on direct requests |
| Etsy | etsy.com | High (Cloudflare) | Fully blocked on direct requests |
| Mercari UK | mercari.com | High (Cloudflare) | Fully blocked on direct requests |
| OnBuy | onbuy.com | High (Cloudflare) | Fully blocked on direct requests |
| Overclockers | overclockers.co.uk | High (Cloudflare) | Fully blocked on direct requests |
| Scan | scan.co.uk | High (Cloudflare) | Fully blocked on direct requests |
| Very.co.uk | very.co.uk | High (Cloudflare) | Fully blocked on direct requests |

**All verified via curl tests returning HTTP 403.**

## Direct-HTTP Connectors (6+)

These sites work with direct HTTP requests and do not require FlareSolverr.

| Connector | Site | Auth Required | Notes |
|-----------|------|---------------|-------|
| Amazon UK | amazon.co.uk | None | Direct HTTP works |
| AliExpress | aliexpress.com | API Key (optional) | Official API + fallback scraping |
| Argos | argos.co.uk | None | Direct HTTP works |
| CCL | cclonline.com | None | Direct HTTP works |
| CeX | cex.co.uk | None | Direct HTTP works |
| Ebuyer | ebuyer.com | None | Direct HTTP works |
| eBay | ebay.co.uk | API Key | Official API |
| Google Shopping | google.com | None | Browser-based (Playwright) |
| John Lewis | johnlewis.com | None | Direct HTTP works |
| Laptops Direct | laptopsdirect.co.uk | None | Direct HTTP works |
| Music Magpie | musicmagpie.co.uk | None | Direct HTTP works |
| Novatech | novatech.co.uk | None | Direct HTTP works |
| Reddit | reddit.com | None | RSS feed (no HTTP scraping) |
| HotUKDeals | hotukdeals.com | None | RSS feed (no HTTP scraping) |
| Shopify | *.myshopify.com | None | Generic Shopify scraping |
| Dell UK | dell.co.uk | None | Direct HTTP works |
| Aria | aria.co.uk | None | Direct HTTP works |
| EE Gaming | ee.co.uk | None | Retired (redirects) |

## Browser-Assisted Connectors (2)

These use Playwright for dynamic content, not FlareSolverr.

| Connector | Site | Notes |
|-----------|------|-------|
| Facebook Marketplace | facebook.com | Requires session cookies (FB_C_USER, FB_XS, etc.) |
| Vinted | vinted.co.uk | Browser-based scraping |
| Gumtree | gumtree.com | Browser-based scraping |

## Auth-Gated Connectors (1)

| Connector | Site | Auth | Notes |
|-----------|------|------|-------|
| Costco UK | costco.co.uk | Session cookie | Member-only pricing |

## Quick Reference

**Can I use this connector without FlareSolverr?**

- ✅ **Yes**: Amazon, Argos, CCL, CeX, Ebuyer, John Lewis, Laptops Direct, Music Magpie, Novatech, Shopify, Dell, Aria
- ❌ **No**: All sites in "FlareSolverr-Required" table above
- 🔐 **Maybe**: eBay (API key required), Facebook (cookies required), Costco (session cookie required), Google Shopping (Playwright required)

## Testing Without FlareSolverr

```bash
# Test if a site blocks simple requests
curl -I "https://www.backmarket.com/en-gb/search?q=test"

# HTTP 403 = blocked (needs FlareSolverr)
# HTTP 200/301/302 = works directly
```

## Deployment Impact

**Without FlareSolverr deployed:**
- 12 connectors will fail with `ConnectorDegradedError`
- 18+ connectors will work normally

**With FlareSolverr deployed:**
- All 30+ connectors can work (if auth requirements are met)

See [FLARESOLVERR_DEPLOYMENT.md](FLARESOLVERR_DEPLOYMENT.md) for setup instructions.