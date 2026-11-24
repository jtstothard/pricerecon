// React 19 removed `Simulate` from react-dom/test-utils. This keeps the one
// call shape these tests use, Simulate.change(element, { target: { value } }),
// by going through the DOM the way a browser does: set the value with the
// element's native setter (so React's value tracker sees a real change) and
// dispatch bubbling `input` and `change` events for React's root listener.
//
// Test files using it need `// @vitest-environment jsdom`: react-dom decides
// at import time whether the `input` event exists, and under the default node
// environment it falls back to an old-IE polyfill that ignores native `input`
// events, so text-input changes would never reach onChange.
function changeValue(element, value) {
  if (!element) throw new Error('Simulate.change: element not found')
  const descriptor = Object.getOwnPropertyDescriptor(Object.getPrototypeOf(element), 'value')
  descriptor.set.call(element, value)
  const { Event } = element.ownerDocument.defaultView
  element.dispatchEvent(new Event('input', { bubbles: true }))
  element.dispatchEvent(new Event('change', { bubbles: true }))
}

export const Simulate = {
  change(element, eventData = {}) {
    changeValue(element, eventData.target?.value ?? element.value)
  },
}
