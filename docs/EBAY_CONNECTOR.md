# eBay Connector for PriceRecon

## Overview

The eBay connector implements the eBay Browse API with OAuth token management for searching listings and retrieving normalized data.

## Features

- ✅ OAuth client credentials grant for application access tokens
- ✅ Token persistence in `connector_configs` database table
- ✅ Automatic token refresh on expiry (5-minute buffer)
- ✅ Keyword search with price and condition filters
- ✅ NormalizedListing schema compliance
- ✅ Condition mapping (new, refurbished, used variants)
- ✅ Seller info extraction
- ✅ Error handling for auth failures and rate limits

## Configuration

The connector requires eBay API credentials via environment variables:

```bash
export EBAY_APP_ID="your_ebay_app_id"
export EBAY_CERT_ID="your_ebay_cert_id"
```

### Getting eBay Credentials

1. Go to [eBay Developers](https://developer.ebay.com/)
2. Create an account or sign in
3. Navigate to "My Keys" under "My Account"
4. Create a new API key set or use existing one
5. Copy the **App ID (Client ID)** and **Cert ID (Client Secret)**
6. Set the environment variables above

## Usage

### Basic Search

```python
import asyncio
from pricerecon.connectors.ebay import eBayConnector

async def search_example():
    connector = eBayConnector(
        app_id="your_app_id",
        cert_id="your_cert_id",
        db_path="pricerecon.db"
    )

    await connector.initialize()

    try:
        # Search with keyword
        listings = await connector.search("RTX 3090")

        # Search with filters
        listings = await connector.search(
            "RTX 3090",
            filters={
                "price_max": 1000,
                "condition": "refurbished"
            }
        )

        for listing in listings:
            print(f"{listing.title_raw} - £{listing.price}")

    finally:
        await connector.cleanup()

asyncio.run(search_example())
```

### Available Filters

- `price_max`: Maximum price (e.g., `1000`)
- `condition`: One of `new`, `refurbished`, `used_like_new`, `used_good`, `used_fair`

### Condition Mapping

The connector maps eBay condition strings to normalized `Condition` enum:

| eBay Condition | Normalized |
|----------------|------------|
| New | `NEW` |
| New without tags | `NEW_OPEN_BOX` |
| Open box | `NEW_OPEN_BOX` |
| Certified refurbished | `REFURBISHED` |
| Like New | `USED_LIKE_NEW` |
| Very Good | `USED_GOOD` |
| Good | `USED_GOOD` |
| Acceptable | `USED_FAIR` |
| For parts or not working | `FOR_PARTS` |

## Database Schema

The connector stores OAuth tokens in the `connector_configs` table:

```sql
CREATE TABLE connector_configs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    connector_id TEXT NOT NULL UNIQUE,
    config_json TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

Token JSON structure:
```json
{
  "oauth_token": {
    "access_token": "...",
    "token_type": "Application Access Token",
    "expires_in": 7200,
    "expires_at": "2026-07-11T20:00:00",
    "refresh_token": null
  }
}
```

## Token Lifecycle

1. **Token fetch**: Connector obtains access token via client credentials grant
2. **Token storage**: Token saved to `connector_configs` table
3. **Token reuse**: Connector checks for valid cached token before new request
4. **Token refresh**: If token expires or is missing, fetches fresh token

## Error Handling

The connector handles:
- **401 Unauthorized**: Invalid credentials or expired token
- **429 Too Many Requests**: Rate limiting by eBay API
- **Network errors**: HTTP connection failures
- **Parsing errors**: Malformed API responses

## Testing

Run the test suite:

```bash
cd /home/hermes/pricerecon
source venv/bin/activate
PYTHONPATH=src:$PYTHONPATH python test_ebay_connector.py
```

Test coverage:
- OAuth token lifecycle (fetch, save, load, refresh)
- Search and listing parsing
- Condition filter mapping
- Error handling

## Integration with PriceRecon

The connector is registered via entry points in `pyproject.toml`:

```toml
[tool.entry-points."pricerecon.connectors"]
ebay = "pricerecon.connectors.ebay:eBayConnector"
```

Auto-discovery:
```python
from pricerecon.connectors import discover_connectors

connectors = discover_connectors()
# {"ebay": eBayConnector}

ebay = connectors["ebay"](app_id="...", cert_id="...")
```

## API Reference

### eBayConnector

```python
class eBayConnector(BaseConnector):
    def __init__(self, app_id: str, cert_id: Optional[str] = None, db_path: str = "pricerecon.db")
    async def initialize(self) -> None
    async def cleanup(self) -> None
    async def search(self, query: str, filters: Optional[dict] = None) -> list[NormalizedListing]
```

### Properties

- `source_role`: Always `SourceType.MARKETPLACE`
- `connector_id`: Always `"ebay"`

## Notes

- eBay Browse API is limited to **50 results per request** (hard limit)
- Tokens last approximately **2 hours**
- The connector applies a **5-minute buffer** before considering tokens expired
- Marketplace is configured for **UK (EBAY_GB)** - adjust `X-EBAY-C-MARKETPLACE-ID` for other regions
- Rate limits are enforced by eBay; the connector does not implement additional rate limiting