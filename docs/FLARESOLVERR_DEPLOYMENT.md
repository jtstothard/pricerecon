# FlareSolverr Deployment for PriceRecon

## Overview

FlareSolverr is a proxy server that bypasses Cloudflare and DDoS-GUARD protection. PriceRecon uses it for connectors that target sites with aggressive anti-bot protections.

**12 connectors require FlareSolverr:**

| Connector | Site | Protection Level |
|-----------|------|------------------|
| AO.com | ao.com | High (Cloudflare) |
| Back Market | backmarket.com | High (Cloudflare) |
| Box | box.co.uk | High (Cloudflare) |
| CDKeys | cdkeys.com | High (Cloudflare) |
| Currys | currys.co.uk | High (Cloudflare) |
| Depop | depop.com | High (Cloudflare) |
| Etsy | etsy.com | High (Cloudflare) |
| Mercari | mercari.com | High (Cloudflare) |
| OnBuy | onbuy.com | High (Cloudflare) |
| Overclockers | overclockers.co.uk | High (Cloudflare) |
| Scan | scan.co.uk | High (Cloudflare) |
| Very.co.uk | very.co.uk | High (Cloudflare) |

**All tested sites return HTTP 403 with simple curl requests, confirming protection.**

## Architecture

FlareSolverr is deployed as a sidecar service that PriceRecon connects to via HTTP. The workflow:

```
PriceRecon (connector.search())
  ↓
TemplateConnector._fetch_html()
  ↓
FlareSolverrClient.request_html()
  ↓
POST {FLARESOLVERR_URL} with {"cmd": "request.get", "url": "<target>"}
  ↓
FlareSolverr container (solves challenge)
  ↓
Returns {"solution": {"response": "<html>"}}
  ↓
Parse listings from HTML
```

## Deployment Options

### Option 1: Docker Standalone (Recommended for Local Dev)

```bash
docker run -d \
  --name flaresolverr \
  -p 8191:8191 \
  -e LOG_LEVEL=info \
  flaresolverr/flaresolverr:latest

# Verify it's running
curl http://localhost:8191

# Should return JSON like {"status": "ok"}
```

Configure PriceRecon:

```yaml
# config.yml
flaresolverr_url: "http://localhost:8191"
```

Or via environment:

```bash
export PRICERECON_FLARESOLVERR_URL="http://localhost:8191"
```

### Option 2: Docker Compose (Production)

Add to `docker-compose.yml`:

```yaml
services:
  pricerecon:
    # ... existing config ...
    environment:
      - PRICERECON_FLARESOLVERR_URL=http://flaresolverr:8191
    depends_on:
      - flaresolverr
    networks:
      - media_back

  flaresolverr:
    image: flaresolverr/flaresolverr:latest
    container_name: flaresolverr
    ports:
      - "8191:8191"
    environment:
      - LOG_LEVEL=info
    networks:
      - media_back
    restart: unless-stopped

networks:
  media_back:
    external: true
```

Start:

```bash
docker-compose up -d
```

### Option 3: Remote Service (Multi-Host Setup)

If PriceRecon and FlareSolverr run on different hosts:

```yaml
# config.yml (on PriceRecon host)
flaresolverr_url: "http://docker-app-vm:8191/v1"
```

Ensure DNS resolution works or use IP address directly.

## Configuration Priority

FlareSolverr endpoint is resolved in this order (first wins):

1. Connector `__init__()` parameter: `BackMarketConnector(flaresolverr_url="...")`
2. Environment variable: `PRICERECON_FLARESOLVERR_URL`
3. Config file: `config.yml` → `flaresolverr_url`
4. Template file: `templates/backmarket.yml` → `flaresolverr_url`

## Verification

### Quick Check

Run the provided check script:

```bash
./scripts/check_flaresolverr.sh
```

This will:
- Detect configured endpoint
- Test connectivity
- Show deployment instructions if missing

### Live Connector Testing

After deploying FlareSolverr, verify connectors work:

```bash
python3 scripts/test_flaresolverr_connectors.py
```

This tests all FlareSolverr-dependent connectors with live queries.

