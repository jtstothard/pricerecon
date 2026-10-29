import { createElement } from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { expect, it } from 'vitest'
import { Candidate, ProductContent } from '../../pages/Discovery'
import { parseDiscoveryFeed } from '../../lib/discovery'
import captured from './image-feed.json'

it('separates comparison from flat product sections', () => {
  const candidate = parseDiscoveryFeed(captured).candidates[0]
  const html = renderToStaticMarkup(
    createElement(Candidate, { candidate, tracking: [], onSaved: async () => {} })
  )
  expect(html).toContain('Product details')
  expect(html).not.toContain('<details')
  const detail = renderToStaticMarkup(
    createElement(ProductContent, {
      candidate,
      tracking: [],
      onSaved: async () => {},
      view: 'costs',
    })
  )
  expect(detail).toContain(candidate.total_reason)
  expect(detail).toContain(candidate.missing_data.join('; '))
  expect(detail).not.toContain('<details')
})

import { PriceAssessments } from '../discovery/PriceAssessments'
import type { PriceAssessment } from '../../lib/assessments'

it('shows comparison outcome and gaps before optional method and revision details', () => {
  const price: PriceAssessment['current_best'] = {
    state: 'invalidated',
    amount: '65.00',
    reason: 'Identity corrected',
    observation_count: 1,
    synthetic: true,
    paths: [
      {
        observed_at: '2026-10-27T12:00:00Z',
        scenario_kind: 'public_no_coupon',
        synthetic: true,
        offer_key: 'technical-offer-key',
        evidence_ids: ['claim-1'],
        dependencies: [],
      },
    ],
  }
  const assessment: PriceAssessment = {
    id: 'assessment-1',
    revision: 8,
    historical: true,
    assessed_at: '2026-10-27T12:00:00Z',
    cohort: { condition: 'new', quantity: '1' },
    invalidation_reasons: ['identity_corrected'],
    current_best: price,
    observed_low: price,
    window_start: '2026-10-26T12:00:00Z',
    window_end: '2026-10-27T12:00:00Z',
    usual_price: { ...price, reason: 'Insufficient history' },
    personal_price: { ...price, reason: 'Eligibility unknown' },
    sources: ['shop'],
    unchecked_sources: ['marketplace'],
    coverage_reason: 'Only one source checked',
    method: 'technical-method',
    policy_version: 'policy-v1',
    policy_fingerprint: 'fingerprint',
    max_age: 3600,
    allowed_scenarios: ['public_no_coupon'],
    gaps: [],
    exclusions: [],
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

import { parsePriceAssessment } from '../../lib/assessments'

function capturedClaim(synthetic: boolean, pathSynthetic: boolean) {
  return {
    state: 'supported',
    amount: '45.10',
    reason: 'Lowest verified total among the offers checked.',
    observation_count: 1,
    synthetic,
    paths: [
      {
        observed_at: '2026-10-27T12:00:00Z',
        scenario_kind: 'public_no_coupon',
        synthetic: pathSynthetic,
        offer_key: 'offer-key',
        evidence_ids: ['claim-1'],
        dependencies: [],
      },
    ],
  }
}

function capturedAssessment(currentBest: object) {
  return {
    id: 'assessment-envelope',
    revision: 1,
    historical: false,
    savings: null,
    assessed_at: '2026-10-27T12:00:00Z',
    cohort: { condition: 'new', quantity: '1' },
    invalidation_reasons: [],
    current_best: currentBest,
    observed_low: capturedClaim(false, false),
    usual_price: { state: 'unavailable', amount: null, reason: 'No calibration.', observation_count: 0, synthetic: false, paths: [] },
    personal_price: { state: 'unavailable', amount: null, reason: 'No personal history.', observation_count: 0, synthetic: false, paths: [] },
    window_start: '2026-10-26T12:00:00Z',
    window_end: '2026-10-27T12:00:00Z',
    policy: {
      version: 'policy-v1',
      max_evidence_age_seconds: 3600,
      allowed_scenario_kinds: ['public_no_coupon'],
    },
    coverage: { sources: ['shop'], unchecked_sources: [], gaps: [], reason: 'Declared scope' },
    method: 'qualified-payable-minimum-v1',
    policy_fingerprint: 'fingerprint',
    gaps: [],
    exclusions: [],
  }
}

it('carries the envelope synthetic marker through the parser and warns beside the amount', () => {
  const assessment = parsePriceAssessment(capturedAssessment(capturedClaim(true, false)))
  expect(assessment.current_best.synthetic).toBe(true)
  // The envelope warning must render even when no individual path warns.
  expect(assessment.current_best.paths[0].synthetic).toBe(false)
  const html = renderToStaticMarkup(
    createElement(PriceAssessments, { assessments: [assessment] })
  )
  expect(html).toContain('decided by fixture evidence, not a live market fact')
  expect(html).not.toContain('no real market history')
})

it('keeps a live envelope claim live and refuses a payload without an explicit marker', () => {
  const live = parsePriceAssessment(capturedAssessment(capturedClaim(false, false)))
  expect(live.current_best.synthetic).toBe(false)
  const unmarked = capturedAssessment(capturedClaim(true, false))
  delete (unmarked.current_best as Record<string, unknown>).synthetic
  expect(() => parsePriceAssessment(unmarked)).toThrow()
})

import { SourceCoverage } from '../discovery/SourceCoverage'
it('keeps source gaps ahead of optional acquisition provenance', () => {
  const feed = parseDiscoveryFeed(captured)
  feed.cohort_gaps = ['Marketplace was not checked']
  const html = renderToStaticMarkup(createElement(SourceCoverage, { feed }))
  expect(html).toContain('<h3>Sources and gaps')
  for (const gap of feed.cohort_gaps) expect(html).toContain(gap)
})

it.each(['unknown', 'conditional', 'verified_at_observation'] as const)(
  'preserves %s costs, liabilities and excluded benefits in the expanded breakdown',
  (state) => {
    const candidate = parseDiscoveryFeed(captured).candidates[0]
    candidate.offers = [
      {
        id: 'offer',
        revision: 1,
        binding_id: 'binding',
        binding_revision: 1,
        source: 'fixture',
        source_listing_id: 'listing',
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
        cost_scenarios: [
          {
            id: 'cost',
            revision: 3,
            policy_version: 'technical-cost-policy',
            offer_id: 'offer',
            offer_revision: 1,
            binding_id: 'binding',
            binding_revision: 1,
            configuration_id: 'watch',
            configuration_revision: 1,
            key: 'cost-key',
            kind: 'public_no_coupon',
            state,
            captured_at: '2026-10-27T12:00:00Z',
            context: {
              purchase_scope: 'standalone',
              quantity: 1,
              basket_members: [],
              consignment_members: [],
            },
            context_evidence: [],
            assumptions: ['UK address required'],
            issues: ['Carrier fee unconfirmed'],
            withdrawn: true,
            historical_total: { currency: 'GBP', amount: '60.00' },
            total: state === 'unknown' ? null : { currency: 'GBP', amount: '60.00' },
            known_subtotal: { GBP: '50.00' },
            merchant_payable: { GBP: '50.00' },
            additional_liabilities: {},
            components: [],
            fx_quotes: [],
            benefits: [
              {
                kind: 'cashback',
                state: 'conditional',
                currency: 'GBP',
                amount: '5.00',
                reason: 'Approval required',
                evidence: [],
              },
            ],
          },
        ],
      },
    ]
    const html = renderToStaticMarkup(
      createElement(ProductContent, {
        candidate,
        tracking: [],
        onSaved: async () => {},
        view: 'costs',
      })
    )
    expect(html).toContain('Historical cost withdrawn')
    const technical = renderToStaticMarkup(
      createElement(ProductContent, {
        candidate,
        tracking: [],
        onSaved: async () => {},
        view: 'technical',
      })
    )
    expect(technical).toContain('60.00')
    expect(html).toContain('Carrier fee unconfirmed')
    expect(html).toContain('UK address required')
    expect(html).toContain('Benefits excluded from payable')
    expect(html).toContain('Approval required')
    expect(html).toContain('<dt>Merchant payable</dt><dd>GBP 50.00')
    expect(technical).toContain('technical-cost-policy')
    expect(html).not.toContain('technical-cost-policy')
    if (state === 'unknown') expect(html).toContain('incomplete, not a delivered total')
  }
)
