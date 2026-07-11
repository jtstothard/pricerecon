# PriceRecon

Self-hosted price tracking for search queries across multiple sources.

> "PCPartPicker watches pages. We watch markets."

## What is PriceRecon?

PriceRecon monitors **search queries across multiple heterogeneous sources** — retailers, peer-to-peer marketplaces, and community deal forums — with deterministic normalization, deduplication, and alerting.

Unlike existing tools that watch **product URLs**, PriceRecon watches **markets**. Define a search query ("RTX 3090, max £700, UK"), and the system searches across eBay, CeX, Amazon, Facebook Marketplace, Reddit, and retailers simultaneously, normalizes and deduplicates the results, and alerts on market movement.

## Features

- **Search-query-based monitoring** — not URL tracking
- **Multi-source with pluggable connectors** — add any source via code or config
- **Deterministic normalization and diff** — no LLM in the pipeline
- **Self-hosted with data ownership** — Docker, SQLite, your data
- **Custom notifications** — Telegram, Discord, webhooks, more

## Quickstart

### Docker (recommended)

```bash
docker-compose up -d
```

The app will be available at `http://localhost:8000`.

### Local development

```bash
# Install dependencies
pip install -e .

# Run the server
python -m pricerecon

# Or with uvicorn
uvicorn pricerecon.app:app --reload
```

## API

### Health check

```bash
curl http://localhost:8000/api/health
```

Response:
```json
{"status": "ok"}
```

## Project Structure

```
src/pricerecon/
├── api/          # FastAPI endpoints
├── connectors/   # Source connectors (eBay, CeX, Amazon, etc.)
├── models/       # Pydantic models (NormalizedListing, etc.)
├── db/           # Database schema and migrations
├── config.py     # Configuration management
├── app.py        # FastAPI application
├── cli.py        # CLI entry point
└── __main__.py   # python -m pricerecon entry point

connectors/       # Connector templates (YAML-based)
frontend/         # React + TypeScript frontend (future)
cli/             # CLI tool (future)
docs/            # Documentation (future)
```

## Connectors

PriceRecon supports two types of connectors:

### Code connectors
Python classes implementing the `BaseConnector` interface. Used when a source needs auth flows, multi-step pagination, tier fallbacks, or complex parsing.

Examples:
- **eBay** — Browse API with OAuth
- **CeX** — Algolia proxy API
- **Amazon** — `curl_cffi` with TLS fingerprint impersonation
- **FB Marketplace** — Playwright + stealth

### Config connectors
YAML files declaring endpoint, access method, request template, and field mapping. Used for simple sources.

### Config connectors
- Reddit RSS feeds
- HotUKDeals RSS
- Generic Shopify stores
- Simple HTML scrapers (CSS selectors)

## Facebook Marketplace caveat

The FB Marketplace connector uses Playwright plus browser fingerprinting and requires valid session cookies. Make sure your use complies with Facebook's terms and local policy. The connector is intended for self-hosted, low-rate, manual monitoring only.

## Database

PriceRecon uses SQLite by default. All data is stored in `pricerecon.db`:

- `watches` — Watch configurations
- `sources` — Connector configurations
- `listings` — Current listing snapshots
- `price_history` — Price time series
- `events` — Diff engine events
- `notifications` — Sent notification log
- `connector_configs` — Per-connector settings
- `deal_signals` — Signal source posts
- `schema_migrations` — Schema version tracking

## License

MIT License — see LICENSE file.

## Contributing

Contributions welcome! This is an open-source project for the community.

---

Built by Jay Stothard · [GitHub](https://github.com/jtstothard/pricerecon)