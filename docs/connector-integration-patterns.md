# Connector Integration Patterns

This guide documents three integration patterns for connector implementations:

1. **FlareSolverr bypass** — for anti-bot protected sources (Cloudflare/DataDome/Akamai)
2. **Camofox/browser-assisted** — for SPA/JS-rendered sources requiring full browser
3. **Auth fields** — for sources requiring credentials (username/password, membership ID, session cookies)

These patterns build on the [Connector Development Guide](connector-development.md).

---

## FlareSolverr Bypass Pattern

### Overview

FlareSolverr is a proxy service that solves Cloudflare, DataDome, and Akamai challenges by launching a real browser and returning the rendered HTML. It's ideal for sources that block automated HTTP requests but don't require JavaScript execution for content rendering.

### Infrastructure

- **Service**: FlareSolverr (HTTP API)
- **Deployment**: `docker-app-vm`
- **URL**: `http://docker-app-vm:8191/v1`
- **Protocol**: POST with JSON payload

### When to Use

Use FlareSolverr when:
- HTTP requests return 403 (bot detection) or challenge pages
- The source uses Cloudflare, DataDome, or Akamai protection
- Content is server-rendered HTML (no SPA/JS dependency)
- You need raw HTML for parsing

Do NOT use when:
- Content requires JavaScript execution to render (use Camofox instead)
- Source has strict rate limiting that browser requests won't bypass

### Implementation

Use the `FlareSolverrClient` from `pricerecon.connectors.flaresolverr`:

```python
from pricerecon.connectors.flaresolverr import FlareSolverrClient
from pricerecon.connectors.base import BaseConnector
from pricerecon.models import NormalizedListing, SourceType
from typing import Optional
import httpx

class MyRetailerConnector(BaseConnector):
    def __init__(self, flaresolverr_url: str | None = None):
        # Configuration: fall back to global config or explicit value
        from pricerecon.config import get_global_config
        global_config = get_global_config()
        
        self.flaresolverr_url = (
            flaresolverr_url 
            or global_config.get("flaresolverr_url")
            or "http://docker-app-vm:8191/v1"
        )
        self._flaresolverr_client: Optional[FlareSolverrClient] = None
        self._client: Optional[httpx.AsyncClient] = None

    async def initialize(self) -> None:
        if self.flaresolverr_url:
            self._flaresolverr_client = FlareSolverrClient(self.flaresolverr_url)
        
        # Regular httpx client for non-protected endpoints
        self._client = httpx.AsyncClient(timeout=30.0)

    async def cleanup(self) -> None:
        if self._client:
            await self._client.aclose()

    async def search(
        self, query: str, filters: Optional[dict] = None
    ) -> list[NormalizedListing]:
        search_url = f"https://myretailer.com/search?q={query}"
        
        # Try FlareSolverr first if configured
        if self._flaresolverr_client:
            try:
                html = await self._flaresolverr_client.request_html(search_url)
                return self._parse_html(html)
            except Exception as exc:
                # Log warning but don't fail completely
                logger.warning("FlareSolverr request failed: %s", exc)
                # Optionally fall back to direct request
        
        # Direct request (may fail on protected sources)
        if self._client:
            response = await self._client.get(search_url)
            response.raise_for_status()
            return self._parse_html(response.text)
        
        raise ValueError("Neither FlareSolverr nor direct client available")

    def _parse_html(self, html: str) -> list[NormalizedListing]:
        # Parse HTML with BeautifulSoup, parsel, or similar
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        
        listings = []
        for product_card in soup.select(".product-card"):
            # Extract listing data...
            listing = NormalizedListing(
                source=self.connector_id,
                source_type=self.source_role,
                source_listing_id=product_card["data-id"],
                title_raw=product_card.select_one(".title").text,
                # ... other fields
            )
            listings.append(listing)
        
        return listings
```

### FlareSolverrClient API

```python
class FlareSolverrClient:
    def __init__(self, endpoint: str, timeout: float = 90.0):
        """
        Args:
            endpoint: FlareSolverr API URL (e.g., "http://docker-app-vm:8191/v1")
            timeout: HTTP client timeout for the FlareSolverr request
        """

    async def request_html(self, url: str, *, max_timeout: int = 60000) -> str:
        """
        Fetch HTML via FlareSolverr.
        
        Args:
            url: Target URL to fetch
            max_timeout: Maximum time for FlareSolverr to solve challenge (ms)
        
        Returns:
            Rendered HTML string
        
        Raises:
            httpx.HTTPStatusError: If FlareSolverr request fails
            ValueError: If response structure is invalid
        """
```

