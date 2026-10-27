# PriceRecon CloakBrowser wrapper

`server.mjs` retains and fixes the existing deployed wrapper; this is not a second browser service. Its runtime remains the existing CloakBrowser image, with its installed package, lockfile and browser binary. No new browser dependency was added to PriceRecon.

Run the wrapper contract tests without browser downloads:

```sh
node --test services/cloakbrowser/server.test.mjs
```

Normal sessions return bounded rendered HTML (262,144 JavaScript string units maximum), `htmlTruncated`, a final URL with credentials/query removed, and `mainStatus`. This wrapper does not claim passive network interception. PriceRecon independently bounds content to its caller's requested limit and rejects title-only responses and blocked-document statuses.

The normal endpoint creates a fresh context per call and closes the browser afterward. It does not provide persistent profiles. The existing authenticated Reddit extraction endpoint remains separate and does not return storage state. HTTP health reports active sessions without exposing account data.

For Camofox, PriceRecon supplies a stable anonymous context identity per connector/backend/merchant origin. A directly constructed adapter without a connector scope gets a private random scope. Explicitly configured `user_id`/`session_key` account profiles are preserved; operators must assign such profiles to their intended connector and merchant instead of reusing an account context as a global default. `sessionKey` alone is a tab group, not a cookie-isolation boundary.

Deployment source, image identities, test results and limits are recorded in [the deployment receipt](../../docs/product/category-discovery/browser-fix-deployment.md). No global browser default or existing account routing was enabled by this fix.

AliExpress inspection can opt into `options.render_mode: dom` and an optional CSS `options.ready_selector`. DOM mode removes scripts, media and presentation attributes, serializes current form selections, and clears unrelated input values and textarea content. It keeps the same size limit and reports truncation; it is not a general secret scrubber or permission to archive pages. The live AliExpress search still exceeded the limit in this mode, so it is not a qualified discovery route.

`dom.integration.mjs` exercises the real installed browser against a controlled intercepted document. Run it inside the existing browser image with networking disabled, set `CLOAKBROWSER_EXECUTABLE` to that image's installed Chromium path, and mount the script beside `server.mjs`. It requires the image's existing Playwright package and never downloads a browser.
