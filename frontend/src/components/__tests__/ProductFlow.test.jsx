import { createRequire } from 'node:module'
import React, { act } from 'react'
import { Simulate } from 'react-dom/test-utils'
import { createRoot } from 'react-dom/client'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import Discovery, { ProductDetail } from '../../pages/Discovery'
import { ChoiceValue } from '../discovery/ChoiceValue'
import { IdentityCorrection } from '../discovery/IdentityCorrection'
import ExactTrackingControl from '../ExactTracking'
import { parseDiscoveryFeed } from '../../lib/discovery'
import captured from './image-feed.json'
// Can use an existing local DOM installation in offline environments.
const { JSDOM } = createRequire(import.meta.url)(process.env.WATCH_DOM_MODULE || 'jsdom')
let root, container, dom
beforeEach(() => {
  dom = new JSDOM('<div id="root"></div>', { url: 'http://localhost/discover' })
  vi.stubGlobal('window', dom.window)
  vi.stubGlobal('document', dom.window.document)
  vi.stubGlobal('IS_REACT_ACT_ENVIRONMENT', true)
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
async function change(element, value) {
  await act(async () => {
    const prototype =
      element.tagName === 'SELECT'
        ? dom.window.HTMLSelectElement.prototype
        : dom.window.HTMLInputElement.prototype
    Object.getOwnPropertyDescriptor(prototype, 'value').set.call(element, value)
    element.dispatchEvent(
      new dom.window.Event(element.tagName === 'SELECT' ? 'change' : 'input', { bubbles: true })
    )
  })
}
const candidate = () => ({
  ...parseDiscoveryFeed(captured).candidates[0],
  configurations: [
    {
      id: 'watch',
      revision: 1,
      state: 'supported',
      values: { dial: 'Blue', movement: 'Quartz' },
      evidence_ids: [],
      issues: [],
      policy_version: 'fixture',
    },
  ],
})
it('loads a directly addressed product from the API and selects flat technical navigation', async () => {
  const c = candidate()
  const body = { ...captured, candidates: [{ ...captured.candidates[0], id: c.id }] }
  const fetch = vi.fn().mockResolvedValue({ ok: true, json: async () => body })
  vi.stubGlobal('fetch', fetch)
  await mount(
    <MemoryRouter initialEntries={[`/discover/product/${c.id}?view=technical`]}>
      <Routes>
        <Route path="/discover/product/:id" element={<ProductDetail />} />
      </Routes>
    </MemoryRouter>
  )
  expect(fetch.mock.calls[0][0]).toBe('/api/discovery/watches')
  expect(container.querySelector('[aria-current="page"]').textContent).toBe('Technical')
  expect(container.textContent).toContain('Complete retained record')
  expect(container.querySelector('details')).toBeNull()
  const overview = Array.from(container.querySelectorAll('nav a')).find(
    (a) => a.textContent === 'Overview'
  )
  await act(async () =>
    overview.dispatchEvent(
      new dom.window.MouseEvent('click', { bubbles: true, cancelable: true, button: 0 })
    )
  )
  expect(container.querySelector('[aria-current="page"]').textContent).toBe('Overview')
  expect(container.textContent).toContain('Watch specifications')
  expect(container.textContent).not.toContain('Complete retained record')
})
it('reports missing products and API rejection without selecting another watch', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => captured }))
  await mount(
    <MemoryRouter initialEntries={['/discover/product/missing']}>
      <Routes>
        <Route path="/discover/product/:id" element={<ProductDetail />} />
      </Routes>
    </MemoryRouter>
  )
  expect(container.querySelector('[role="alert"]').textContent).toContain('Watch not found')
})
it('keeps preset and arbitrary custom values editable', async () => {
  let saved = ''
  function Harness() {
    const [value, setValue] = React.useState('137.25')
    return (
      <ChoiceValue
        label="Target"
        value={value}
        choices={['100', '150']}
        onChange={(v) => {
          saved = v
          setValue(v)
        }}
      />
    )
  }
  await mount(<Harness />)
  expect(container.querySelector('input').value).toBe('137.25')
  await change(container.querySelector('select'), '150')
  expect(saved).toBe('150')
  expect(container.querySelector('input')).toBeNull()
  await change(container.querySelector('select'), '__custom')
  expect(container.querySelector('input').value).toBe('150')
  await act(async () =>
    Simulate.change(container.querySelector('input'), { target: { value: '143.72' } })
  )
  expect(saved).toBe('143.72')
})
it('submits an explicit correction reason and actor and exposes rejection', async () => {
  const fetch = vi
    .fn()
    .mockResolvedValue({
      ok: false,
      status: 409,
      json: async () => ({ detail: 'Identity changed. Reload before saving.' }),
    })
  vi.stubGlobal('fetch', fetch)
  await mount(<IdentityCorrection candidate={candidate()} onSaved={async () => {}} />)
  await change(container.querySelector('[aria-label="Correct value"]'), 'Green')
  await change(container.querySelector('[name="correction_state"]'), 'disputed')
  await change(
    container.querySelector('[aria-label="Reason"]'),
    'The recorded specification is incorrect.'
  )
  const actor = container.querySelector('[name="correction_actor"]')
  await act(async () => Simulate.change(actor, { target: { value: 'Buyer' } }))
  await act(async () =>
    container
      .querySelector('form')
      .dispatchEvent(new dom.window.Event('submit', { bubbles: true, cancelable: true }))
  )
  expect(container.querySelector('[role="alert"]').textContent).toContain('Reload')
  const payload = JSON.parse(fetch.mock.calls[0][1].body)
  expect(payload.value).toBe('Green')
  expect(payload.rationale).toBe('The recorded specification is incorrect.')
  expect(payload.actor).toBe('Buyer')
  expect(payload.state).toBe('disputed')
})
it('saves a selected delivered-target preset through the existing API and shows rejection', async () => {
  const fetch = vi
    .fn()
    .mockResolvedValue({
      ok: false,
      status: 409,
      json: async () => ({ detail: 'Identity changed. Reload before saving.' }),
    })
  vi.stubGlobal('fetch', fetch)
  const c = candidate()
  await mount(
    <ExactTrackingControl
      candidate={c}
      configuration={c.configurations[0]}
      onSaved={async () => {}}
    />
  )
  await change(container.querySelector('[aria-label="UK delivered target (£)"]'), '150')
  await act(async () =>
    container
      .querySelector('form')
      .dispatchEvent(new dom.window.Event('submit', { bubbles: true, cancelable: true }))
  )
  expect(JSON.parse(fetch.mock.calls[0][1].body).target_gbp).toBe('150')
  expect(container.querySelector('[role="alert"]')).not.toBeNull()
  expect(container.querySelector('details')).toBeNull()
})

