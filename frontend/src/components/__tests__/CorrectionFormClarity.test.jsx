import { createRequire } from 'node:module'
import React, { act } from 'react'
import { Simulate } from 'react-dom/test-utils'
import { createRoot } from 'react-dom/client'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { IdentityCorrection } from '../discovery/IdentityCorrection'
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

const dialConfiguration = {
  id: 'watch',
  revision: 1,
  policy_version: 'fixture',
  state: 'supported',
  values: { dial: 'mint', movement: 'Quartz' },
  evidence_ids: [],
  issues: [],
}
const lineageEntry = {
  id: '2c69ade4',
  revision: 1,
  field: 'dial',
  value: 'salmon',
  state: 'corrected',
  original_value: 'mint',
  actor: 'Buyer',
  rationale: 'The selected variation differs from this watch.',
  recorded_at: '2026-10-27T12:04:48Z',
  previous_correction_id: null,
}
const correctionRecord = {
  candidate_id: 'candidate',
  configuration_id: 'watch',
  revision: 1,
  state: 'corrected',
  requalification: 'required',
  values: { dial: 'salmon', movement: 'Quartz' },
  original_configuration: dialConfiguration,
  original_evidence: [],
  needs: ['Fresh compatible configuration and selected merchant variation evidence'],
  lineage: [lineageEntry],
}
const baseCandidate = () => {
  const candidate = parseDiscoveryFeed(captured).candidates[0]
  candidate.configurations = [dialConfiguration]
  candidate.corrections = []
  candidate.identity_state = 'unresolved'
  candidate.public_total = {
    ...candidate.public_total,
    state: 'verified_at_observation',
    amount: '50.10',
    currency: 'GBP',
  }
  return candidate
}
const invalidatedCoupon = {
  id: 'coupon-1',
  revision: 1,
  label: 'Synthetic TEN opportunity',
  state: 'invalidated',
  category: 'public',
  applicability: 'supported',
  lineage: 'observation_only',
  offer_revision: 1,
  binding_revision: 1,
  configuration_revision: 1,
  policy_version: 'coupon-policy',
  identity_policy_version: 'identity-policy',
  captured_at: '2026-10-27T12:00:36Z',
  context: { purchase_scope: null, quantity: null, basket_members: [], consignment_members: [] },
  issues: [],
  opportunity_evidence: [],
  terms: null,
  eligibility: null,
  application: null,
  resulting_cost: null,
  historical_resulting_cost: null,
}

// F2 — the promised before→after preview must track the live form value.
it('shows the before→after preview live while the buyer types, never one save behind', async () => {
  await mount(<IdentityCorrection candidate={baseCandidate()} onSaved={async () => {}} />)
  const preview = container.querySelector('.correction-preview')
  expect(preview).not.toBeNull()
  // Before a value is chosen the preview is greyed out — it must not show a
  // fake identical "intended" value that reads as "nothing happened".
  expect(preview.textContent).toContain('You are changing dial from mint to')
  expect(preview.querySelector('.correction-preview-pending')).not.toBeNull()
  expect(preview.textContent).not.toContain('to mint')
  await change(container.querySelector('[aria-label="What should it be?"]'), '__custom')
  const custom = container.querySelector('[aria-label="What should it be? custom value"]')
  await act(async () => Simulate.change(custom, { target: { value: 'salmon' } }))
  expect(container.querySelector('.correction-preview').textContent).toContain('from mint to salmon')
  // A preset pick updates the preview just as immediately.
  await change(container.querySelector('[aria-label="What should it be?"]'), 'Blue')
  expect(container.querySelector('.correction-preview').textContent).toContain('from mint to Blue')
})

