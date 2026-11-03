import { createRequire } from 'node:module'
import React, { act } from 'react'
import { createRoot } from 'react-dom/client'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { CollectionCoverage } from '../discovery/CollectionCoverage'
// Can use an existing local DOM installation in offline environments.
const { JSDOM } = createRequire(import.meta.url)(process.env.WATCH_DOM_MODULE || 'jsdom')

// Shapes mirror GET /api/discovery/collection (src/pricerecon/models/collection.py):
// the walkthrough fixture and the staged pilot envelope both carry
// tracking_reserve 0; the shared-grant study carries real reserves.
const ATTEMPTED = '2026-10-27T12:04:48Z'
const resource = (name, used, limit, tracking_reserve) => ({
  resource: name,
  used,
  limit,
  tracking_reserve,
})
const attempt = (over) => ({
  id: 'attempt-1',
  source: 'cex',
  purpose: 'tracking',
  context_id: 'watch:7:fixture',
  query: 'ML05',
  attempted_at: ATTEMPTED,
  state: 'success',
  reason: null,
  next_eligible_at: ATTEMPTED,
  last_good_at: ATTEMPTED,
  last_good_age_seconds: 0,
  evidence_state: 'observed_at_attempt',
  ...over,
})
const status = (over) => ({
  state: 'supplied',
  activation: 'staged',
  gates: ['live_activation_not_authorized'],
  scope_id: 'synthetic-finite-study',
  version: 'fixture-v1',
  stops_at: '2026-10-28T12:00:00Z',
  usage: [resource('requests', 3, 100, 0), resource('pages', 1, 20, 0)],
  provider_usage: [{ source: 'ebay', used: 0, limit: 7, tracking_reserve: 0 }],
  attempts: [],
  ...over,
})

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
  vi.useRealTimers()
  vi.unstubAllGlobals()
})
async function show(body, now = '2026-11-03T09:00:00Z') {
  vi.useFakeTimers({ toFake: ['Date'] })
  vi.setSystemTime(new Date(now))
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => body }))
  await act(async () => {
    root.render(<CollectionCoverage />)
  })
  return container.textContent
}
const stamp = (iso) => new Date(iso).toLocaleString()
const reserveClaim = /have reserved capacity|capacity is reserved/i

// D-1 — the sentence about reserved capacity must follow the data.
it('does not claim reserved capacity when every tracking reserve is zero', async () => {
  const text = await show(status())
  expect(text).not.toMatch(reserveClaim)
  expect(text).toContain(
    'No capacity is held back for tracking or potential-alert verification: every tracking reserve is 0, so discovery can use the whole shared allowance.'
  )
  // The exact technical values stay visible per resource and provider.
  expect(text).toContain('requests: 3 used or reserved of 100; tracking reserve 0.')
  expect(text).toContain('pages: 1 used or reserved of 20; tracking reserve 0.')
  expect(text).toContain('ebay requests: 0 of 7; tracking reserve 0.')
})
it('says how much is held back from discovery when reserves are nonzero', async () => {
  const text = await show(
    status({
      usage: [resource('requests', 1, 1, 0), resource('pages', 1, 20, 1), resource('details', 0, 20, 5)],
      provider_usage: [{ source: 'cex', used: 1, limit: 1, tracking_reserve: 0 }],
    })
  )
  expect(text).toContain(
    'Capacity is held back from discovery for tracking and potential-alert verification on 2 of 4 limits; a tracking reserve of 0 holds nothing back.'
  )
  expect(text).not.toContain('No capacity is held back')
  expect(text).toContain('pages: 1 used or reserved of 20; tracking reserve 1.')
  expect(text).toContain('details: 0 used or reserved of 20; tracking reserve 5.')
  expect(text).toContain('requests: 1 used or reserved of 1; tracking reserve 0.')
  expect(text).toContain('cex requests: 1 of 1; tracking reserve 0.')
})
it('makes no reserve claim when no operating envelope is supplied', async () => {
  const text = await show(status({ state: 'blocked', scope_id: null, stops_at: null, usage: [], provider_usage: [] }))
  expect(text).not.toMatch(reserveClaim)
  expect(text).not.toContain('No capacity is held back')
  expect(text).toContain('No operating envelope is supplied, so no tracking reserve is defined.')
})
it('keeps the unrelated honesty sentences after the reserve sentence', async () => {
  const text = await show(status())
  expect(text).toContain(
    'Capped, blocked and failed attempts leave gaps; an empty result means the declared search completed.'
  )
})

