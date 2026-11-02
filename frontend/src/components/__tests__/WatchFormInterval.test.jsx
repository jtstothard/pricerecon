import { createRequire } from 'node:module'
import React, { act } from 'react'
import { createRoot } from 'react-dom/client'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import WatchForm from '../WatchForm'
// Can use an existing local DOM installation in offline environments.
const { JSDOM } = createRequire(import.meta.url)(process.env.WATCH_DOM_MODULE || 'jsdom')

// Regression seam for D-8: a watch whose saved interval is a custom value
// (not one of the presets) must stay restorable in the open edit form.
const savedWatch = {
  id: 7,
  name: 'Saved wristwatch search',
  query: 'militado ml05',
  category: null,
  display_title: null,
  enabled: true,
  last_check_at: null,
  sources: [{ connector: 'ebay', enabled: true }],
  schedule: { interval: '30m', timezone: 'Europe/London' },
}

let root, container, dom, fetchMock

beforeEach(() => {
  dom = new JSDOM('<div id="root"></div>', { url: 'http://localhost/watches' })
  vi.stubGlobal('window', dom.window)
  vi.stubGlobal('document', dom.window.document)
  vi.stubGlobal('IS_REACT_ACT_ENVIRONMENT', true)
  fetchMock = vi.fn(async (url) =>
    url === '/api/sources'
      ? { ok: true, json: async () => [] }
      : { ok: true, json: async () => savedWatch }
  )
  vi.stubGlobal('fetch', fetchMock)
  container = document.getElementById('root')
  root = createRoot(container)
})

afterEach(async () => {
  await act(async () => root.unmount())
  dom.window.close()
  vi.unstubAllGlobals()
})

async function mount(element) {
  await act(async () => {
    root.render(element)
  })
}

async function changeSelect(select, value) {
  await act(async () => {
    Object.getOwnPropertyDescriptor(dom.window.HTMLSelectElement.prototype, 'value').set.call(select, value)
    select.dispatchEvent(new dom.window.Event('change', { bubbles: true }))
  })
}

it('keeps a saved custom interval selectable after changing away and resubmits it', async () => {
  await mount(<WatchForm open editingWatch={savedWatch} onClose={() => {}} onSaved={() => {}} />)
  const select = container.querySelector('#interval')
  // Load shows the saved custom value as its own selected option.
  expect(select.value).toBe('30m')
  expect(select.querySelector('option[value="30m"]').textContent).toBe('Every 30m (saved)')

  // Change to a preset interval.
  await changeSelect(select, '4h')
  expect(select.value).toBe('4h')

  // The saved custom value must remain offered while the form is open.
  const savedOption = select.querySelector('option[value="30m"]')
  expect(savedOption).not.toBeNull()
  expect(savedOption.textContent).toBe('Every 30m (saved)')

  // Selecting it again must drive the real select state back to the saved value.
  await changeSelect(select, '30m')
  expect(select.value).toBe('30m')

  // The submitted payload carries the restored interval.
  await act(async () => {
    container
      .querySelector('form')
      .dispatchEvent(new dom.window.Event('submit', { bubbles: true, cancelable: true }))
  })
  const put = fetchMock.mock.calls.find(([url]) => url === '/api/watches/7')
  expect(put).toBeDefined()
  expect(JSON.parse(put[1].body).schedule.interval).toBe('30m')
})
