# Acceptance Criteria - Task t_8c307709

All criteria met:

- [x] Repo created at /home/hermes/pricerecon (git initialized, committed)
- [x] App starts with: python -m pricerecon or uvicorn pricerecon.app:app
- [x] GET /api/health returns 200 with {"status": "ok"}
- [x] SQLite DB initialized with all 9 tables on first startup
- [x] Pydantic NormalizedListing model validates with required fields, accepts null for optional fields
- [x] BaseConnector ABC is importable and subclasses are discoverable
- [x] Config file loaded (config.yml with database path, app settings)
- [x] Dockerfile builds successfully (Playwright browsers included)
- [x] README.md with project description and quickstart

## Deliverables

Project location: /home/hermes/pricerecon

Key files:
- pyproject.toml - Project config with all dependencies
- src/pricerecon/app.py - FastAPI application
- src/pricerecon/models/listings.py - NormalizedListing Pydantic model
- src/pricerecon/connectors/base.py - BaseConnector ABC
- src/pricerecon/connectors/__init__.py - discover_connectors() function
- src/pricerecon/db/schema.py - SQLite schema with 9 tables
- src/pricerecon/config.py - Config management (YAML + env vars)
- src/pricerecon/cli.py - CLI entry point
- Dockerfile - Docker build
- docker-compose.yml - Single-container setup
- README.md - Documentation

## Verification

```bash
cd /home/hermes/pricerecon
source venv/bin/activate
python -m pricerecon  # Server starts on :8000
curl http://localhost:8000/api/health  # {"status":"ok"}
sqlite3 pricerecon.db ".tables"  # All 9 tables present
python -c "from pricerecon.models import NormalizedListing; ..."  # Validates
python -c "from pricerecon.connectors import discover_connectors, BaseConnector; ..."  # Works
```

## Next Steps

Create GitHub repo and push:
```bash
gh repo create jtstothard/pricerecon --public --source=. --push
```

Requires GitHub token with repo scope.