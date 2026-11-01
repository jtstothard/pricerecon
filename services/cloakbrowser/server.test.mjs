import assert from 'node:assert/strict';
import test from 'node:test';
import { _render } from './server.mjs';

test('ordinary browser sessions return usable page evidence', async () => {
  const page = {
    setDefaultNavigationTimeout() {},
    on() {},
    async goto() { return { status: () => 200 }; },
    async waitForTimeout() {},
    async title() { return 'Control product'; },
    url() { return 'https://example.test/final'; },
    async content() { return '<html><body>Control product £42</body></html>'; },
  };
  const result = await _render({ newPage: async () => page }, 'https://example.test/', undefined, 0);
  assert.match(result.html, /Control product £42/);
  assert.equal(result.finalUrl, 'https://example.test/final');
  assert.equal(result.mainStatus, 200);
});


test('large pages disclose truncation instead of implying complete content', async () => {
  const page = {
    setDefaultNavigationTimeout() {}, on() {},
    async goto() { return { status: () => 403 }; },
    async waitForTimeout() {}, async title() { return 'Denied'; },
    url() { return 'https://example.test/denied?token=private'; },
    async content() { return 'x'.repeat(300000); },
  };
  const result = await _render({ newPage: async () => page }, 'https://example.test/', undefined, 0);
  assert.equal(result.html.length, 262144);
  assert.equal(result.htmlTruncated, true);
  assert.equal(result.mainStatus, 403);
  assert.equal(result.finalUrl, 'https://example.test/denied');
  assert.equal(result.networkInterceptionSupported, false);
});