### Request Flow

```
Connector → POST http://docker-app-vm:8191/v1
           Payload: {"cmd": "request.get", "url": "https://...", "maxTimeout": 60000}
           ↓
FlareSolverr → Launch browser → Solve challenge → Return HTML
           ↓
Connector ← Response: {"solution": {"response": "<html>...</html>", "status": 200}}
```

### Error Handling

```python
try:
    html = await self._flaresolverr_client.request_html(url)
except httpx.HTTPStatusError as exc:
    if exc.response.status_code == 504:
        # FlareSolverr timeout (challenge took too long)
        logger.error("FlareSolverr timeout: %s", url)
    else:
        # FlareSolverr service error (down, misconfigured)
        logger.error("FlareSolverr service error: %s", exc)
    raise
except ValueError as exc:
    # Invalid response structure
    logger.error("FlareSolverr returned invalid response: %s", exc)
    raise
```

### Configuration

Add to global `config.yml`:

```yaml
# FlareSolverr endpoint (for Cloudflare-protected retailers)
flaresolverr_url: "http://docker-app-vm:8191/v1"

# Or per-connector in watch config:
sources:
  - connector: myretailer
    config:
      flaresolverr_url: "http://docker-app-vm:8191/v1"
```

### Existing Examples

- `Box` connector — uses FlareSolverr for search pages
- `Currys` connector — uses FlareSolverr for all product pages
- `Scan` connector — uses FlareSolverr for category pages

---

## Camofox Browser-Assisted Pattern

### Overview

Camofox is a remote browser service that runs Playwright browsers and exposes them via a REST API. It's ideal for Single Page Applications (SPAs) and sources where content is rendered via JavaScript.

### Infrastructure

- **Service**: Camofox REST API
- **Deployment**: `192.168.10.252:9377`
- **Protocol**: REST API with `/tabs` and `/sessions` endpoints
- **Authentication**: Bearer token (optional, via `Authorization` header)

### When to Use

Use Camofox when:
- Source is a SPA (React, Vue, Angular) requiring JS execution
- Content loads dynamically after page load (lazy loading, infinite scroll)
- Source requires browser fingerprints or stealth techniques
- You need to interact with the page (click buttons, scroll, wait for elements)

Do NOT use when:
- Source is simple server-rendered HTML (use FlareSolverr or direct HTTP)
- Performance is critical (browser is slower than HTTP)

### Implementation

Use the `BrowserClient` from `pricerecon.connectors.browser_client`:

```python
from pricerecon.connectors.browser_client import BrowserClient, BrowserSessionConfig
from pricerecon.connectors.base import BaseConnector
from pricerecon.models import NormalizedListing, SourceType
from typing import Optional

class MySPAConnector(BaseConnector):
    def __init__(self, camofox_url: str | None = None):
        self.camofox_url = camofox_url or "http://192.168.10.252:9377"
        self._browser_client: Optional[BrowserClient] = None
        self._context: Optional[Any] = None

    async def initialize(self) -> None:
        config = BrowserSessionConfig(
            headless=True,
            viewport_width=1366,
            viewport_height=768,
            locale="en-GB",
            timezone_id="Europe/London",
            camofox_url=self.camofox_url,
            camofox_user_id="pricerecon-myspa",  # Unique ID for this connector
            camofox_session_key="watcher",
        )
        self._browser_client = BrowserClient(config=config)
        self._context = await self._browser_client.new_context()

    async def cleanup(self) -> None:
        if self._context:
            await self._context.close()
        if self._browser_client:
            await self._browser_client.close()

    async def search(
        self, query: str, filters: Optional[dict] = None
    ) -> list[NormalizedListing]:
        page = await self._context.new_page()
        
        try:
            # Navigate to search page
            await page.goto(f"https://myspa.com/search?q={query}", timeout=30000)
            
            # Wait for results to load
            await page.wait_for_selector(".product-card", timeout=15000)
            
            # Extract data from page
            listings_data = await page.eval_on_selector_all(
                ".product-card",
                """elements => elements.map(el => ({
                    id: el.dataset.id,
                    title: el.querySelector('.title')?.textContent,
                    price: el.querySelector('.price')?.textContent,
                    url: el.querySelector('a')?.href,
                }))"""
            )
            
            return self._parse_listings(listings_data)
        finally:
            # Close the remote tab
            await page.close()

    def _parse_listings(self, items: list[dict]) -> list[NormalizedListing]:
        from decimal import Decimal
        
        listings = []
        for item in items:
            listing = NormalizedListing(
                source=self.connector_id,
                source_type=self.source_role,
                source_listing_id=str(item["id"]),
                title_raw=item["title"],
                price=Decimal(item["price"].replace("£", "")),
                currency="GBP",
                url=item["url"],
                # ... other fields
            )
            listings.append(listing)
        
        return listings
```