// D-2 — next_eligible_at is the earliest permitted retry (finish time plus
// recovery spacing; src/pricerecon/core/rate_limiter.py), not a schedule.
const NOT_SCHEDULED = 'no run is scheduled and missed periods are not replayed'
it('does not read an elapsed next-eligible time as a pending run (ordinary attempt)', async () => {
  const text = await show(status({ attempts: [attempt()] }))
  expect(text).not.toContain('Next eligible')
  expect(text).toContain(
    `No spacing wait remains (earliest next attempt was ${stamp(ATTEMPTED)}); ${NOT_SCHEDULED}.`
  )
  // The recorded attempt time is not hidden.
  expect(text).toContain(`Attempted ${stamp(ATTEMPTED)}`)
})
it('keeps the same plain reading after the stale step advances only the fixture clock', async () => {
  const text = await show(
    status({ attempts: [attempt({ last_good_age_seconds: 10800 })] }),
    '2026-11-03T09:00:00Z'
  )
  expect(text).toContain('(10800 seconds old)')
  expect(text).toContain(
    `No spacing wait remains (earliest next attempt was ${stamp(ATTEMPTED)}); ${NOT_SCHEDULED}.`
  )
  expect(text).not.toMatch(/Next eligible|will run|scheduled for/)
})
it('shows a future spacing wait for a failed attempt without inventing another time', async () => {
  const later = '2026-11-03T10:30:00Z'
  const text = await show(
    status({
      attempts: [
        attempt({
          state: 'failed',
          reason: 'upstream_error',
          evidence_state: 'unrefreshed',
          last_good_at: null,
          last_good_age_seconds: null,
          attempted_at: '2026-11-03T08:59:00Z',
          next_eligible_at: later,
        }),
      ],
    })
  )
  expect(text).toContain(
    `Source spacing: not retried before ${stamp(later)}; no catch-up replay and no run is scheduled.`
  )
  expect(text).not.toContain('No spacing wait remains')
  expect(text).toContain(`Attempted ${stamp('2026-11-03T08:59:00Z')}`)
})
it('explains a capped attempt whose retry time equals its own time', async () => {
  const text = await show(
    status({
      attempts: [attempt({ state: 'capped', reason: 'resource_exhausted:requests', evidence_state: 'unrefreshed' })],
    })
  )
  expect(text).toContain('capped (resource exhausted:requests)')
  expect(text).toContain(`No spacing wait remains (earliest next attempt was ${stamp(ATTEMPTED)})`)
})
it('shows the lease for a running attempt rather than a retry time', async () => {
  const lease = '2026-11-03T09:05:00Z'
  const text = await show(
    status({
      attempts: [
        attempt({ state: 'running', attempted_at: '2026-11-03T08:59:30Z', next_eligible_at: lease, evidence_state: 'unrefreshed' }),
      ],
    })
  )
  expect(text).toContain(
    `This source is held for the running attempt until ${stamp(lease)}; no catch-up replay and no run is scheduled.`
  )
})
it('says nothing about retry timing when the API records none', async () => {
  const text = await show(
    status({ attempts: [attempt({ state: 'capped', reason: 'recovery_spacing', next_eligible_at: null })] })
  )
  expect(text).not.toContain('Next eligible')
  expect(text).not.toContain('No spacing wait remains')
  expect(text).not.toContain('Source spacing')
})
it('exposes the exact recorded next_eligible_at as a technical tooltip', async () => {
  await show(status({ attempts: [attempt()] }))
  const tip = container.querySelector(`[title="Technical field next_eligible_at: ${ATTEMPTED}"]`)
  expect(tip).not.toBeNull()
})