it('loads API failures visibly on the direct product route', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false }))
  await mount(
    <MemoryRouter initialEntries={['/discover/product/missing']}>
      <Routes>
        <Route path="/discover/product/:id" element={<ProductDetail />} />
      </Routes>
    </MemoryRouter>
  )
  expect(container.querySelector('[role="alert"]').textContent).toContain(
    'Discovery could not load'
  )
})
it('edits custom preference values and preserves the existing preference API revision', async () => {
  const fetch = vi
    .fn()
    .mockResolvedValueOnce({ ok: true, json: async () => captured })
    .mockResolvedValue({ ok: false, status: 409 })
  vi.stubGlobal('fetch', fetch)
  await mount(
    <MemoryRouter initialEntries={['/discover?view=preferences']}>
      <Discovery />
    </MemoryRouter>
  )
  await change(container.querySelector('[aria-label="Public UK delivered budget (£)"]'), '__custom')
  await act(async () =>
    Simulate.change(
      container.querySelector('[aria-label="Public UK delivered budget (£) custom value"]'),
      { target: { value: '172.35' } }
    )
  )
  await change(container.querySelector('[aria-label="Maximum case width (mm)"]'), '38')
  await act(async () =>
    container
      .querySelector('form')
      .dispatchEvent(new dom.window.Event('submit', { bubbles: true, cancelable: true }))
  )
  expect(fetch.mock.calls[1][0]).toBe('/api/discovery/watches/preferences')
  expect(JSON.parse(fetch.mock.calls[1][1].body).values).toMatchObject({
    budget_gbp: '172.35',
    compact_max_width_mm: '38',
  })
  expect(container.querySelector('[role="alert"]').textContent).toContain('another window')
})
it('submits custom correction values and buyer-written rationale unchanged', async () => {
  const fetch = vi.fn().mockResolvedValue({ ok: false, status: 400 })
  vi.stubGlobal('fetch', fetch)
  await mount(<IdentityCorrection candidate={candidate()} onSaved={async () => {}} />)
  for (const [label, value] of [
    ['Correct value', 'Lilac / teal'],
    ['Reason', 'I checked the selected dial variant.'],
  ]) {
    await change(container.querySelector(`[aria-label="${label}"]`), '__custom')
    await act(async () =>
      Simulate.change(container.querySelector(`[aria-label="${label} custom value"]`), {
        target: { value },
      })
    )
  }
  await act(async () =>
    Simulate.change(container.querySelector('[name="correction_actor"]'), {
      target: { value: 'Jay' },
    })
  )
  await act(async () =>
    container
      .querySelector('form')
      .dispatchEvent(new dom.window.Event('submit', { bubbles: true, cancelable: true }))
  )
  expect(JSON.parse(fetch.mock.calls[0][1].body)).toMatchObject({
    value: 'Lilac / teal',
    rationale: 'I checked the selected dial variant.',
    actor: 'Jay',
  })
  expect(container.querySelector('[role="alert"]').textContent).toContain(
    'Correction was not saved'
  )
})

