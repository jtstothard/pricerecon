# PriceRecon

> Self-hosted price tracking for search queries across multiple sources.

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](https://www.docker.com/)

> "PCPartPicker watches pages. We watch markets."

## What is PriceRecon?

PriceRecon monitors **search queries across multiple heterogeneous sources** — retailers, peer-to-peer marketplaces, and community deal forums — with deterministic normalization, deduplication, and alerting.

Unlike existing tools that watch **product URLs**, PriceRecon watches **markets**. Define a search query (e.g., "RTX 3090, max £700, UK"), and the system searches across eBay, CeX, Amazon, Facebook Marketplace, Reddit, and retailers simultaneously, normalizes and deduplicates the results, and alerts on market movement.

## Key Features

- **Search-query-based monitoring** — Not URL tracking. Define a query, let the system find the listings.
- **18+ built-in connectors** — eBay, CeX, Amazon, Facebook Marketplace, Reddit, HotUKDeals, and more.
- **Deterministic diff engine** — Detects new listings, price drops, price increases, stock changes, and gone listings.
- **Self-hosted with data ownership** — Docker, SQLite, your data on your hardware.
- **Custom notifications** — Telegram, Discord, webhooks, and extensible notification system.
- **Pluggable connector architecture** — Add any source via Python or YAML config.

## Quick Start

### Docker (Recommended)

```bash
# Clone the repository
git clone https://github.com/jtstothard/pricerecon.git
cd pricerecon

# Copy environment template and configure
cp .env.example .env
# Edit .env with your API keys and credentials

# Start with Docker Compose
docker-compose up -d

# The app will be available at http://localhost:8000
```

### Local Development

```bash
# Create a virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"

# Run the server
python -m pricerecon

# Or with uvicorn
uvicorn pricerecon.app:app --reload
```

## Configuration

Copy `.env.example` to `.env` and configure:

```bash
# Core API auth
PRICERECON_API_KEY=your-secret-key

# eBay credentials (for eBay connector)
EBAY_APP_ID=your-ebay-app-id
EBAY_CERT_ID=your-ebay-cert-id

# Facebook Marketplace cookies (HttpOnly session cookies)
# Required for FB Marketplace connector
FB_C_USER=your-c-user-cookie
FB_XS=your-xs-cookie
FB_DATR=your-datr-cookie
FB_FR=your-fr-cookie
FB_SB=your-sb-cookie

# Messaging integrations
TELEGRAM_BOT_TOKEN=your-telegram-bot-token
DISCORD_WEBHOOK_URL=your-discord-webhook-url

# Optional browser / anti-bot services
FLARESOLVERR_URL=http://localhost:8191
```

See [`.env.example`](.env.example) for all available options.

## Supported Sources

| Source | Type | Auth | Notes |
|--------|------|------|-------|
| **eBay** | Marketplace | OAuth 2.0 | Browse API, official API |
| **Amazon** | Retailer | curl_cffi | TLS fingerprint impersonation |
| **CeX** | Marketplace | None | Algolia proxy API |
| **Facebook Marketplace** | Marketplace | Session cookies | Playwright + stealth (see caveat below) |
| **Reddit** | Signal | None | RSS feeds |
| **HotUKDeals** | Signal | None | RSS feeds |
| **Box** | Retailer | FlareSolverr | Anti-bot bypass |
| **Currys** | Retailer | FlareSolverr | Anti-bot bypass |
| **Ebuyer** | Retailer | FlareSolverr | Anti-bot bypass |
| **CCL** | Retailer | FlareSolverr | Anti-bot bypass |
| **Novatech** | Retailer | FlareSolverr | Anti-bot bypass |
| **Scan** | Retailer | FlareSolverr | Anti-bot bypass |
| **Overclockers** | Retailer | FlareSolverr | Anti-bot bypass |
| **Aria** | Retailer | FlareSolverr | Anti-bot bypass |
| **Shopify** | Marketplace | None | Generic Shopify stores |
| **HTML Generic** | Retailer | None | CSS selector-based scrapers |

### Source Types

- **Retailer** — Official retailer sites, single seller per listing
- **Marketplace** — Multi-seller platforms with user listings
- **Signal** — Community forums, deal aggregators, RSS feeds

### Facebook Marketplace Caveat

The FB Marketplace connector uses Playwright with browser fingerprinting and requires valid session cookies. Make sure your use complies with Facebook's terms and local policy. The connector is intended for self-hosted, low-rate, manual monitoring only.

## How to Add a Connector

PriceRecon supports two types of connectors:

### 1. Python Connectors (Code)

For sources requiring auth flows, multi-step pagination, or complex parsing:

```python
from pricerecon.connectors.base import BaseConnector
from pricerecon.models import NormalizedListing, SourceType

class MyConnector(BaseConnector):
    @property
    def source_role(self) -> SourceType:
        return SourceType.MARKETPLACE

    async def search(self, query: str, filters: dict | None = None) -> list[NormalizedListing]:
        # Implement search logic
        return [NormalizedListing(
            source="my_source",
            source_type=self.source_role,
            source_listing_id="123",
            title_raw="Product Title",
            price=Decimal("99.99"),
            currency="GBP",
            url="https://example.com/item/123",
        )]
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full connector development guide.

### 2. YAML Config Connectors

For simple sources without auth, configure via YAML:

```yaml
# connectors/my_retailer.yml
name: my_retailer
base_url: https://example.com
search_endpoint: /search
method: GET
params:
  q: "{{query}}"
listings_selector: .product-card
fields:
  title:
    selector: .title
  price:
    selector: .price
    type: numeric
  url:
    selector: a
    attribute: href
```

## API

### Health Check

```bash
curl http://localhost:8000/api/health
```

Response:
```json
{"status": "ok", "connector_states": {...}}
```

### Create a Watch

```bash
curl -X POST http://localhost:8000/api/watches \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d '{
    "query": "RTX 3090",
    "filters": {"price_max": 700, "region": "UK"},
    "sources": ["ebay", "cex", "amazon"]
  }'
```

### List Events

```bash
curl http://localhost:8000/api/events?watch_id=1 \
  -H "Authorization: Bearer YOUR_API_KEY"
```

## Database Schema

PriceRecon uses SQLite by default. All data is stored in `pricerecon.db`:

| Table | Purpose |
|-------|---------|
| `watches` | Watch configurations |
| `sources` | Connector configurations |
| `listings` | Current listing snapshots |
| `price_history` | Price time series |
| `events` | Diff engine events |
| `notifications` | Sent notification log |
| `connector_configs` | Per-connector settings |
| `deal_signals` | Signal source posts |
| `schema_migrations` | Schema version tracking |

## Documentation

- **[Connector Development Guide](docs/connector-development.md)** — Build connectors, understand the diff engine
- **[CONTRIBUTING.md](CONTRIBUTING.md)** — Contribution guidelines and PR checklist

## License

MIT License — see [LICENSE](LICENSE) file.

## Contributing

Contributions welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

Built by Jay Stothard · [GitHub](https://github.com/jtstothard/pricerecon)