import http from 'node:http';
import { pathToFileURL } from 'node:url';

async function cloakLaunch(options) {
  const { launch } = await import('cloakbrowser');
  return launch(options);
}

const HOST = process.env.HOST || '0.0.0.0';
const PORT = Number(process.env.PORT || 9378);
const NAV_TIMEOUT = Number(process.env.NAV_TIMEOUT_MS || 60000);
// storageState payloads (cookies + localStorage for one or more origins) are
// larger than a plain URL request. Allow up to ~1 MB but cap to avoid abuse.
const MAX_BODY = 1_000_000;
const MAX_HTML = 262_144;
const REDACTED = '[redacted]';
const SECRET_KEY = /cookie|authorization|token|secret|password|session|api[-_]?key/i;
const SECRET_VALUE = /(Bearer\s+|Basic\s+)[A-Za-z0-9._~+/=-]+/gi;
let activeSessions = 0;

function json(res, status, body) {
  const data = JSON.stringify(body);
  res.writeHead(status, { 'content-type': 'application/json; charset=utf-8', 'cache-control': 'no-store' });
  res.end(data);
}
function redactHeaders(headers) {
  const blocked = /cookie|authorization|token|akamai|set-cookie|proxy-authorization/i;
  return Object.fromEntries(Object.entries(headers || {}).filter(([k]) => !blocked.test(k)).map(([k, v]) => [k, String(v).slice(0, 300)]));
}
// Redaction used for any structured result body that could carry secrets.
function safeText(value, limit = 500) {
  return String(value ?? '').replace(SECRET_VALUE, REDACTED).slice(0, limit);
}
function safeUrl(value) {
  try {
    const u = new URL(String(value));
    if (u.protocol !== 'http:' && u.protocol !== 'https:') return '';
    u.username = ''; u.password = ''; u.search = '';
    return u.toString();
  } catch { return ''; }
}
function redactStructured(value, depth = 0) {
  if (depth > 6) return REDACTED;
  if (Array.isArray(value)) return value.slice(0, 50).map((v) => redactStructured(v, depth + 1));
  if (value && typeof value === 'object') {
    return Object.fromEntries(
      Object.entries(value).slice(0, 50).map(([k, v]) => [
        k,
        SECRET_KEY.test(k) ? REDACTED : redactStructured(v, depth + 1),
      ]),
    );
  }
  return safeText(value);
}

// Validate the Playwright storageState contract WITHOUT logging it.
// Mirrors the field checks in PriceRecon's _validate_playwright_storage_state.
function validateStorageState(state) {
  if (state === undefined || state === null) return undefined; // optional -> unauthenticated
  if (typeof state !== 'object' || Array.isArray(state)) {
    throw new Error('storageState must be an object');
  }
  const cookies = state.cookies;
  const origins = state.origins;
  if (cookies !== undefined && !Array.isArray(cookies)) {
    throw new Error('storageState.cookies must be an array');
  }
  if (origins !== undefined && !Array.isArray(origins)) {
    throw new Error('storageState.origins must be an array');
  }
  for (const cookie of cookies || []) {
    if (!cookie || typeof cookie !== 'object') throw new Error('storageState contains a malformed cookie');
    for (const field of ['name', 'value', 'domain', 'path']) {
      if (typeof cookie[field] !== 'string') throw new Error('storageState contains a malformed cookie');
    }
  }
  for (const origin of origins || []) {
    if (!origin || typeof origin !== 'object' || typeof origin.origin !== 'string') {
      throw new Error('storageState contains a malformed origin');
    }
    const local = origin.localStorage;
    if (local !== undefined && !Array.isArray(local)) {
      throw new Error('storageState origin localStorage must be an array');
    }
    for (const entry of local || []) {
      if (!entry || typeof entry.name !== 'string' || typeof entry.value !== 'string') {
        throw new Error('storageState contains malformed localStorage');
      }
    }
  }
  return state;
}

async function readBody(req) {
  let data = '';
  for await (const chunk of req) {
    data += chunk;
    if (data.length > MAX_BODY) throw new Error('request too large');
  }
  return data ? JSON.parse(data) : {};
}