### BrowserSessionConfig Options

```python
@dataclass
class BrowserSessionConfig:
    headless: bool = True
    viewport_width: int = 1366
    viewport_height: int = 768
    user_agent: str | None = None
    locale: str = "en-GB"
    timezone_id: str = "Europe/London"
    
    # Camofox-specific
    camofox_url: str | None = None
    camofox_user_id: str | None = None  # Identifier for this connector
    camofox_session_key: str | None = None  # Session grouping key
    camofox_api_key: str | None = None  # Bearer token for auth
    camofox_access_key: str | None = None  # Alternative to api_key
```

### Request Flow

```
Connector → BrowserClient (uses Camofox if camofox_url set)
         ↓
    POST http://192.168.10.252:9377/tabs
    Payload: {"userId": "...", "sessionKey": "...", "url": "https://..."}
         ↓
Camofox → Launch browser → Navigate → Render JS
         ↓
    GET http://192.168.10.252:9377/tabs/{tabId}/snapshot?format=text
         ↓
Connector ← HTML content of rendered page
```

### Page Interaction Pattern

```python
page = await self._context.new_page()

try:
    # Navigate
    await page.goto(url, wait_until="networkidle", timeout=30000)
    
    # Wait for specific element
    await page.wait_for_selector(".results", timeout=15000)
    
    # Scroll if needed (infinite scroll)
    for _ in range(3):
        await page.evaluate("window.scrollBy(0, 1000)")
        await page.wait_for_timeout(1000)
    
    # Extract data
    data = await page.eval_on_selector_all(".item", "...")
    
    # Or get raw HTML
    html = await page.content()
    
finally:
    await page.close()  # Important: closes remote tab
```

### Adding Session Cookies

```python
async def initialize(self) -> None:
    config = BrowserSessionConfig(camofox_url=self.camofox_url, ...)
    self._browser_client = BrowserClient(config=config)
    
    # Load cookies from environment
    cookies = [
        {"name": "session", "value": os.getenv("SESSION_COOKIE")},
        {"name": "auth", "value": os.getenv("AUTH_COOKIE")},
    ]
    
    self._context = await self._browser_client.new_context(cookies=cookies)
```

### Error Handling

```python
try:
    await page.goto(url, timeout=30000)
except Exception as exc:
    if "timeout" in str(exc).lower():
        logger.error("Page load timeout: %s", url)
    elif "403" in str(exc).lower() or "blocked" in str(exc).lower():
        logger.error("Page blocked by bot detection: %s", url)
    raise
```

### Configuration

Add to global `config.yml`:

```yaml
connectors:
  myspa:
    enabled: true
    camofox_url: "http://192.168.10.252:9377"
    camofox_user_id: "pricerecon-myspa"
    camofox_api_key: null  # Optional: set if Camofox requires auth
```

Or per-watch config:

```yaml
sources:
  - connector: myspa
    config:
      camofox_url: "http://192.168.10.252:9377"
```

### Existing Examples

- `AliExpress` connector — uses Camofox for product detail pages
- `browser_client.py` — shared utilities for browser-based connectors

### Performance Notes

- Camofox is slower than direct HTTP (~3-10x slower)
- Each page creates a remote tab; always close tabs in `finally` blocks
- Use `wait_for_selector` instead of fixed delays
- Batch requests when possible (multiple pages per context)

---

## Auth Fields Pattern

### Overview

Some sources require authentication credentials to access data. This pattern covers how to configure and use credential fields (username/password, membership ID, API keys, session cookies) in connectors.

### Credential Types

