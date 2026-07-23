# Reddit acquisition fallback

`RedditHardwareSwapUKConnector` and `RedditBapcSalesUKConnector` use this order:

1. subreddit RSS (cheap, anonymous attempt);
2. official Reddit OAuth API, only when explicitly enabled;
3. browser acquisition through Camofox or local Playwright, only when enabled.

A 403 (`bot_blocked`) or 429 (`rate_limited`) from RSS is never treated as an empty successful search. If no fallback is configured, or all configured fallbacks fail, the connector raises the structured degraded error with the original RSS status and fallback details.

## Official API prerequisites

Create an approved Reddit application and provide all of these environment variables to the worker:

```text
PRICERECON_REDDIT_API_ENABLED=true
REDDIT_CLIENT_ID=...
REDDIT_CLIENT_SECRET=...
REDDIT_USER_AGENT=PriceRecon/1.0 by /u/your-reddit-account
```

The connector uses the OAuth client-credentials flow. Reddit approval, valid credentials, and compliance with Reddit API terms are human-gated prerequisites; the application does not attempt to register or approve an app automatically.

## Browser prerequisites

For remote Camofox:

```text
CAMOFOX_URL=http://camofox:9376
# Optional: CAMOFOX_API_KEY, CAMOFOX_USER_ID, CAMOFOX_SESSION_KEY
```

For local Playwright, explicitly opt in and install the browser runtime in the deployment image:

```text
PRICERECON_REDDIT_BROWSER_ENABLED=true
playwright install chromium
```

Browser acquisition is intended for blocked public pages and may still require a human to solve a CAPTCHA or sign-in challenge. Such pages remain `bot_blocked`; they are not returned as zero results.