// Unauthenticated session (existing behavior, unchanged contract).
async function runSession({ url, apiUrl, waitMs = 3000, renderMode = 'html', readySelector }) {
  if (typeof url !== 'string' || !/^https:\/\//i.test(url)) throw new Error('url must be an https URL');
  activeSessions++;
  const browser = await cloakLaunch({ headless: true });
  try {
    const context = await browser.newContext();
    return await _render(context, url, apiUrl, waitMs, renderMode, readySelector);
  } finally {
    await browser.close();
    activeSessions--;
  }
}

// Authenticated session: optional Playwright storageState is injected into the
// context in memory. The state is never logged, persisted, or returned.
// When `storageState` is absent/null, behavior is identical to runSession.
async function runAuthenticatedSession({ url, apiUrl, waitMs = 3000, storageState, redditStructured = false }) {
  if (typeof url !== 'string' || !/^https:\/\//i.test(url)) throw new Error('url must be an https URL');
  const state = validateStorageState(storageState);
  activeSessions++;
  const browser = await cloakLaunch({ headless: true });
  try {
    const context = state
      ? await browser.newContext({ storageState: state })
      : await browser.newContext();
    if (redditStructured) {
      return await _renderReddit(context, url, waitMs);
    }
    return await _render(context, url, apiUrl, waitMs);
  } finally {
    await browser.close();
    activeSessions--;
  }
}

// Shared render path for /api/browser/session (unchanged contract).
export async function _render(context, url, apiUrl, waitMs, renderMode = 'html', readySelector) {
  if (!['html', 'dom'].includes(renderMode)) throw new Error('unsupported render mode');
  if (readySelector !== undefined && (typeof readySelector !== 'string' || readySelector.length > 200)) {
    throw new Error('invalid ready selector');
  }
  const page = await context.newPage();
  page.setDefaultNavigationTimeout(NAV_TIMEOUT);
  const responseLog = [];
  page.on('response', response => {
    const u = response.url();
    if (/sproducts/i.test(u)) responseLog.push({ url: u.split('?')[0], status: response.status(), headers: redactHeaders(response.headers()) });
  });
  const main = await page.goto(url, { waitUntil: 'domcontentloaded' });
  if (readySelector) {
    await page.locator(readySelector).first().waitFor({ state: 'attached', timeout: Math.min(NAV_TIMEOUT, 10000) });
  }
  await page.waitForTimeout(Number(waitMs));
  const title = await page.title();
  const html = renderMode === 'dom' ? await page.locator('body').evaluate(body => {
    const clone = body.cloneNode(true);
    // Do not serialize account, password or hidden anti-CSRF values. Preserve
    // only a numeric SKU input and current public radio/checkbox selection.
    const original = [...body.querySelectorAll('input')];
    const copies = [...clone.querySelectorAll('input')];
    copies.forEach((copy, i) => {
      const input = original[i];
      copy.removeAttribute('value');
      if (input && /^(skuId|sku_id|quantity)$/i.test(input.name) && /^\d+$/.test(input.value)) {
        copy.setAttribute('value', input.value);
      }
      if (input?.type === 'radio' && /^(movement|color|colour|dial|strap|band|size)$/i.test(input.name) && input.value.length <= 100) copy.setAttribute('value', input.value);
      if (input?.checked && ['radio', 'checkbox'].includes(input.type)) copy.setAttribute('checked', '');
      else copy.removeAttribute('checked');
    });
    const originalOptions = [...body.querySelectorAll('option')];
    clone.querySelectorAll('option').forEach((copy, i) => {
      if (originalOptions[i]?.selected) copy.setAttribute('selected', '');
      else copy.removeAttribute('selected');
    });
    clone.querySelectorAll('script,style,noscript,template,svg,canvas,img,picture,video,audio,source,iframe,link').forEach(e => e.remove());
    // Hydration blobs and presentation attributes can dwarf the public evidence.
    // Preserve only attributes used by the offer/link parser and current controls.
    const allowed = new Set(['href', 'name', 'type', 'value', 'checked', 'selected', 'data-sku-id', 'data-current-price']);
    clone.querySelectorAll('*').forEach(element => {
      for (const attribute of [...element.attributes]) {
        if (attribute.name === 'class') {
          const relevant = attribute.value.split(/\s+/).filter(v => /^(sku-item--(?:property|selected)|price--currentPriceText)/.test(v));
          if (relevant.length) element.setAttribute('class', relevant.join(' '));
          else element.removeAttribute('class');
        } else if (!allowed.has(attribute.name)) element.removeAttribute(attribute.name);
      }
    });
    clone.querySelectorAll('textarea').forEach(e => { e.textContent = ''; });
    return '<html><body>' + clone.innerHTML + '</body></html>';
  }) : await page.content();
  const result = {
    navigated: true, title,
    finalUrl: safeUrl(page.url()),
    mainStatus: main?.status() ?? null,
    html: html.slice(0, MAX_HTML),
    htmlTruncated: html.length > MAX_HTML,
    networkInterceptionSupported: false,
    sproductsResponses: responseLog,
  };
  if (apiUrl) {
    if (typeof apiUrl !== 'string' || !/^https:\/\//i.test(apiUrl)) throw new Error('apiUrl must be an https URL');
    const api = await page.evaluate(async target => {
      const r = await fetch(target, { credentials: 'include' });
      const text = await r.text();
      let body; try { body = JSON.parse(text); } catch { body = { text: text.slice(0, 2000) }; }
      return { status: r.status, contentType: r.headers.get('content-type'), body };
    }, apiUrl);
    result.api = api;
    result.apiUrl = apiUrl.split('?')[0];
  }
  return result;
}

// Reddit feature-path structured extraction. Returns a bounded, redacted,
// authenticated-aware result. Never returns cookies/headers/bodies.
async function _renderReddit(context, url, waitMs) {
  const page = await context.newPage();
  page.setDefaultNavigationTimeout(NAV_TIMEOUT);
  await page.goto(url, { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(Number(waitMs));
  const title = await page.title();
  const authenticated = await page.locator('body').evaluate((body) => {
    const text = body?.innerText || '';
    return !/log\s*in\s*to\s*reddit|sign\s*in\s*to\s*reddit|session\s+has\s+expired/i.test(text);
  });
  const items = await page.locator('a[href*="/comments/"]').evaluateAll((anchors) => {
    const seen = new Set();
    const out = [];
    for (const anchor of anchors) {
      const href = anchor.href || '';
      if (!href || !/reddit\.com\/r\/[^/]+\/comments\//i.test(href) || seen.has(href)) continue;
      seen.add(href);
      const t = (anchor.textContent || '').replace(/\s+/g, ' ').trim();
      if (t) out.push({ title: t, url: href });
    }
    return out.slice(0, 50);
  });
  return {
    navigated: true,
    ok: true,
    authenticated: Boolean(authenticated),
    title: safeText(title, 200),
    mainStatus: 200,
    items: items.map((item) => ({ title: safeText(item.title), url: safeUrl(item.url) })),
  };
}

const server = http.createServer(async (req, res) => {
  try {
    if (req.method === 'GET' && req.url === '/health') return json(res, 200, { ok: true, service: 'cloakbrowser', browser: 'cloakbrowser', activeSessions });
    if (req.method === 'GET' && req.url === '/api/health') return json(res, 200, { ok: true, service: 'cloakbrowser', activeSessions });
    if (req.method === 'GET' && req.url === '/api/storage-state') {
      // Capability advertisement. Never reflects stored state.
      return json(res, 200, { ok: true, storageStateSupported: true });
    }
    if (req.method === 'POST' && (req.url === '/api/browser/session' || req.url === '/api/browser/probe')) {
      const body = await readBody(req);
      const result = await runSession(body);
      return json(res, 200, result);
    }
    if (req.method === 'POST' && (req.url === '/api/browser/authenticated-session' || req.url === '/api/browser/authenticated-probe')) {
      const body = await readBody(req);
      // storageState is intentionally not logged on any path.
      const result = await runAuthenticatedSession(body);
      return json(res, 200, result);
    }
    return json(res, 404, { error: 'not found' });
  } catch (err) {
    // Never log request bodies or cookies. Only a short, redacted message.
    console.error(`[request-error] ${String(err?.message || err).replace(/[\r\n]/g, ' ').slice(0, 500)}`);
    return json(res, 400, { error: String(err?.message || err).slice(0, 300) });
  }
});
if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  server.listen(PORT, HOST, () => console.log(`[cloakbrowser] listening on ${HOST}:${PORT}`));
  process.on('SIGTERM', () => server.close(() => process.exit(0)));
}