| Type | Use Case | Storage |
|------|----------|---------|
| **API Key** | API authentication | Environment variable or config |
| **Username/Password** | Login forms | Environment variable |
| **Membership ID** | Membership-only access | Watch config |
| **Session Cookies** | Logged-in state | Environment variable |

### Implementation: Environment Variables

For secrets like API keys or session cookies, use environment variables:

```python
import os
from pricerecon.connectors.base import BaseConnector

class MyAuthenticatedConnector(BaseConnector):
    def __init__(self):
        self.api_key = os.getenv("MYSTORE_API_KEY")
        self.session_cookie = os.getenv("MYSTORE_SESSION_COOKIE")
        
        # Validate required credentials
        if not self.api_key:
            raise ValueError("MYSTORE_API_KEY environment variable required")
    
    async def initialize(self) -> None:
        # Validate credentials work
        if self.api_key:
            headers = {"Authorization": f"Bearer {self.api_key}"}
            # Make test request to verify auth...
```

### Implementation: Config-Based Auth Fields

For per-watch credentials (like membership IDs), use the connector config:

```python
from pricerecon.config import get_global_config

class MembershipConnector(BaseConnector):
    def __init__(self, config: dict | None = None):
        self.config = config or {}
        
        # Get membership ID from watch-specific config
        self.membership_id = self.config.get("membership_id")
        if not self.membership_id:
            # Fall back to global config
            global_config = get_global_config()
            connector_config = global_config.get("connectors", {}).get("membership", {})
            self.membership_id = connector_config.get("membership_id")
    
    async def search(self, query: str, filters: dict | None = None) -> list[NormalizedListing]:
        if not self.membership_id:
            raise ValueError("membership_id is required in connector config")
        
        # Use membership_id in requests
        headers = {"X-Membership-ID": self.membership_id}
        # ...
```

### Config Schema Examples

#### Global Config (`config.yml`)

```yaml
connectors:
  mystore:
    enabled: true
    # Shared API key (if all watches use same credentials)
    api_key: null  # Set via env var instead: MYSTORE_API_KEY
    membership_id: null  # Optional default membership ID
  
  membership_retailer:
    enabled: true
    membership_id: "DEFAULT_MEMBER_123"  # Shared membership (optional)
```

#### Watch-Specific Config

```yaml
sources:
  - connector: mystore
    config:
      membership_id: "MEMBER_456"  # Override for this watch
```

#### Environment Variables

```bash
# Set in .env or export directly
export MYSTORE_API_KEY="sk_live_..."
export MYSTORE_SESSION_COOKIE="session=abc123; auth=xyz789"
```

### Schema for Auth Fields

Add to connector `__init__` to validate config schema:

```python
from typing import Any
from pydantic import BaseModel, Field, field_validator

class ConnectorConfig(BaseModel):
    """Schema for this connector's config."""
    
    membership_id: str | None = Field(
        default=None,
        description="Membership ID for member-only pricing"
    )
    
    api_key_override: str | None = Field(
        default=None,
        description="Override default API key for this watch"
    )
    
    @field_validator("membership_id")
    @classmethod
    def validate_membership(cls, v: str | None) -> str | None:
        if v is not None and not v.strip():
            raise ValueError("membership_id cannot be empty")
        return v

class MyConnector(BaseConnector):
    def __init__(self, config: dict | None = None):
        # Validate and parse config
        parsed_config = ConnectorConfig(**(config or {}))
        self.membership_id = parsed_config.membership_id
        # ...
```

### Session Cookie Pattern

For sources requiring logged-in sessions:

```python
import os
from pricerecon.connectors.browser_client import BrowserClient, BrowserSessionConfig

class SessionAuthConnector(BaseConnector):
    async def initialize(self) -> None:
        # Load cookies from environment
        session_cookie = os.getenv("STORE_SESSION_COOKIE")
        if not session_cookie:
            raise ValueError("STORE_SESSION_COOKIE environment variable required")
        
        # Parse cookie string (format: "name1=value1; name2=value2")
        cookies = []
        for pair in session_cookie.split(";"):
            if "=" in pair:
                name, value = pair.strip().split("=", 1)
                cookies.append({"name": name, "value": value})
        
        # Create browser context with cookies
        config = BrowserSessionConfig(
            camofox_url=self.camofox_url,
            camofox_user_id="pricerecon-session",
        )
        self._browser_client = BrowserClient(config=config)
        self._context = await self._browser_client.new_context(cookies=cookies)
```

