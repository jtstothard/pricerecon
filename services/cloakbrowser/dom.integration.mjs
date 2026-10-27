import assert from 'node:assert/strict';
import { chromium } from 'playwright';
import { _render } from './server.mjs';
// Use an already installed browser; this test never downloads binaries.
const executablePath = process.env.CLOAKBROWSER_EXECUTABLE;
assert.ok(executablePath, 'Set CLOAKBROWSER_EXECUTABLE to the installed browser');
const browser=await chromium.launch({headless:true,executablePath,args:['--no-sandbox']});
try {
 const ctx=await browser.newContext();
 await ctx.route('**/*',route=>route.fulfill({contentType:'text/html',body:`<h1 data-state="private-state" style="private-style">Controlled offer</h1><input name="password" value="private-password"><input name="csrf" value="private-token"><input name="skuId" value="1001"><input name="quantity" value="1"><input type="radio" name="movement" value="2035" checked><input type="radio" name="movement" value="VH31"><select name="dial"><option>Red</option><option>Blue</option></select><textarea>private-note</textarea><script>document.querySelector('input[value="VH31"]').checked=true;document.querySelector('select').selectedIndex=1;window.privateState='private-script';</script>`}));
 const r=await _render(ctx,'https://fixture.test/',undefined,0,'dom','h1');
 assert.equal(r.mainStatus,200);assert.equal(r.htmlTruncated,false);
 for(const value of ['private-password','private-token','private-note','private-script','private-state','private-style','<script'])assert.ok(!r.html.includes(value));
 assert.match(r.html, /name="skuId" value="1001"/);
 assert.match(r.html, /value="VH31" checked=""/);
 assert.ok(!/value="2035" checked/.test(r.html));
 assert.match(r.html, /option selected="">Blue/);
 console.log(JSON.stringify({native_dom_fixture:'passed',redaction:'passed',live_control_state:'passed',external_requests:0}));
}finally{await browser.close()}
