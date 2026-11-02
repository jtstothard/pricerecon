import { createRequire } from 'node:module'
import React, { act } from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { createRoot } from 'react-dom/client'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import Discovery, { Candidate, ProductContent, ProductDetail } from '../../pages/Discovery'
import { ObservationHistory } from '../discovery/ObservationHistory'
import ExactTrackingControl, { TrackingStatus } from '../ExactTracking'
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

const dialConfiguration = {
  id: 'watch',
  revision: 2,
  policy_version: 'fixture',
  state: 'unresolved',
  values: { dial: 'salmon', movement: 'Quartz' },
  evidence_ids: [],
  issues: [],
}
const originalConfiguration = {
  ...dialConfiguration,
  revision: 1,
  state: 'supported',
  values: { dial: 'mint', movement: 'Quartz' },
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
const correctedCandidate = () => {
  const candidate = parseDiscoveryFeed(captured).candidates[0]
  candidate.identity_state = 'unresolved'
  candidate.public_total = {
    ...candidate.public_total,
    state: 'unknown',
    amount: null,
    currency: 'GBP',
  }
  candidate.configurations = [dialConfiguration]
  candidate.corrections = [
    {
      candidate_id: candidate.id,
      configuration_id: 'watch',
      revision: 1,
      state: 'corrected',
      requalification: 'required',
      values: { dial: 'salmon', movement: 'Quartz' },
      original_configuration: originalConfiguration,
      original_evidence: [],
      needs: ['Fresh compatible configuration and selected merchant variation evidence'],
      lineage: [lineageEntry],
    },
  ]
  return candidate
}

// F1 — the correction entry point sits where the buyer looks first.
it('links “Wrong watch details?” from the feed card, hero and Technical tab', async () => {
  const candidate = correctedCandidate()
  const card = renderToStaticMarkup(<Candidate candidate={candidate} tracking={[]} />)
  expect(card).toContain('Wrong watch details?</a>')
  expect(card).toContain('view=correction')
  const technical = renderToStaticMarkup(
    <ProductContent
      candidate={candidate}
      tracking={[]}
      onSaved={async () => {}}
      view="technical"
    />
  )
  expect(technical).toContain('Details wrong? Correct them on the')
  expect(technical).toContain('technical record')
})

// F1 — the tab names the buyer's thought, and the kit's “Technical record”
// vocabulary is bridged on screen.
it('names the correction tab after the buyer’s thought', async () => {
  const candidate = correctedCandidate()
  const body = { ...captured, candidates: [{ ...correctionPayloadFor(candidate), corrections: [] }] }
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => body }))
  await mount(
    <MemoryRouter initialEntries={[`/discover/product/${candidate.id}`]}>
      <Routes>
        <Route path="/discover/product/:id" element={<ProductDetail />} />
      </Routes>
    </MemoryRouter>
  )
  const navLinks = Array.from(container.querySelectorAll('nav[aria-label="Product sections"] a'))
  const labels = navLinks.map((link) => link.textContent)
  expect(labels).toContain('Wrong details?')
  expect(labels).not.toContain('Correction')
  const correctionLink = navLinks.find((link) => link.textContent === 'Wrong details?')
  expect(correctionLink.getAttribute('href')).toContain('view=correction')
  const hero = container.querySelector('[aria-label="Watch buying summary"]')
  expect(hero.textContent).toContain('Wrong watch details?')
  // F10 — the hero must not stutter "Total unknown. … Total unknown."
  const priceSummary = container.querySelector('.product-price-summary')
  expect(priceSummary.querySelector('.product-delivered-price').textContent).toBe('Total unknown')
  expect(
    priceSummary.querySelector('.product-delivered-price + p').textContent.startsWith('Total unknown')
  ).toBe(false)
})

function correctionPayloadFor(candidate) {
  // The API feed payload shape: the parsed fixture candidate is embedded
  // as the first candidate with our identity fields.
  return {
    ...captured.candidates[0],
    id: candidate.id,
    configurations: [originalConfiguration],
    corrections: [],
  }
}

