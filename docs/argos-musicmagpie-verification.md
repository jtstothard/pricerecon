# Live Verification Script for Argos and MusicMagpie

## Anti-Bot Protection Status

Both sites require Camofox to bypass bot protection:

- **Argos**: Akamai Edge DNS protection
- **MusicMagpie**: Cloudflare "Just a moment..." challenge

## Running Live Verification

Use Camofox to bypass protection:

```bash
cd /home/hermes/pricerecon
source venv/bin/activate
python3 verify_argos_musicmagpie_camofox.py
```

This script:
1. Configures connectors with Camofox at `http://192.168.10.252:9377`
2. Runs a real search for "laptop"
3. Displays sample listings
4. Reports pass/fail status

## Alternative: Run Tests

Deterministic fixture tests (no network required):

```bash
cd /home/hermes/pricerecon
source venv/bin/activate
pytest tests/test_argos_musicmagpie.py -v
```

All tests pass:
- ✓ Source type validation
- ✓ Product card parsing
- ✓ Price extraction
- ✓ Stock detection
- ✓ Deduplication

## Production Usage

Configure in watch YAML:

```yaml
sources:
  - connector: argos
    config:
      camofox_url: "http://192.168.10.252:9377"

  - connector: musicmagpie
    config:
      camofox_url: "http://192.168.10.252:9377"
```

Or set in global `config.yml`:

```yaml
connectors:
  argos:
    enabled: true
    camofox_url: "http://192.168.10.252:9377"
  musicmagpie:
    enabled: true
    camofox_url: "http://192.168.10.252:9377"
```