// F2 — once a correction exists, the stale value is named, not shown as current.
it('labels the previously saved value instead of presenting a stale intended value', async () => {
  const candidate = baseCandidate()
  candidate.corrections = [correctionRecord]
  await mount(<IdentityCorrection candidate={candidate} onSaved={async () => {}} />)
  const preview = container.querySelector('.correction-preview')
  expect(preview.textContent).toContain('You are changing dial from mint to')
  expect(preview.textContent).toContain('Last saved value: salmon')
  expect(container.textContent).not.toContain('Intended value:')
})

// F3 — the picker must be able to express the task (dial → salmon).
it('makes the current value visible and any value typeable in the value picker', async () => {
  await mount(<IdentityCorrection candidate={baseCandidate()} onSaved={async () => {}} />)
  const select = container.querySelector('[aria-label="What should it be?"]')
  const optionTexts = Array.from(select.options).map((option) => option.textContent)
  expect(optionTexts).toContain('mint (current)')
  expect(optionTexts).toContain('Type another value…')
  expect(optionTexts).not.toContain('Not set')
  expect(optionTexts).not.toContain('Other / custom')
  // The current value is selectable like any other value.
  await change(select, 'mint')
  expect(container.querySelector('.correction-preview').textContent).toContain('from mint to mint')
})

// F7 — the reason select must not offer "Not set" on a required field, and
// must say where the reason is permanently recorded.
it('drops the Not-set trap from the required reason and states where the reason goes', async () => {
  await mount(<IdentityCorrection candidate={baseCandidate()} onSaved={async () => {}} />)
  const reason = container.querySelector('[aria-label^="Reason"]')
  expect(reason.getAttribute('aria-label')).toBe(
    'Reason (recorded with your name in the correction history)'
  )
  const optionTexts = Array.from(reason.options).map((option) => option.textContent)
  expect(optionTexts).not.toContain('Not set')
  expect(optionTexts[0]).toBe('Choose a reason…')
  expect(optionTexts).toContain('Write your own reason…')
})

// F8 — the button names the act; consequences appear post-decision only.
it('sells the action honestly and states consequences only once a change is pending', async () => {
  await mount(<IdentityCorrection candidate={baseCandidate()} onSaved={async () => {}} />)
  expect(container.querySelector('button[type="submit"]').textContent).toBe(
    'Save correction — old prices will be withdrawn'
  )
  expect(container.textContent).not.toContain('Old prices stop applying')
  expect(container.textContent).not.toContain('does not fetch new prices')
  await change(container.querySelector('[aria-label="What should it be?"]'), 'Blue')
  expect(container.textContent).toContain(
    'Saving records your correction; it does not fetch new prices'
  )
})

// F6 — plain-language labels; the internal vocabulary stays available second.
it('labels the form for the buyer and keeps jargon out of the controls', async () => {
  const candidate = baseCandidate()
  candidate.corrections = [correctionRecord]
  await mount(<IdentityCorrection candidate={candidate} onSaved={async () => {}} />)
  const form = container.querySelector('form')
  expect(form.textContent).toContain("What's wrong?")
  expect(form.textContent).toContain('What should it be?')
  expect(form.textContent).toContain('How sure are you?')
  const sure = container.querySelector('[name="correction_state"]')
  expect(Array.from(sure.options).map((option) => option.textContent)).toEqual([
    "It's fixed — re-check prices",
    'Not sure — pause buying qualification',
  ])
  expect(container.textContent).not.toContain('Correction state')
  expect(container.textContent).not.toContain('Identity state')
  expect(container.textContent).not.toContain('Identity field')
  expect(container.textContent).not.toContain('Disputed; withhold qualification')
})