// F9 — the card and hero must show the correction and its cause so the
// retained reported title is not misread as the change failing.
it('shows the corrected value and explains the state change on the card', async () => {
  const candidate = correctedCandidate()
  const card = renderToStaticMarkup(<Candidate candidate={candidate} tracking={[]} />)
  expect(card).toContain('Details corrected (dial mint → salmon)')
  expect(card).toContain('kept on record, no longer used for pricing')
  expect(card).toContain('awaiting fresh evidence')
  expect(card).toContain('salmon (was: mint, as listed)')
  expect(card).toContain('Identity unresolved — awaiting fresh evidence')
  // The corrected-caution string is one vocabulary, identically punctuated.
  expect(card).not.toContain('Old prices withdrawn · matching offer needed')
})

// S5 residual 3 — repeated corrections to one field have one current value;
// the complete chain remains available in correction history.
it('shows only the latest value and original observation for repeated corrections', async () => {
  const candidate = correctedCandidate()
  const secondEntry = {
    ...lineageEntry,
    id: '9615feda',
    revision: 2,
    value: 'Blue',
    original_value: 'salmon',
    previous_correction_id: lineageEntry.id,
    rationale: 'The source description conflicts with the watch shown.',
  }
  candidate.corrections[0].revision = 2
  candidate.corrections[0].values = { dial: 'Blue', movement: 'Quartz' }
  candidate.corrections[0].lineage = [lineageEntry, secondEntry]
  candidate.configurations = [
    { ...dialConfiguration, values: { dial: 'Blue', movement: 'Quartz' } },
  ]

  const card = renderToStaticMarkup(<Candidate candidate={candidate} tracking={[]} />)
  expect(card).toContain('Details corrected (dial mint → Blue)')
  expect(card).toContain('dial: Blue (was: mint, as listed)')
  expect(card).not.toContain('dial: salmon (was: mint, as listed)')
  expect(card).not.toContain('dial: Blue (was: salmon, as listed)')
  expect(card).not.toContain('dial mint → salmon · dial salmon → Blue')

  const rawCandidate = {
    ...correctionPayloadFor(candidate),
    identity_state: 'unresolved',
    public_delivered_total: {
      ...captured.candidates[0].public_delivered_total,
      state: 'unknown',
      amount: null,
    },
    configurations: candidate.configurations,
    corrections: candidate.corrections,
  }
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
    ok: true,
    json: async () => ({ ...captured, candidates: [rawCandidate] }),
  }))
  await mount(
    <MemoryRouter initialEntries={[`/discover/product/${candidate.id}`]}>
      <Routes>
        <Route path="/discover/product/:id" element={<ProductDetail />} />
      </Routes>
    </MemoryRouter>
  )
  const hero = container.querySelector('[aria-label="Watch buying summary"]')
  expect(hero.textContent).toContain('Details corrected (dial mint → Blue)')
  expect(hero.textContent).toContain('dialBlue (was: mint, as listed)')
  expect(hero.textContent).not.toContain('dialsalmon (was: mint, as listed)')
  expect(hero.textContent).not.toContain('dialBlue (was: salmon, as listed)')

  const history = renderToStaticMarkup(
    <ProductContent
      candidate={candidate}
      tracking={[]}
      onSaved={async () => {}}
      view="correction"
    />
  )
  expect(history).toContain('mint → salmon')
  expect(history).toContain('salmon → Blue')
})

// S5 residual 1 — a corrected target must not fall back to raw withdrawal
// vocabulary on the feed card.
it('glosses a withheld corrected target on the feed card and retains its technical state', () => {
  const candidate = correctedCandidate()
  const intent = {
    id: 1,
    revision: 1,
    candidate_id: candidate.id,
    capture_id: candidate.capture_id,
    configuration_id: 'watch',
    configuration_revision: 1,
    target_gbp: '60',
    notifications: { channels: ['webhook'] },
    invalidation_revision: 1,
    invalidation_reason: 'evidence_invalidated',
    assessment: {
      state: 'withheld',
      reasons: ['evidence_invalidated'],
      assessed_at: '2026-10-27T12:04:48Z',
      valid_until: '2026-10-27T13:04:48Z',
      delivered_gbp: null,
      policy_version: 'policy-v1',
    },
  }
  const card = renderToStaticMarkup(<Candidate candidate={candidate} tracking={[intent]} />)
  expect(card).toContain('Target £60 · alert withheld')
  expect(card).toContain('old evidence kept on record, no longer used for alerts')
  expect(card).toContain('title="Technical state: withheld; reasons: evidence_invalidated"')
  expect(card).not.toContain('Target £60 · withheld · evidence withdrawn')
})

