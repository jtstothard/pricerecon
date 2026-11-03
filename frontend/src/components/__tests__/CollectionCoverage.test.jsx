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

// Backend states (src/pricerecon/db/collection.py collection_status): a policy is
// only retained for supplied, expired/not-yet-started and operating_policy_changed.
// invalid, ambiguous and required select no policy, so scope_id/stops_at are null
// and usage/provider_usage are empty. The helper refuses to build the impossible
// combination so a fixture cannot assert rows the backend cannot produce.
const TAIL = ['live_activation_not_authorized', 'production_operating_envelope_unproven']
const NO_POLICY_GATES = ['operating_policy_invalid', 'operating_policy_ambiguous', 'operating_policy_required']
const rejected = (gate, over = {}) => {
  if (!NO_POLICY_GATES.includes(gate)) throw new Error(`${gate} retains a policy`)
  const body = status({
    state: 'blocked',
    gates: [gate, ...TAIL],
    scope_id: null,
    version: null,
    stops_at: null,
    usage: [],
    provider_usage: [],
    ...over,
  })
  if (body.scope_id || body.stops_at || body.usage.length || body.provider_usage.length)
    throw new Error(`${gate} cannot carry a policy, scope, stop time or usage rows`)
  return body
}
const changed = (over = {}) =>
  status({ state: 'blocked', gates: ['operating_policy_changed', ...TAIL], ...over })

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
    'No capacity is carved out of the shared allowance for tracking or potential-alert verification: every tracking reserve is 0, so discovery and tracking draw on the same allowance until a limit is used up.'
  )
  // A zero reserve is not an admission guarantee or an unrestricted-discovery claim.
  expect(text).not.toMatch(/discovery can use the whole|whole shared allowance/i)
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
  expect(text).not.toContain('No capacity is carved out')
  expect(text).toContain('pages: 1 used or reserved of 20; tracking reserve 1.')
  expect(text).toContain('details: 0 used or reserved of 20; tracking reserve 5.')
  expect(text).toContain('requests: 1 used or reserved of 1; tracking reserve 0.')
  expect(text).toContain('cex requests: 1 of 1; tracking reserve 0.')
})
it('cannot build an invalid/ambiguous/required fixture that carries usage rows', () => {
  for (const gate of NO_POLICY_GATES) {
    expect(() => rejected(gate, { usage: [resource('requests', 3, 100, 0)] })).toThrow(/cannot carry/)
    expect(() => rejected(gate, { scope_id: 'synthetic-finite-study' })).toThrow(/cannot carry/)
    expect(() => rejected(gate, { provider_usage: [{ source: 'ebay', used: 0, limit: 7, tracking_reserve: 0 }] })).toThrow(/cannot carry/)
  }
  expect(() => rejected('operating_policy_changed')).toThrow(/retains a policy/)
})
const NO_CLAIM = /discovery and tracking draw|whole shared allowance|No capacity is carved out|have reserved capacity|capacity is reserved/i
it('says a rejected (invalid) envelope was supplied but is unusable, with no policy rows', async () => {
  const text = await show(rejected('operating_policy_invalid'))
  expect(text).toContain('Operating policy: blocked.')
  expect(text).toContain(
    'A supplied operating envelope was rejected as invalid, so there is no usable operating envelope and no tracking reserve is defined. Admission is closed.'
  )
  expect(text).not.toContain('No operating envelope is supplied')
  expect(text).not.toMatch(NO_CLAIM)
  expect(text).not.toContain('used or reserved of')
  expect(text).not.toContain('Envelope ')
  expect(text).toContain('operating policy invalid')
})
it('says an ambiguous envelope selection cannot be resolved, with no policy rows', async () => {
  const text = await show(rejected('operating_policy_ambiguous'))
  expect(text).toContain(
    'More than one operating envelope is stored and none can be chosen, so there is no usable operating envelope and no tracking reserve is defined. Admission is closed.'
  )
  expect(text).not.toContain('No operating envelope is supplied')
  expect(text).not.toMatch(NO_CLAIM)
  expect(text).not.toContain('used or reserved of')
  expect(text).toContain('operating policy ambiguous')
})
it('says a required envelope is missing, with no policy rows', async () => {
  const text = await show(rejected('operating_policy_required'))
  expect(text).toContain(
    'An operating envelope is required and none usable is available, so no tracking reserve is defined. Admission is closed.'
  )
  expect(text).not.toMatch(NO_CLAIM)
  expect(text).not.toContain('used or reserved of')
  expect(text).toContain('operating policy required')
})
it('keeps the retained envelope and its exact rows when the supplied policy changed', async () => {
  const text = await show(
    changed({
      usage: [resource('requests', 3, 100, 0), resource('pages', 1, 20, 2)],
      provider_usage: [{ source: 'ebay', used: 4, limit: 7, tracking_reserve: 1 }],
    })
  )
  expect(text).toContain(
    'The supplied operating policy differs from the retained envelope, so admission is closed and no tracking reserve currently applies. The retained envelope is shown for reference; nothing can use its figures.'
  )
  expect(text).not.toMatch(NO_CLAIM)
  expect(text).not.toMatch(/no current operating envelope|No operating envelope is supplied|rejected as invalid/)
  // The envelope row does not contradict the sentence above it.
  expect(text).toContain(
    `Retained envelope synthetic-finite-study is not in force; recorded stop time ${stamp('2026-10-28T12:00:00Z')}.`
  )
  expect(text).toContain('requests: 3 used or reserved of 100; tracking reserve 0.')
  expect(text).toContain('pages: 1 used or reserved of 20; tracking reserve 2.')
  expect(text).toContain('ebay requests: 4 of 7; tracking reserve 1.')
  expect(text).toContain('operating policy changed')
})
it('does not claim an expiry before the envelope starts (expired state covers not-yet-started)', async () => {
  for (const stops_at of ['2026-11-02T12:00:00Z', '2026-11-30T12:00:00Z']) {
    const text = await show(status({ state: 'expired', gates: ['operating_policy_expired', ...TAIL], stops_at }))
    expect(text).not.toMatch(NO_CLAIM)
    expect(text).not.toMatch(/has expired|have expired|already expired/)
    expect(text).toContain(
      'The operating envelope is not active now (its window has closed or has not opened yet): admission is closed, so no tracking reserve currently applies. The recorded figures below are exact but nothing can use them.'
    )
    expect(text).toContain(`Retained envelope synthetic-finite-study is not in force; recorded stop time ${stamp(stops_at)}.`)
    expect(text).toContain('requests: 3 used or reserved of 100; tracking reserve 0.')
    await act(async () => root.unmount())
    root = createRoot(container)
  }
})
it('describes a supplied envelope that sets no limits without calling it unsupplied', async () => {
  const text = await show(status({ usage: [], provider_usage: [] }))
  expect(text).toContain('The supplied operating envelope sets no limits, so no tracking reserve is defined.')
  expect(text).not.toContain('No operating envelope is supplied')
  expect(text).toContain('Envelope synthetic-finite-study; stops')
})
it('says a supplied envelope with a limit used up is already at its limit, not open capacity', async () => {
  const text = await show(
    status({
      usage: [resource('requests', 100, 100, 0), resource('pages', 1, 20, 0)],
      provider_usage: [{ source: 'ebay', used: 7, limit: 7, tracking_reserve: 0 }],
    })
  )
  expect(text).toContain('2 of 3 limits are already used up, so further attempts that need them are capped.')
  expect(text).not.toMatch(/whole shared allowance/i)
  expect(text).toContain('requests: 100 used or reserved of 100; tracking reserve 0.')
})
it('does not add a used-up sentence when nothing is at its limit', async () => {
  expect(await show(status())).not.toContain('already used up')
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
const BROWSER = "by this browser's clock"
const SERVER = 'the server decides admission when an attempt starts'
it('does not read an elapsed next-eligible time as a pending run (ordinary attempt)', async () => {
  const text = await show(status({ attempts: [attempt()] }))
  expect(text).not.toContain('Next eligible')
  expect(text).toContain(
    `By this browser's clock no spacing wait remains (recorded earliest next attempt: ${stamp(ATTEMPTED)}); ${SERVER}; ${NOT_SCHEDULED}.`
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
    `By this browser's clock no spacing wait remains (recorded earliest next attempt: ${stamp(ATTEMPTED)}); ${SERVER}; ${NOT_SCHEDULED}.`
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
    `Source spacing: recorded earliest next attempt is ${stamp(later)} (${BROWSER}, still ahead); ${SERVER}; ${NOT_SCHEDULED}.`
  )
  expect(text).not.toContain('no spacing wait remains')
  expect(text).toContain(`Attempted ${stamp('2026-11-03T08:59:00Z')}`)
})
it('explains a capped attempt whose retry time equals its own time', async () => {
  const text = await show(
    status({
      attempts: [attempt({ state: 'capped', reason: 'resource_exhausted:requests', evidence_state: 'unrefreshed' })],
    })
  )
  expect(text).toContain('capped (resource exhausted:requests)')
  expect(text).toContain(`no spacing wait remains (recorded earliest next attempt: ${stamp(ATTEMPTED)})`)
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
    `This source is held for the running attempt until ${stamp(lease)} (${BROWSER}, lease still ahead); ${SERVER}; ${NOT_SCHEDULED}.`
  )
  expect(text).not.toContain('Lease expired')
})
it('does not say the source is held when a running attempt lease has passed (crashed process)', async () => {
  const lease = '2026-11-03T08:30:00Z'
  const text = await show(
    status({
      attempts: [
        attempt({ state: 'running', attempted_at: '2026-11-03T08:20:00Z', next_eligible_at: lease, evidence_state: 'unrefreshed' }),
      ],
    })
  )
  expect(text).not.toContain('is held for the running attempt')
  expect(text).not.toContain('This source is held')
  expect(text).toContain(
    `Lease expired, unconfirmed: the running attempt's lease ended ${stamp(lease)} (${BROWSER}) with no recorded finish; ${SERVER}; ${NOT_SCHEDULED}.`
  )
})
it('judges a running lease against the browser clock at the moment it renders', async () => {
  const lease = '2026-11-03T09:00:30Z'
  const row = attempt({ state: 'running', next_eligible_at: lease, evidence_state: 'unrefreshed' })
  expect(await show(status({ attempts: [row] }), '2026-11-03T09:00:00Z')).toContain('held for the running attempt')
  await act(async () => root.unmount())
  root = createRoot(container)
  expect(await show(status({ attempts: [row] }), '2026-11-03T09:00:31Z')).toContain('Lease expired, unconfirmed')
})
it('never presents a browser-clock judgement as server certainty', async () => {
  const rows = [
    attempt({ id: 'a', next_eligible_at: '2026-11-03T10:30:00Z' }),
    attempt({ id: 'b' }),
    attempt({ id: 'c', state: 'running', next_eligible_at: '2026-11-03T09:05:00Z', evidence_state: 'unrefreshed' }),
    attempt({ id: 'd', state: 'running', next_eligible_at: '2026-11-03T08:30:00Z', evidence_state: 'unrefreshed' }),
  ]
  const text = await show(status({ attempts: rows }))
  expect(text.match(/this browser's clock/g)).toHaveLength(4)
  expect(text.match(/the server decides admission when an attempt starts/g)).toHaveLength(4)
  expect(text).not.toMatch(/is not retried|cannot retry|will be retried|server (confirms|time)/i)
})
it('keeps the exact recorded ISO instant in the tooltip so the local rendering is never the only record', async () => {
  const iso = '2026-11-03T10:30:00Z'
  await show(status({ attempts: [attempt({ state: 'failed', reason: 'upstream_error', next_eligible_at: iso })] }))
  expect(container.querySelector(`[title="Technical field next_eligible_at: ${iso}"]`)).not.toBeNull()
})
it('says nothing about retry timing when the API records none', async () => {
  const text = await show(
    status({ attempts: [attempt({ state: 'capped', reason: 'recovery_spacing', next_eligible_at: null })] })
  )
  expect(text).not.toContain('Next eligible')
  expect(text).not.toContain('no spacing wait remains')
  expect(text).not.toContain('Source spacing')
})
it('exposes the exact recorded next_eligible_at as a technical tooltip', async () => {
  await show(status({ attempts: [attempt()] }))
  const tip = container.querySelector(`[title="Technical field next_eligible_at: ${ATTEMPTED}"]`)
  expect(tip).not.toBeNull()
})