// F6 — one changed field on top; the nine-field intended configuration
// behind an explicit disclosure.
it('summarises the changed field and puts the full intended configuration behind a disclosure', async () => {
  const candidate = baseCandidate()
  candidate.corrections = [correctionRecord]
  await mount(<IdentityCorrection candidate={candidate} onSaved={async () => {}} />)
  const history = container.querySelector('#correction-history')
  expect(history).not.toBeNull()
  expect(history.textContent).toContain('dial: mint → salmon')
  const disclosure = history.querySelector('details')
  expect(disclosure.querySelector('summary').textContent).toBe('Show full intended configuration')
  expect(disclosure.textContent).toContain('movement')
  // The raw requalification enum must not leak into a heading.
  const headings = Array.from(history.querySelectorAll('h3')).map((heading) => heading.textContent)
  expect(headings).toContain('Corrected — waiting for fresh evidence')
  expect(headings.join(' ')).not.toContain('· required')
  expect(history.textContent).not.toContain('Identity corrected · required')
})

// F4 — after saving, the outcome names each dependent effect and the
// appended lineage entry, with links to every surface.
it('reports what happened because of the correction, linking each effect', async () => {
  const start = baseCandidate()
  start.offers = [{ ...invalidatedCouponOffer() }]
  const tracking = {
    id: 1,
    revision: 1,
    candidate_id: start.id,
    capture_id: start.capture_id,
    configuration_id: 'watch',
    configuration_revision: 1,
    target_gbp: '60',
    notifications: { channels: ['webhook'] },
    invalidation_revision: 0,
    invalidation_reason: null,
    assessment: {
      state: 'withheld',
      reasons: ['evidence_invalidated'],
      assessed_at: '2026-10-27T12:04:48Z',
      valid_until: '2026-10-27T13:04:48Z',
      delivered_gbp: null,
      policy_version: 'policy-v1',
    },
  }
  const saved = baseCandidate()
  saved.configurations = [{ ...dialConfiguration, state: 'unresolved', values: { dial: 'salmon' } }]
  saved.corrections = [correctionRecord]
  saved.public_total = { ...saved.public_total, state: 'unknown', amount: null, currency: 'GBP' }
  saved.offers = [{ ...invalidatedCouponOffer(), coupons: [invalidatedCoupon] }]
  const fetch = vi.fn().mockResolvedValue({
    ok: true,
    json: async () => correctionResponse(saved),
  })
  vi.stubGlobal('fetch', fetch)
  function Harness() {
    const [candidate, setCandidate] = React.useState(start)
    return (
      <IdentityCorrection
        candidate={candidate}
        tracking={[tracking]}
        onSaved={async () => {
          setCandidate(saved)
        }}
      />
    )
  }
  await mount(<Harness />)
  await change(container.querySelector('[aria-label="What should it be?"]'), '__custom')
  await act(async () =>
    Simulate.change(container.querySelector('[aria-label="What should it be? custom value"]'), {
      target: { value: 'salmon' },
    })
  )
  await act(async () =>
    Simulate.change(container.querySelector('[name="correction_actor"]'), {
      target: { value: 'Buyer' },
    })
  )
  await act(async () =>
    container
      .querySelector('form')
      .dispatchEvent(new dom.window.Event('submit', { bubbles: true, cancelable: true }))
  )
  const summary = container.querySelector('[role="status"]')
  expect(summary).not.toBeNull()
  expect(summary.textContent).toContain('Correction saved — a history entry was added below.')
  expect(summary.textContent).toContain('Because dial changed (mint → salmon):')
  expect(summary.textContent).toContain('Total unknown')
  expect(summary.textContent).toContain('was GBP 50.10')
  expect(summary.textContent).toContain('Synthetic TEN opportunity')
  expect(summary.textContent).toContain('kept as a dated record')
  expect(summary.textContent).toContain('kept, unchanged, in History')
  expect(summary.textContent).toContain('your £60 target stays saved')
  expect(summary.textContent).toContain('1 entry appended to the correction history (nothing is overwritten)')
  const links = Array.from(summary.querySelectorAll('a')).map((link) => link.getAttribute('href'))
  expect(links.some((href) => href.includes('view=costs'))).toBe(true)
  expect(links.some((href) => href.includes('view=history'))).toBe(true)
  expect(links.some((href) => href.includes('view=tracking'))).toBe(true)
  expect(links).toContain('#correction-history')
  // The appended lineage entry itself is visible below the summary.
  expect(container.querySelector('#correction-history').textContent).toContain(
    'dial: mint → salmon'
  )
})