// F5 — one plain-language family for the correction event; precise terms
// stay available second (title tooltips).
it('uses the kept-on-record vocabulary across Costs consequences', async () => {
  const candidate = correctedCandidate()
  candidate.advertised_item_price = '70.00'
  candidate.missing_data = ['freshness: freshness_unvalidated']
  candidate.offers = [
    {
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
      coupons: [
        {
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
          context: {
            purchase_scope: null,
            quantity: null,
            basket_members: [],
            consignment_members: [],
          },
          issues: ['receipt_predates_correction', 'source_revision_superseded'],
          opportunity_evidence: [],
          terms: null,
          eligibility: null,
          application: null,
          resulting_cost: null,
          historical_resulting_cost: null,
        },
      ],
      cost_scenarios: [
        {
          id: 'cost',
          revision: 1,
          policy_version: 'cost-policy',
          offer_id: 'offer',
          offer_revision: 1,
          binding_id: 'binding',
          binding_revision: 1,
          configuration_id: 'watch',
          configuration_revision: 1,
          key: 'cost-key',
          kind: 'public_no_coupon',
          state: 'unknown',
          captured_at: '2026-10-27T12:00:36Z',
          context: { purchase_scope: 'standalone', quantity: 1, basket_members: [], consignment_members: [] },
          context_evidence: [],
          assumptions: [],
          issues: ['identity_correction_withdrawn'],
          withdrawn: true,
          historical_total: { currency: 'GBP', amount: '50.10' },
          total: null,
          known_subtotal: { GBP: '50.00' },
          merchant_payable: { GBP: '50.00' },
          additional_liabilities: {},
          components: [
            {
              kind: 'import_tax',
              state: 'not_applicable',
              amount: null,
              currency: null,
              basis: 'scenario',
              included_in: null,
              payer: 'buyer',
              collector: 'merchant',
              reason: 'No import tax applies to this synthetic scenario.',
              assumptions: [],
              evidence: [],
            },
          ],
          benefits: [],
          fx_quotes: [],
        },
      ],
    },
  ]
  const costs = renderToStaticMarkup(
    <ProductContent
      candidate={candidate}
      tracking={[]}
      onSaved={async () => {}}
      view="costs"
    />
  )
  // The doubled “Total unknown — Total unknown” rendering bug is gone.
  expect(costs).not.toContain('Total unknown — Total unknown')
  expect(costs).toContain('Total unknown')
  // One vocabulary for withdrawn things, with the precise term beside it.
  expect(costs).toContain('kept on record, no longer used for pricing')
  expect(costs).toContain('Historical item lead')
  expect(costs).not.toContain('Historical item lead (withdrawn)')
  expect(costs).not.toContain('Historical cost withdrawn.')
  expect(costs).toContain('Invalidated — kept on record')
  // Bare enum paragraphs are labelled.
  expect(costs).not.toMatch(/<p>supported<\/p>/)
  expect(costs).toContain('Coupon applicability: supported at observation')
  // S5 residual 2 — every named raw Costs code has buyer wording and keeps
  // the precise code available as a technical tooltip, not as visible copy.
  expect(costs).toContain('Watch details were corrected — this cost is kept on record, no longer used for pricing.')
  expect(costs).toContain('Coupon receipt predates the correction — kept on record, no longer used for pricing.')
  expect(costs).toContain('Source revision superseded — coupon receipt kept on record, no longer used for pricing.')
  expect(costs).toContain('Freshness not validated — current price and availability are not established.')
  expect(costs).toContain('unknown; not applicable. No import tax applies to this synthetic scenario.')
  for (const code of [
    'identity_correction_withdrawn',
    'receipt_predates_correction',
    'source_revision_superseded',
    'freshness: freshness_unvalidated',
    'not_applicable',
  ]) {
    expect(costs).toContain(`title="Technical detail: ${code}"`)
  }
  expect(costs).not.toContain('<li>identity_correction_withdrawn</li>')
  expect(costs).not.toContain('<li>receipt_predates_correction</li>')
  expect(costs).not.toContain('<li>source_revision_superseded</li>')
  expect(costs).not.toContain('freshness: freshness_unvalidated</p>')
  expect(costs).not.toContain('unknown; not_applicable.')
})

