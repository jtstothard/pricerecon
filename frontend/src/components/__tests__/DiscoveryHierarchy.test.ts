import { createElement } from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { expect, it } from 'vitest'
import { Candidate } from '../../pages/Discovery'
import { parseDiscoveryFeed } from '../../lib/discovery'
import captured from './image-feed.json'

it('offers compact buyer groups with conditions before technical evidence', () => {
  const candidate = parseDiscoveryFeed(captured).candidates[0]
  const html = renderToStaticMarkup(createElement(Candidate, { candidate, tracking: [], onSaved: async () => {} }))
  expect(html).not.toContain('<summary>Price and evidence</summary>')
  for (const label of ['Price breakdown', 'Watch details', 'Price history', 'Sources', 'Technical evidence']) {
    expect(html).toContain(`<summary>${label}`)
  }
  expect(html.indexOf(candidate.total_reason)).toBeLessThan(html.indexOf('<summary>Technical evidence: capture lineage'))
  expect(html).toContain(candidate.missing_data.join('; '))
  expect(html).not.toMatch(/<details[^>]*\sopen/)
})

import { PriceAssessments } from '../discovery/PriceAssessments'
import type { PriceAssessment } from '../../lib/assessments'

it('shows comparison outcome and gaps before optional method and revision details', () => {
  const price: PriceAssessment['current_best'] = { state: 'invalidated', amount: '65.00', reason: 'Identity corrected', observation_count: 1, paths: [{ observed_at: '2026-10-27T12:00:00Z', scenario_kind: 'public_no_coupon', synthetic: true, offer_key: 'technical-offer-key', evidence_ids: ['claim-1'], dependencies: [] }] }
  const assessment: PriceAssessment = {
    id: 'assessment-1', revision: 8, historical: true, assessed_at: '2026-10-27T12:00:00Z',
    cohort: { condition: 'new', quantity: '1' }, invalidation_reasons: ['identity_corrected'],
    current_best: price, observed_low: price, window_start: '2026-10-26T12:00:00Z', window_end: '2026-10-27T12:00:00Z',
    usual_price: { ...price, reason: 'Insufficient history' }, personal_price: { ...price, reason: 'Eligibility unknown' },
    sources: ['shop'], unchecked_sources: ['marketplace'], coverage_reason: 'Only one source checked',
    method: 'technical-method', policy_version: 'policy-v1', policy_fingerprint: 'fingerprint', max_age: 3600,
    allowed_scenarios: ['public_no_coupon'], gaps: [], exclusions: [],
  }
  const html = renderToStaticMarkup(createElement(PriceAssessments, { assessments: [assessment] }))
  expect(html).toContain('Historical assessment')
  expect(html).toContain('unavailable as a current buying claim')
  expect(html).toContain('Synthetic verification data')
  expect(html).toContain('marketplace')
  expect(html).toContain('<summary>Technical evidence</summary>')
  expect(html.indexOf('Only one source checked')).toBeLessThan(html.indexOf('technical-method'))
  expect(html).not.toMatch(/<summary>[^<]*revision 8/)
})

import { SourceCoverage } from '../discovery/SourceCoverage'
it('keeps source gaps ahead of optional acquisition provenance', () => {
  const feed = parseDiscoveryFeed(captured)
  feed.cohort_gaps = ['Marketplace was not checked']
  const html = renderToStaticMarkup(createElement(SourceCoverage, { feed }))
  expect(html).toContain('<summary>Sources and gaps')
  for (const gap of feed.cohort_gaps) expect(html).toContain(gap)
})

it.each(['unknown', 'conditional', 'verified_at_observation'] as const)('preserves %s costs, liabilities and excluded benefits in the expanded breakdown', state => {
  const candidate = parseDiscoveryFeed(captured).candidates[0]
  candidate.offers = [{
    id: 'offer', revision: 1, binding_id: 'binding', binding_revision: 1, source: 'fixture', source_listing_id: 'listing',
    source_evidence: null, seller: 'Fixture seller', condition: 'new', condition_description: null, visible_condition: null,
    quantity: 1, availability: 'unknown', purchase_mode: 'buy_now', item_price: '50.00', currency: 'GBP', destination: 'UK',
    qualification: { state: 'unresolved', values: {}, evidence_ids: [], issues: [] }, comparison: { state: 'unresolved', values: {}, evidence_ids: [], issues: [] }, comparison_cohort: null,
    policy_version: 'offer-policy', evidence: [], coupons: [], cost_scenarios: [{
      id: 'cost', revision: 3, policy_version: 'technical-cost-policy', offer_id: 'offer', offer_revision: 1, binding_id: 'binding', binding_revision: 1,
      configuration_id: 'watch', configuration_revision: 1, key: 'cost-key', kind: 'public_no_coupon', state,
      captured_at: '2026-10-27T12:00:00Z', context: { purchase_scope: 'standalone', quantity: 1, basket_members: [], consignment_members: [] },
      context_evidence: [], assumptions: ['UK address required'], issues: ['Carrier fee unconfirmed'], withdrawn: true,
      historical_total: { currency: 'GBP', amount: '60.00' }, total: state === 'unknown' ? null : { currency: 'GBP', amount: '60.00' },
      known_subtotal: { GBP: '50.00' }, merchant_payable: { GBP: '50.00' }, additional_liabilities: {}, components: [], fx_quotes: [],
      benefits: [{ kind: 'cashback', state: 'conditional', currency: 'GBP', amount: '5.00', reason: 'Approval required', evidence: [] }],
    }],
  }]
  const html = renderToStaticMarkup(createElement(Candidate, { candidate, tracking: [], onSaved: async () => {} }))
  expect(html).toContain('Historical cost withdrawn')
  expect(html).toContain('GBP 60.00')
  expect(html).toContain('Carrier fee unconfirmed')
  expect(html).toContain('UK address required')
  expect(html).toContain('Benefits excluded from payable')
  expect(html).toContain('Approval required')
  expect(html).toContain('<dt>Merchant payable</dt><dd>GBP 50.00')
  expect(html.indexOf('Carrier fee unconfirmed')).toBeLessThan(html.indexOf('technical-cost-policy'))
  if (state === 'unknown') expect(html).toContain('incomplete, not a delivered total')
})
