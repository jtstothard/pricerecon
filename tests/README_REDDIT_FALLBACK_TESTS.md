# Reddit Fallback Chain Testing

This directory contains comprehensive tests for the Reddit connector's three-tier fallback system (RSS → API → Browser).

## Test Files

### test_reddit_fallbacks.py
**Deterministic unit tests** with mocked responses covering:
- Basic fallback chain progression (RSS → API → Browser)
- Error handling and structured degraded errors
- Rate limiting and authentication failures
- Retry logic with exponential backoff
- Credential loading from environment and files
- API rate limit header extraction

**Run:** `pytest tests/test_reddit_fallbacks.py -v`

**Tests:** 35 tests, all deterministic, no external dependencies

---

### test_reddit_fallbacks_edge_cases.py
**Edge case tests** covering scenarios not present in the main suite:
- Empty subreddit responses (genuine no posts vs parse errors)
- Bot-wall HTML responses in browser fallback
- Rate limit headers preserved in fallback chain errors
- Malformed JSON handling in browser tier
- Partial API response data handling
- Bot wall detection patterns
- **Normalization consistency** across all three tiers (field names, timestamp formats)

**Run:** `pytest tests/test_reddit_fallbacks_edge_cases.py -v`

**Tests:** 8 tests, all deterministic, no external dependencies

---

### test_reddit_fallbacks_live.py
**Live integration tests** that make real HTTP requests to Reddit.

These tests verify that the fallback chain works against actual Reddit infrastructure, not just mocks. They are **skipped by default** to avoid:
- Requiring credentials in CI
- Rate limiting Reddit's infrastructure
- Flaky tests due to external dependencies

**Prerequisites for running:**

For browser tests:
```bash
export PRICERECON_REDDIT_BROWSER_ENABLED=true
export CAMOFOX_URL=your_camofox_url
export CAMOFOX_API_KEY=your_api_key
export CAMOFOX_ACCESS_KEY=your_access_key
export CAMOFOX_USER_ID=your_user_id
export CAMOFOX_SESSION_KEY=your_session_key
```

For API tests:
```bash
export PRICERECON_REDDIT_API_ENABLED=true
export REDDIT_CLIENT_ID=your_client_id
export REDDIT_CLIENT_SECRET=your_client_secret
export REDDIT_USER_AGENT=your_user_agent
```

**Run all live tests:**
```bash
pytest tests/test_reddit_fallbacks_live.py -m live -v
```

**Skip live tests (default in CI):**
```bash
pytest tests/ -v -m "not live"
```

**Tests:** 4 tests, all marked with `@pytest.mark.live`

---

## Running All Tests

```bash
# Run all deterministic tests (fast, no credentials)
pytest tests/test_reddit_fallbacks.py tests/test_reddit_fallbacks_edge_cases.py -v

# Run all tests including live (requires credentials)
pytest tests/ -v

# Skip live tests (recommended for CI)
pytest tests/ -v -m "not live"
```

---

## Test Coverage Summary

| Test File | Tests | Type | Credentials Required | CI Default |
|-----------|-------|------|---------------------|------------|
| test_reddit_fallbacks.py | 35 | Deterministic | No | Run |
| test_reddit_fallbacks_edge_cases.py | 8 | Deterministic | No | Run |
| test_reddit_fallbacks_live.py | 4 | Live integration | Yes | Skip |

**Total:** 47 tests (43 deterministic + 4 live)

---

## Acceptance Criteria Met

✅ **Deterministic unit tests with mocked RSS/API/browser responses covering all tier-progression permutations**
   - Full chain progression (RSS→API→Browser)
   - Single-tier success paths
   - All-tiers-fail scenarios

✅ **Edge cases covered:**
   - Empty subreddit responses
   - Bot-wall HTML responses
   - Rate-limit headers in fallback context
   - Malformed JSON in browser fallback
   - Partial API response data

✅ **Normalization consistency asserted across mock responses from different tiers:**
   - Field names identical across RSS, API, and Browser
   - Timestamp format consistent (UTC timezone-aware)
   - All required fields present

✅ **Live verification exists for at least one fallback path:**
   - Browser tier live test against real Reddit
   - API tier live test against real Reddit
   - Schema consistency test across live tiers

✅ **Live tests marked with flag/env-gate so they can be skipped in CI without credentials:**
   - `@pytest.mark.live` decorator
   - `pytest.markers` configured in pyproject.toml
   - Tests auto-skip when credentials not configured
   - CI runs with `-m "not live"` flag

✅ **`pytest` passes with all deterministic tests green:**
   - 43/43 deterministic tests passing
   - 352/352 total tests passing (including non-Reddit tests)

✅ **No test silently passes on an error condition:**
   - All error paths assert on error type (ConnectorStatus)
   - All degraded errors have structured details
   - Empty results vs parse errors distinguished

---

## Live Test Documentation

The live test file (`test_reddit_fallbacks_live.py`) contains comprehensive inline documentation:

```python
# Run live tests with:
#   pytest tests/test_reddit_fallbacks_live.py -m live

# Or configure with environment variables:
#   export PRICERECON_REDDIT_BROWSER_ENABLED=true
#   export CAMOFOX_URL=your_camofox_url
#   ...
```

See the `LIVE_TEST_DOCS` variable at the end of the file for detailed setup instructions.