// S5 residual 5 — historical assessments name the correction that made
// them historical instead of relying on the transient post-save summary.
it('names correction-driven invalidation on historical assessments', () => {
  const candidate = correctedCandidate()
  const claim = {
    state: 'invalidated',
    amount: '45.10',
    reason: 'Identity corrected: dial',
    observation_count: 6,
    synthetic: true,
    paths: [],
  }
  candidate.price_assessments = [
    {
      id: 'assessment-1',
      revision: 2,
      historical: true,
      assessed_at: '2026-10-27T12:00:36Z',
      method: 'qualified-payable-minimum-v1',
      cohort: { condition: 'new', quantity: '1' },
      policy_version: 'policy-v1',
      policy_fingerprint: 'fingerprint',
      window_start: '2026-10-27T12:00:00Z',
      window_end: '2026-10-27T12:04:48Z',
      max_age: 3600,
      allowed_scenarios: ['public_no_coupon', 'public_coupon'],
      current_best: claim,
      observed_low: claim,
      usual_price: { ...claim, state: 'unavailable', amount: null },
      personal_price: { ...claim, state: 'unavailable', amount: null },
      invalidation_reasons: ['evidence_revision_withdrawn'],
      sources: ['fixture'],
      unchecked_sources: [],
      coverage_reason: 'Synthetic declared scope.',
      gaps: [],
      exclusions: [],
    },
  ]
  const history = renderToStaticMarkup(
    <ProductContent
      candidate={candidate}
      tracking={[]}
      onSaved={async () => {}}
      view="history"
    />
  )
  expect(history).toContain('Historical assessment')
  expect(history).toContain('Why historical: Watch details or supporting evidence were corrected — kept on record, no longer used for pricing.')
  expect(history).toContain('title="Technical reasons: evidence_revision_withdrawn"')
})

// F10 — the retained-observations proof is visible without a button.
it('auto-loads retained observations and labels them as the nothing-overwritten proof', async () => {
  const fetch = vi.fn().mockResolvedValue({
    ok: true,
    json: async () => ({
      candidate_id: 'x',
      as_of: '2026-10-27T12:04:48Z',
      history_state: 'limited',
      coverage_reason: 'Limited retained history.',
      last_good: null,
      observations: [
        {
          id: 'obs-1',
          capture_id: 'cap-1',
          captured_at: '2026-10-27T12:00:36Z',
          observed_at: '2026-10-27T12:00:36Z',
          source: 'cex',
          acquisition_state: 'success',
          evidence_kind: 'synthetic',
          validity: 'invalidated',
          change: 'unchanged',
          duplicate_of: null,
          reasons: [],
          lineage: [],
          current_eligible: false,
          market_history_eligible: false,
          freshness: 'unvalidated',
          offer: {
            id: 'offer-1',
            revision: 1,
            authenticity: 'unknown',
            internal_health: 'unknown',
            binding_id: 'binding',
            binding_revision: 1,
            source: 'cex',
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
            cost_scenarios: [],
            coupons: [],
          },
          binding: {
            id: 'binding',
            revision: 1,
            configuration_id: 'watch',
            configuration_revision: 1,
            merchant_key: null,
            product_id: null,
            variation_id: null,
            resolution: { state: 'unresolved', values: {}, evidence_ids: [], issues: [] },
          },
          configuration: originalConfiguration,
          costs: [],
          policy_versions: {},
          dependencies: [],
          invalidations: [
            {
              id: 'inv-1',
              target: { kind: 'configuration', id: 'watch', revision: 1 },
              reason: 'Identity corrected: dial',
              recorded_at: '2026-10-27T12:04:48Z',
              correction_reference: '2c69ade4',
            },
          ],
        },
      ],
      attempts: [],
      gaps: [],
      usual_price: { state: 'unavailable', amount: null, reason: 'No calibration.' },
      savings: null,
      legacy_events_included: false,
    }),
  })
  vi.stubGlobal('fetch', fetch)
  await mount(<ObservationHistory candidateId="x" />)
  expect(container.querySelector('button')).toBeNull()
  expect(fetch).toHaveBeenCalled()
  expect(container.querySelector('caption').textContent).toContain('kept')
  expect(container.textContent).toContain('withdrawn after correction — kept on record')
  expect(container.textContent).not.toContain('invalidated · withdrawn')
})