it('writes a custom target without rounding or substituting a preset', async () => {
  const fetch = vi.fn().mockResolvedValue({ ok: false, status: 400 })
  vi.stubGlobal('fetch', fetch)
  const c = candidate()
  await mount(
    <ExactTrackingControl
      candidate={c}
      configuration={c.configurations[0]}
      onSaved={async () => {}}
    />
  )
  await change(container.querySelector('[aria-label="UK delivered target (£)"]'), '__custom')
  await act(async () =>
    Simulate.change(container.querySelector('[name="target_gbp"]'), { target: { value: '143.72' } })
  )
  await act(async () =>
    container
      .querySelector('form')
      .dispatchEvent(new dom.window.Event('submit', { bubbles: true, cancelable: true }))
  )
  expect(JSON.parse(fetch.mock.calls[0][1].body).target_gbp).toBe('143.72')
  expect(container.querySelector('[role="alert"]')).not.toBeNull()
})

it('shows an arbitrary externally revised value instead of a blank preset', async () => {
  await mount(<ChoiceValue label="Target" value="150" choices={['100', '150']} onChange={() => {}} />)
  await mount(<ChoiceValue label="Target" value="157.65" choices={['100', '150']} onChange={() => {}} />)
  expect(container.querySelector('select').value).toBe('__custom')
  expect(container.querySelector('input').value).toBe('157.65')
})

it('puts the watch and buying action before flat detail navigation and keeps attribution in Technical', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => captured }))
  const id = captured.candidates[0].id
  await mount(<MemoryRouter initialEntries={[`/discover/product/${id}`]}><Routes><Route path="/discover/product/:id" element={<ProductDetail />} /></Routes></MemoryRouter>)
  const brief = container.querySelector('[aria-label="Watch buying summary"]')
  expect(brief).not.toBeNull()
  expect(brief.compareDocumentPosition(container.querySelector('nav')) & dom.window.Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
  expect(brief.querySelector('h1').textContent).toBe(captured.candidates[0].title)
  const track = Array.from(brief.querySelectorAll('a')).find(a => /Track this watch|Edit delivered target/.test(a.textContent))
  expect(track.getAttribute('href')).toContain('view=tracking')
  expect(brief.textContent).toContain('Condition')
  expect(container.querySelectorAll('figure')).toHaveLength(1)
  expect(container.querySelector('.product-content h2').textContent).toBe('Watch specifications')
  expect(container.querySelector('details')).toBeNull()
  await act(async () => container.querySelector('nav a[href*="technical"]').dispatchEvent(new dom.window.MouseEvent('click', { bubbles: true, cancelable: true, button: 0 })))
  expect(container.querySelector('.product-content').textContent).toContain('Image source and attribution')
  expect(container.querySelector('.product-content').textContent).toContain('Capture lineage')
})
