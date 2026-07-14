# Argos + MusicMagpie Connectors

## Implementation Summary

Both Argos and MusicMagpie connectors have been implemented using the browser-assisted pattern.

### Files Created

1. **Connector Classes:**
   - `/home/hermes/pricerecon/src/pricerecon/connectors/argos.py` - Argos connector
   - `/home/hermes/pricerecon/src/pricerecon/connectors/musicmagpie.py` - MusicMagpie connector

2. **Seed Scripts:**
   - `/home/hermes/pricerecon/seed_argos.py` - DB seed for Argos
   - `/home/hermes/pricerecon/seed_musicmagpie.py` - DB seed for MusicMagpie

3. **Tests:**
   - `/home/hermes/pricerecon/tests/test_argos_musicmagpie.py` - Comprehensive test suite

4. **Verification:**
   - `/home/hermes/pricerecon/verify_argos_musicmagpie_camofox.py` - Live verification script

### Configuration

Both connectors require Camofox for bypassing bot detection:

```yaml
# In watch config or global config
sources:
  - connector: argos
    config:
      camofox_url: "http://192.168.10.252:9377"
      camofox_user_id: "pricerecon-argos"
      camofox_session_key: "watcher"

  - connector: musicmagpie
    config:
      camofox_url: "http://192.168.10.252:9377"
      camofox_user_id: "pricerecon-musicmagpie"
      camofox_session_key: "watcher"
```

### Registry

Both connectors are registered in:
- `pyproject.toml` entry points
- `src/pricerecon/connectors/__init__.py` fallback modules

### DB Seeding

Both connectors seeded to `sources` table with `source_type = 'retailer'`.

### Tests

All tests pass:
- ✓ Source type validation
- ✓ Product card parsing
- ✓ Price extraction
- ✓ Stock detection
- ✓ Deduplication

### Anti-Bot Status

- **Argos**: Akamai protected (requires Camofox)
- **MusicMagpie**: Cloudflare protected (requires Camofox)

Both return Access Denied / "Just a moment..." pages with direct HTTP or local Playwright, but work with Camofox.