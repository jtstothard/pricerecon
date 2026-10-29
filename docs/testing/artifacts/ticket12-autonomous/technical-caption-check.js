// Run in preview_evaluate on the owned guarded fixture's Technical product view.
// Before-fix browser readback was #29414f (fails this predicate); rebuilt check passes.
(() => {
  const caption = document.querySelector('.product-view-technical figcaption');
  if (!caption) throw new Error('Open Technical before checking attribution');
  const color = getComputedStyle(caption).color;
  const expected = getComputedStyle(document.documentElement)
    .getPropertyValue('--text-secondary').trim();
  const probe = document.createElement('span');
  probe.style.color = expected;
  document.body.append(probe);
  const resolved = getComputedStyle(probe).color;
  probe.remove();
  if (color !== resolved) throw new Error(`Unreadable attribution: ${color}; expected ${resolved}`);
  return { color, expected: resolved, passed: true };
})()