### Error Handling for Missing Credentials

```python
def __init__(self, config: dict | None = None):
    self.config = config or {}
    
    # Try multiple sources for credentials
    self.api_key = (
        self.config.get("api_key")  # Watch-specific
        or os.getenv("MYSTORE_API_KEY")  # Environment
        or get_global_config().get("connectors", {}).get("mystore", {}).get("api_key")  # Global
    )
    
    if not self.api_key:
        raise ValueError(
            "API key required. Set via: "
            "1) sources[].config.api_key in watch config, "
            "2) MYSTORE_API_KEY environment variable, or "
            "3) connectors.mystore.api_key in config.yml"
        )
```

### Testing with Mock Credentials

```python
import pytest

@pytest.fixture
def mock_connector():
    """Create connector with test credentials."""
    os.environ["MYSTORE_API_KEY"] = "test_key_123"
    return MyConnector()

@pytest.mark.asyncio
async def test_search_with_auth(mock_connector, respx_mock):
    await mock_connector.initialize()
    
    # Mock API to check Authorization header
    def check_auth(request):
        assert "Authorization" in request.headers
        assert "test_key_123" in request.headers["Authorization"]
        return True
    
    respx_mock.get("https://api.mystore.com/search").mock(
        return_value=httpx.Response(200, json={"products": []}),
        side_effect=check_auth
    )
    
    await mock_connector.search("test")
```

### Security Best Practices

1. **Never hardcode credentials** in source code
2. **Use environment variables** for secrets (API keys, passwords)
3. **Use config files** for non-sensitive values (membership IDs)
4. **Document required credentials** in connector docstring
5. **Validate credentials** on initialization (fail fast)
6. **Log warnings** for missing optional credentials

### Existing Examples

- `eBay` connector — uses `app_id` from config for OAuth
- `AliExpress` connector — uses DS credentials (`ae_user_id`, `ae_token`) from config

### Example: Full Auth Connector

```python
"""Example connector with multiple auth patterns."""

import os
import logging
from typing import Any, Optional

import httpx

from pricerecon.connectors.base import BaseConnector
from pricerecon.config import get_global_config
from pricerecon.models import NormalizedListing, SourceType

logger = logging.getLogger(__name__)


class AuthExampleConnector(BaseConnector):
    """Connector showing various auth patterns."""
    
    CONNECTOR_ID = "authexample"
    
    def __init__(self, config: dict | None = None):
        self.config = config or {}
        
        # Pattern 1: API key from environment (secret)
        self.api_key = os.getenv("AUTHEXAMPLE_API_KEY")
        
        # Pattern 2: Membership ID from config (non-secret)
        self.membership_id = (
            self.config.get("membership_id")
            or get_global_config().get("connectors", {}).get("authexample", {}).get("membership_id")
        )
        
        # Validate required credentials
        if not self.api_key:
            raise ValueError("AUTHEXAMPLE_API_KEY environment variable required")
        
        if not self.membership_id:
            raise ValueError("membership_id required in connector config")
        
        self._client: Optional[httpx.AsyncClient] = None
    
    @property
    def source_role(self) -> SourceType:
        return SourceType.RETAILER
    
    async def initialize(self) -> None:
        """Initialize HTTP client and validate credentials."""
        self._client = httpx.AsyncClient(timeout=30.0)
        
        # Validate credentials work with a test request
        try:
            response = await self._client.get(
                "https://api.authexample.com/validate",
                headers={"Authorization": f"Bearer {self.api_key}"}
            )
            response.raise_for_status()
            logger.info("AuthExample credentials validated")
        except httpx.HTTPStatusError as exc:
            raise ValueError(f"Invalid credentials: {exc}")
    
    async def cleanup(self) -> None:
        if self._client:
            await self._client.aclose()
    
    async def search(
        self, query: str, filters: Optional[dict[str, Any]] = None
    ) -> list[NormalizedListing]:
        """Search with authentication headers."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "X-Membership-ID": self.membership_id,
        }
        
        response = await self._client.get(
            "https://api.authexample.com/search",
            params={"q": query},
            headers=headers
        )
        response.raise_for_status()
        
        return self._parse_listings(response.json().get("items", []))
    
    def _parse_listings(self, items: list[dict]) -> list[NormalizedListing]:
        from decimal import Decimal
        from datetime import datetime
        
        listings = []
        for item in items:
            try:
                listing = NormalizedListing(
                    source=self.connector_id,
                    source_type=self.source_role,
                    source_listing_id=str(item["id"]),
                    title_raw=item["title"],
                    price=Decimal(str(item["price"])),
                    currency="GBP",
                    url=item["url"],
                    timestamp_seen=datetime.utcnow(),
                )
                listings.append(listing)
            except Exception as exc:
                logger.warning("Failed to parse listing: %s", exc)
        
        return listings
```