it('uses neutral target wording after a disputed save', async () => {
  const start = baseCandidate()
  const disputedRecord = {
    ...correctionRecord,
    state: 'disputed',
    lineage: [{ ...lineageEntry, state: 'disputed' }],
  }
  const saved = baseCandidate()
  saved.configurations = [
    { ...dialConfiguration, state: 'conflicting', values: { dial: 'salmon', movement: 'Quartz' } },
  ]
  saved.corrections = [disputedRecord]
  saved.public_total = { ...saved.public_total, state: 'unknown', amount: null, currency: 'GBP' }
  const tracking = {
    id: 1,
    revision: 1,
    candidate_id: start.id,
    capture_id: start.capture_id,
    configuration_id: 'watch',
    configuration_revision: 1,
    target_gbp: '60',
    notifications: { channels: ['webhook'] },
    invalidation_revision: 0,
    invalidation_reason: null,
    assessment: {
      state: 'withheld',
      reasons: ['evidence_invalidated'],
      assessed_at: '2026-10-27T12:04:48Z',
      valid_until: '2026-10-27T13:04:48Z',
      delivered_gbp: null,
      policy_version: 'policy-v1',
    },
  }
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
    ok: true,
    json: async () => correctionResponse(saved),
  }))
  function Harness() {
    const [candidate, setCandidate] = React.useState(start)
    return (
      <IdentityCorrection
        candidate={candidate}
        tracking={[tracking]}
        onSaved={async () => setCandidate(saved)}
      />
    )
  }
  await mount(<Harness />)
  await change(container.querySelector('[aria-label="What should it be?"]'), '__custom')
  await act(async () =>
    Simulate.change(container.querySelector('[aria-label="What should it be? custom value"]'), {
      target: { value: 'salmon' },
    })
  )
  await change(container.querySelector('[name="correction_state"]'), 'disputed')
  await act(async () =>
    Simulate.change(container.querySelector('[name="correction_actor"]'), {
      target: { value: 'Buyer' },
    })
  )
  await act(async () =>
    container
      .querySelector('form')
      .dispatchEvent(new dom.window.Event('submit', { bubbles: true, cancelable: true }))
  )
  const summary = container.querySelector('.correction-outcome')
  const targetOutcome = Array.from(summary.querySelectorAll('li')).find((item) =>
    item.textContent.includes('target stays saved')
  )
  expect(targetOutcome.textContent).toBe(
    'your £60 target stays saved; alerts wait for fresh evidence for this watch · see Tracking'
  )
  expect(targetOutcome.textContent).not.toBe(
    'your £60 target stays saved; alerts wait for evidence for the corrected watch · see Tracking'
  )
})

function invalidatedCouponOffer() {
  return {
    id: 'offer',
    revision: 1,
    binding_id: 'binding',
    binding_revision: 1,
    source: 'fixture',
    source_listing_id: 'addies',
    source_evidence: null,
    seller: 'Fixture seller',
    condition: 'new',
    condition_description: null,
    visible_condition: null,
    quantity: 1,
    availability: 'unknown',
    purchase_mode: 'buy_now',
    item_price: '50.00',
    currency: 'GBP',
    destination: 'UK',
    qualification: { state: 'unresolved', values: {}, evidence_ids: [], issues: [] },
    comparison: { state: 'unresolved', values: {}, evidence_ids: [], issues: [] },
    comparison_cohort: null,
    policy_version: 'offer-policy',
    evidence: [],
    coupons: [],
    cost_scenarios: [],
  }
}

function correctionResponse(candidate) {
  return {
    ...candidate.corrections[0],
    candidate_id: candidate.id,
  }
}
