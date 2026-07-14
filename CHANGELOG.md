# Changelog

All notable changes to PriceRecon are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **FlareSolverr deployment documentation** (`docs/FLARESOLVERR_DEPLOYMENT.md`)
  - Comprehensive deployment guide for FlareSolverr service
  - Docker standalone, Docker Compose, and multi-host deployment options
  - Configuration priority and endpoint resolution
  - Troubleshooting guide with common issues and solutions
  - Performance and security considerations

- **Connector requirements documentation** (`docs/CONNECTOR_REQUIREMENTS.md`)
  - Categorization of all connectors by dependency (FlareSolverr, direct HTTP, browser, auth)
  - Quick reference table showing which connectors require FlareSolverr
  - Auth requirements per connector (eBay, Facebook, Costco, AliExpress)
  - Browser-assisted connectors distinction

- **FlareSolverr verification script** (`scripts/check_flaresolverr.sh`)
  - Automated detection of configured FlareSolverr endpoint
  - Connectivity testing against common endpoints
  - Deployment instruction generation when FlareSolverr is not running
  - Lists all FlareSolverr-dependent connectors

- **FlareSolverr connector testing script** (`scripts/test_flaresolverr_connectors.py`)
  - Live testing of all 7 FlareSolverr batch connectors
  - Tests Back Market, Depop, Mercari, OnBuy, Etsy, Very.co.uk, CDKeys
  - Success rate threshold (75% = healthy)
  - Detailed error reporting per connector

### Changed
- Updated README.md "Optional browser / anti-bot services" section
  - Now points to comprehensive deployment documentation
  - Clarified FlareSolverr requirement for specific connectors

### Fixed
- Identified FlareSolverr deployment gap in t_7db2a64c
  - 12 connectors blocked without FlareSolverr service
  - Config file referenced non-existent `http://docker-app-vm:8191/v1`
  - All tested sites confirmed to require anti-bot bypass (HTTP 403 on direct requests)

### Technical Debt
- FlareSolverr service not deployed or configured
- 12 FlareSolverr-dependent connectors will fail with `ConnectorDegradedError` until service is deployed
- Config file contains stale endpoint reference (`docker-app-vm` hostname not resolvable)

## [0.5.0] - 2026-07-14

### Added
- FlareSolverr batch connectors: Back Market, Depop, Mercari UK, OnBuy, Etsy, Very.co.uk, AO.com, CDKeys
- TemplateConnector with FlareSolverr bypass support
- FlareSolverrClient for anti-bot protected sites
- Costco UK connector with session-based authentication
- Google Shopping connector (browser-based scraping)
- BT Shop slice removal (retired source, redirects to EE)

### Changed
- Refactored Shopify connector to require store-specific `base_url`
- Fixed Reddit and HUKD connectors to use canonical feeds
- Improved AliExpress fallback lanes on affiliate search failure
- Corrected source types and proactive eBay health checks

### Removed
- BT Shop connector (shop.bt.com redirects with Incapsula, businessdirect.bt.com shows maintenance)

---

For earlier releases, see [GitHub Releases](https://github.com/jtstothard/pricerecon/releases).