// F9/F10 — the tracking editor must not read as “your target is blocked”
// when a target is already retained after a correction.
it('rewords the tracking block when a corrected target is already retained', async () => {
  const intent = {
    id: 1,
    revision: 1,
    candidate_id: 'x',
    capture_id: 'cap',
    configuration_id: 'watch',
    configuration_revision: 1,
    target_gbp: '60',
    notifications: { channels: ['webhook'] },
    invalidation_revision: 1,
    invalidation_reason: 'evidence_invalidated',
    assessment: {
      state: 'withheld',
      reasons: ['evidence_invalidated'],
      assessed_at: '2026-10-27T12:04:48Z',
      valid_until: '2026-10-27T13:04:48Z',
      delivered_gbp: null,
      policy_version: 'policy-v1',
    },
  }
  const status = renderToStaticMarkup(<TrackingStatus intent={intent} />)
  expect(status).toContain('target retained')
  expect(status).toContain('kept on record')
  expect(status).not.toContain('Evidence withdrawn · target retained')
  const candidate = correctedCandidate()
  const editor = renderToStaticMarkup(
    <ExactTrackingControl
      candidate={candidate}
      configuration={dialConfiguration}
      intent={intent}
      onSaved={async () => {}}
    />
  )
  expect(editor).toContain('Your saved target is retained')
  expect(editor).not.toContain('Exact identity must be resolved before starting exact tracking.')
})

// S5 residual 4 — the retained observation must not look like a conflicting
// current value beside the corrected hero.
it('separates retained observed details from the corrected values in Tracking', () => {
  const candidate = correctedCandidate()
  const intent = {
    id: 1,
    revision: 1,
    candidate_id: candidate.id,
    capture_id: candidate.capture_id,
    configuration_id: 'watch',
    configuration_revision: 1,
    target_gbp: '60',
    notifications: { channels: ['webhook'] },
    invalidation_revision: 1,
    invalidation_reason: 'evidence_invalidated',
    assessment: {
      state: 'withheld',
      reasons: ['evidence_invalidated'],
      assessed_at: '2026-10-27T12:04:48Z',
      valid_until: '2026-10-27T13:04:48Z',
      delivered_gbp: null,
      policy_version: 'policy-v1',
    },
  }
  const retainedConfiguration = {
    ...originalConfiguration,
    state: 'unresolved',
  }
  const editor = renderToStaticMarkup(
    <ExactTrackingControl
      candidate={candidate}
      configuration={retainedConfiguration}
      intent={intent}
      onSaved={async () => {}}
    />
  )
  expect(editor).toContain('Tracked watch — retained observation')
  expect(editor).toContain('Details as originally observed; kept unchanged as evidence.')
  expect(editor).toContain('Corrected details — waiting for fresh evidence')
  expect(editor).toContain('salmon (was: mint, as listed)')
  expect(editor).not.toContain('<h3>Tracked watch</h3>')
  expect(editor.indexOf('Tracked watch — retained observation')).toBeLessThan(editor.indexOf('>mint</dd>'))
  expect(editor.indexOf('>mint</dd>')).toBeLessThan(editor.indexOf('Corrected details — waiting for fresh evidence'))
})

// S5 residual 6 — equivalent API responses must not rotate the cards between
// loads while a buyer is following position-based guidance.
it('renders candidates in the same deterministic order for reversed API responses', async () => {
  const expected = [...captured.candidates]
    .sort((left, right) => left.title.localeCompare(right.title) || left.id.localeCompare(right.id))
    .map((candidate) => candidate.id)
  async function renderFeed(candidates) {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ ...captured, candidates }),
    }))
    await mount(
      <MemoryRouter initialEntries={['/discover']}>
        <Discovery />
      </MemoryRouter>
    )
    return Array.from(container.querySelectorAll('[data-candidate]')).map(
      (card) => card.getAttribute('data-candidate')
    )
  }

  expect(await renderFeed(captured.candidates)).toEqual(expected)
  await act(async () => root.unmount())
  root = createRoot(container)
  expect(await renderFeed([...captured.candidates].reverse())).toEqual(expected)
})