Success criteria:
- **Pass**: ≥75% of connectors return listings (at least 6 of 8)
- **Fail**: <75% success rate

### Manual Verification

```bash
# Test FlareSolverr health
curl http://localhost:8191

# Should return {"status": "ok"}

# Test with a real URL
curl -X POST http://localhost:8191 \
  -H "Content-Type: application/json" \
  -d '{"cmd": "request.get", "url": "https://www.etsy.com/uk/search?q=iPhone+12"}'
```

## Troubleshooting

### Connectors Fail with `ConnectorDegradedError`

Symptom: All FlareSolverr connectors fail with "FlareSolverr request failed"

Diagnosis:
```bash
# Check if FlareSolverr is running
curl -v http://localhost:8191

# Check configured endpoint
grep flaresolverr_url config.yml
echo $PRICERECON_FLARESOLVERR_URL
```

Solution:
1. Ensure FlareSolverr container is running: `docker ps | grep flaresolverr`
2. Verify port is accessible: `ss -tlnp | grep 8191`
3. Check firewall rules
4. Verify endpoint configuration matches running service

### Connection Timeout

Symptom: `ConnectorStatus.timeout` errors

Possible causes:
1. FlareSolverr container not responding (check logs: `docker logs flaresolverr`)
2. Network issue (verify host connectivity)
3. Target site is blocking FlareSolverr IP

### Some Connectors Work, Others Don't

Possible causes:
1. Target site changed HTML structure (update selectors)
2. Target site implemented new protection (FlareSolverr may need update)
3. Connector-specific configuration issue

Check connector template and run manual test:
```bash
curl -X POST http://localhost:8191 \
  -H "Content-Type: application/json" \
  -d '{"cmd": "request.get", "url": "<target-search-url>"}'
```

## Performance Considerations

- FlareSolverr requests are slow (~5-15 seconds per request)
- Consider increasing `maxTimeout` for heavy pages:
  ```python
  await client.request_html(url, max_timeout=90000)  # 90 seconds
  ```
- For high-volume usage, run multiple FlareSolverr instances behind a load balancer

## Alternatives

If FlareSolverr is not viable, consider:
1. **Official APIs**: Check if site offers documented API (rare for marketplaces)
2. **Playwright**: Use `browser_client.py` for headless Chrome (slower, more resource-heavy)
3. **Proxy rotation**: Combine with residential proxies (commercial services)
4. **Skip connector**: Mark connector as disabled if not critical

## Security Notes

- FlareSolverr exposes an HTTP API that can be abused
- **In production**: Bind to localhost or use network isolation
- **In Docker**: Don't expose port 8191 publicly; use internal network only
- **Consider authentication**: FlareSolverr doesn't support auth, so use firewall rules

## Monitoring

Track FlareSolverr health:

```bash
# Check container health
docker ps --filter name=flaresolverr --format "table {{.Names}}\t{{.Status}}"

# Monitor resource usage
docker stats flaresolverr --no-stream

# Check logs
docker logs -f flaresolverr
```

Watch for:
- Container restarts (may indicate crashes)
- High memory usage (browser instances leaking)
- Request timeouts (target site issues)

## Maintenance

- Update FlareSolverr regularly: `docker pull flaresolverr/flaresolverr:latest`
- Monitor for browser exploit updates (FlareSolverr bundles Chromium)
- Review connector selector configs quarterly (sites change layouts)

## Related Files

- `/home/hermes/pricerecon/src/pricerecon/connectors/flaresolverr.py` - FlareSolverr client
- `/home/hermes/pricerecon/src/pricerecon/connectors/template_connector.py` - Integration
- `/home/hermes/pricerecon/src/pricerecon/connectors/templates/*.yml` - Connector configs
- `/home/hermes/pricerecon/config.yml` - Runtime configuration
- `/home/hermes/pricerecon/docker-compose.yml` - Deployment config
- `/home/hermes/pricerecon/scripts/check_flaresolverr.sh` - Verification script
- `/home/hermes/pricerecon/scripts/test_flaresolverr_connectors.py` - Live testing