---

## Pattern Selection Guide

| Source Characteristics | Recommended Pattern |
|------------------------|---------------------|
| Anti-bot protection (403), server-rendered HTML | **FlareSolverr** |
| SPA/JS-rendered, lazy loading, infinite scroll | **Camofox** |
| Simple HTML, no protection | Direct HTTP (no pattern needed) |
| Requires API key | **Auth Fields** (env var) |
| Requires login/session | **Auth Fields** + **Camofox** |
| Member-only pricing | **Auth Fields** (config) |

### Combining Patterns

You can combine patterns as needed:

```python
class CombinedPatternConnector(BaseConnector):
    async def initialize(self) -> None:
        # Use FlareSolverr for anti-bot bypass
        self._flaresolverr_client = FlareSolverrClient(flaresolverr_url)
        
        # Use Camofox for JS rendering
        config = BrowserSessionConfig(camofox_url=camofox_url, ...)
        self._browser_client = BrowserClient(config=config)
        
        # Load auth credentials
        self.api_key = os.getenv("API_KEY")
        self.cookies = self._load_cookies()
```

---

## Testing Patterns

### FlareSolverr Test

```python
import pytest
from pricerecon.connectors.flaresolverr import FlareSolverrClient

@pytest.mark.asyncio
async def test_flaresolverr_request():
    client = FlareSolverrClient("http://docker-app-vm:8191/v1")
    
    # Mock httpx in tests, or use real endpoint in integration tests
    html = await client.request_html("https://example.com")
    
    assert "<html" in html
```

### Camofox Test

```python
@pytest.mark.asyncio
async def test_browser_client_camofox():
    config = BrowserSessionConfig(camofox_url="http://192.168.10.252:9377")
    client = BrowserClient(config=config)
    
    context = await client.new_context()
    page = await context.new_page()
    
    await page.goto("https://example.com")
    content = await page.content()
    
    assert "<html" in content
    await page.close()
    await context.close()
    await client.close()
```

### Auth Fields Test

```python
import os
import pytest

@pytest.fixture
def mock_env():
    os.environ["API_KEY"] = "test_key"
    yield
    del os.environ["API_KEY"]

def test_auth_validation(mock_env):
    connector = MyConnector()
    assert connector.api_key == "test_key"
```

---

## Troubleshooting

### FlareSolverr Issues

**Issue**: "FlareSolverr timeout"
- **Cause**: Challenge solving took too long (> 60s)
- **Fix**: Increase `max_timeout` parameter, or use Camofox for complex challenges

**Issue**: "FlareSolverr returned invalid response"
- **Cause**: FlareSolverr service misconfigured or returned unexpected JSON
- **Fix**: Check FlareSolverr logs, verify endpoint URL

### Camofox Issues

**Issue**: "Page load timeout"
- **Cause**: Page takes too long to render
- **Fix**: Increase `timeout` in `page.goto()`, use `wait_until="networkidle"`

**Issue**: "Remote tab not closed"
- **Cause**: Forgetting to call `page.close()`
- **Fix**: Always use `try/finally` blocks to close tabs

### Auth Issues

**Issue**: "Credentials required"
- **Cause**: Missing environment variable or config value
- **Fix**: Set required credential, or use fallback pattern

**Issue**: "Invalid credentials"
- **Cause**: API key or membership ID is wrong
- **Fix**: Verify credentials with manual test request

---

## See Also

- [Connector Development Guide](connector-development.md) — Base connector interface and patterns
- [FlareSolverr GitHub](https://github.com/FlareSolverr/FlareSolverr) — Official FlareSolverr documentation
- [Existing connectors](../src/pricerecon/connectors/) — Reference implementations