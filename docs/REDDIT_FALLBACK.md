# Reddit acquisition fallback

`RedditHardwareSwapUKConnector` and `RedditBapcSalesUKConnector` use this order:

1. subreddit RSS (cheap, anonymous attempt);
2. official Reddit OAuth API, only when explicitly enabled and approved;
3. an authenticated, persistent Camofox profile selected for that Reddit connector.

A 403 (`bot_blocked`) or 429 (`rate_limited`) from RSS is never treated as an empty successful search. If no eligible fallback is configured, or all eligible fallbacks fail, the connector raises the structured degraded error with the original RSS status and fallback details.

## Official API prerequisites

Create an approved Reddit application and provide all of these environment variables to the worker:

```text
PRICERECON_REDDIT_API_ENABLED=true
REDDIT_CLIENT_ID=...
REDDIT_CLIENT_SECRET=...
REDDIT_USER_AGENT=PriceRecon/1.0 by /u/your-reddit-account
```

The connector uses the OAuth client-credentials flow. Reddit approval, valid credentials, and compliance with Reddit API terms are human-gated prerequisites; the application does not attempt to register or approve an app automatically.

## Authenticated Camofox prerequisites

Configure a Camofox backend specifically for Reddit with a persistent, user-scoped profile and session identifier:

```yaml
browser_backends:
  reddit_camofox:
    type: camofox
    endpoint: ${CAMOFOX_URL}
    options:
      user_id: ${PRICERECON_REDDIT_CAMOFOX_USER_ID}
      session_key: ${PRICERECON_REDDIT_CAMOFOX_SESSION_KEY}
connectors:
  reddit_hardwareswapuk:
    browser_backend: reddit_camofox
  reddit_buildapcsalesuk:
    browser_backend: reddit_camofox
```

Alternatively, set `CAMOFOX_URL` (or `PRICERECON_CAMOFOX_URL`) with both
`PRICERECON_REDDIT_CAMOFOX_USER_ID` and
`PRICERECON_REDDIT_CAMOFOX_SESSION_KEY`. An API/access key belongs in the
Camofox backend options when the service requires it.

Establish and maintain the profile session through the approved, human-gated Camofox workflow. PriceRecon does not automate sign-in, export cookies, solve CAPTCHAs, or bypass Reddit policy controls.

If the profile identifiers are missing, or the profile session is expired, the Reddit browser tier fails closed. It never falls back to an anonymous Camofox session or local Playwright. CAPTCHA or bot-wall pages remain `bot_blocked`; they are not returned as zero results.
