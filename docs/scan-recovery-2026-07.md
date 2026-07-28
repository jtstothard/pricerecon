# Scan connector recovery — live verification

- **Issue:** [#60](https://github.com/jtstothard/pricerecon/issues/60)
- **Verified:** 2026-07-28 (UTC)
- **Query:** `RTX 5070`
- **Route:** configured FlareSolverr endpoint `http://localhost:8191/v1` via `ScanConnector` / `TemplateConnector`

## Evidence

The direct baseline probe returned HTTP 200 and matched 26 configured `li.product` cards. A real connector search through the configured FlareSolverr route returned 26 parsed listings. The first three were:

1. ASUS PRIME NVIDIA GeForce RTX 5070 OC 12GB GDDR7 — £679
2. ZOTAC NVIDIA GeForce RTX 5070 AMP White 12GB GDDR7 — £599
3. PNY NVIDIA GeForce RTX 5070 TI OC 16GB GDDR7 — £864

Each result had a product URL under `https://www.scan.co.uk/products/`.

Reproduction:

```bash
python3 - <<'PY'
import asyncio
from pricerecon.connectors.scan import ScanConnector

async def main():
    connector = ScanConnector(flaresolverr_url="http://localhost:8191/v1")
    try:
        listings = await connector.search("RTX 5070")
        print(len(listings))
        for listing in listings[:3]:
            print(listing.title_raw, listing.price, listing.url)
    finally:
        await connector.cleanup()

asyncio.run(main())
PY
```

## Configuration conclusion

`src/pricerecon/connectors/templates/scan.yml` does not contain `disabled: true`; no enablement change was needed. The existing selectors parse the live response successfully. The recovery blocker was verification/tooling: `scripts/check_flaresolverr.sh` previously used GET against the FlareSolverr endpoint, which correctly returned HTTP 405 even when the service was healthy. The check now uses the documented POST JSON API.

No production configuration or connector enablement was changed.
