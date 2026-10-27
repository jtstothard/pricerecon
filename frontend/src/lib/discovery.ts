import { parseTrackingList } from './tracking'
import { parseCorrection } from './corrections'
import { parsePriceAssessment } from './assessments'

// Validate capture-bound qualification states before they reach the buyer feed.
export function record(value: unknown): Record<string, unknown> {
  if (typeof value !== 'object' || value === null || Array.isArray(value)) throw new Error('Invalid discovery record')
  return Object.fromEntries(Object.entries(value))
}
export function text(value: unknown): string {
  if (typeof value !== 'string') throw new Error('Invalid discovery text')
  return value
}
export function list<T>(value: unknown, parse: (item: unknown) => T): T[] {
  if (!Array.isArray(value)) throw new Error('Invalid discovery list')
  return value.map(parse)
}
export function choice<const T extends readonly string[]>(value: unknown, allowed: T): T[number] {
  const found = allowed.find(item => item === value)
  if (found === undefined) throw new Error('Unsupported discovery state')
  return found
}
function amount(value: unknown): string | null {
  if (value === null) return null
  const result = text(value)
  if (!/^\d+(?:\.\d+)?(?:e[+-]?\d+)?$/i.test(result)) throw new Error('Invalid discovery amount')
  return result
}
export function integer(value: unknown): number {
  if (typeof value !== 'number' || !Number.isSafeInteger(value) || value < 0) throw new Error('Invalid discovery count')
  return value
}
export function date(value: unknown): string {
  const result = text(value)
  if (Number.isNaN(Date.parse(result))) throw new Error('Invalid discovery timestamp')
  return result
}
function link(value: unknown): string | null {
  if (value === null) return null
  const result = text(value)
  const url = new URL(result)
  if (!['http:', 'https:'].includes(url.protocol) || url.username || url.password) throw new Error('Invalid discovery link')
  return result
}

export function parsePreferences(value: unknown) {
  const profile = record(value), values = record(profile.values)
  return {
    revision: integer(profile.revision),
    values: {
      compact_max_width_mm: amount(values.compact_max_width_mm),
      compact_strength: choice(values.compact_strength, ['hard', 'soft']),
      colourful_dials: list(values.colourful_dials, text),
      colourful_strength: choice(values.colourful_strength, ['hard', 'soft']),
      budget_gbp: amount(values.budget_gbp),
      budget_strength: choice(values.budget_strength, ['hard', 'soft']),
    },
    interpretation: list(profile.interpretation, item => {
      const rule = record(item)
      return { field: choice(rule.field, ['compact', 'colourful', 'budget']),
        strength: choice(rule.strength, ['hard', 'soft', 'unset']), meaning: text(rule.meaning) }
    }),
  }
}

export function nullableText(value: unknown): string | null {
  return value === null ? null : text(value)
}
function resolution(value: unknown) {
  const result = record(value)
  return {
    state: choice(result.state, ['unresolved', 'supported', 'conflicting', 'rejected']),
    values: Object.fromEntries(Object.entries(record(result.values)).map(([key, value]) => [key, text(value)])),
    evidence_ids: list(result.evidence_ids, text),
    issues: list(result.issues, item => {
      const issue = record(item)
      return { field: text(issue.field), code: text(issue.code), evidence_ids: list(issue.evidence_ids, text) }
    }),
  }
}
export function configuration(value: unknown) {
  const config = record(value)
  return { ...resolution(config), id: text(config.id), revision: integer(config.revision), policy_version: text(config.policy_version) }
}
export function fieldEvidence(value: unknown) {
  const claim = record(value), context = record(claim.context)
  return {
    id: text(claim.id), subject: choice(claim.subject, ['configuration', 'selection', 'offer']),
    field: text(claim.field), value: text(claim.value), assertion_state: choice(claim.assertion_state, ['asserted', 'unknown', 'not_applicable']), issuer: text(claim.issuer),
    issuer_kind: choice(claim.issuer_kind, ['manufacturer', 'seller', 'visible_observation', 'ai_inference', 'search_lead', 'human_correction']),
    extractor: text(claim.extractor), extractor_kind: choice(claim.extractor_kind, ['structured_data', 'deterministic_dom', 'ai', 'human']),
    extractor_version: nullableText(claim.extractor_version), extractor_model: nullableText(claim.extractor_model),
    extraction_run_id: nullableText(claim.extraction_run_id), uncertainty: nullableText(claim.uncertainty),
    effective_at: claim.effective_at === null ? null : date(claim.effective_at),
    observed_at: claim.observed_at === null ? null : date(claim.observed_at),
    retrieved_at: date(claim.retrieved_at), capture_id: text(claim.capture_id), route: text(claim.route),
    pointer: link(claim.pointer), locator: text(claim.locator), retention: choice(claim.retention, ['minimal_fields', 'synthetic']),
    permission_reference: text(claim.permission_reference), derived_from: list(claim.derived_from, text),
    input_claim_ids: list(claim.input_claim_ids, text),
    context: { scope: choice(context.scope, ['configuration', 'selected_variation', 'generic_listing']),
      configuration_key: nullableText(context.configuration_key), merchant_key: nullableText(context.merchant_key),
      product_id: nullableText(context.product_id), variation_id: nullableText(context.variation_id),
      destination: nullableText(context.destination), currency: nullableText(context.currency), quantity: context.quantity === null ? null : integer(context.quantity) },
  }
}
export function binding(value: unknown) {
  const item = record(value)
  return { id: text(item.id), revision: integer(item.revision), configuration_id: text(item.configuration_id),
    configuration_revision: integer(item.configuration_revision), merchant_key: nullableText(item.merchant_key),
    product_id: nullableText(item.product_id), variation_id: nullableText(item.variation_id), resolution: resolution(item.resolution) }
}
function costContext(value: unknown) {
  const context = record(value)
  const stringFields = ['configuration_key', 'merchant_key', 'product_id', 'variation_id', 'seller', 'condition', 'purchase_mode',
    'destination_country', 'destination_nation', 'destination_region', 'shipping_service', 'seller_establishment',
    'goods_location', 'dispatch_country', 'customs_origin', 'dispatch_route', 'basket_id', 'consignment_id', 'grouping_basis',
    'purchase_scope', 'payment_method', 'display_currency', 'charge_currency', 'funding_currency']
  return { ...Object.fromEntries(stringFields.map(key => [key, nullableText(context[key])])),
    purchase_scope: context.purchase_scope === null ? null : choice(context.purchase_scope, ['standalone', 'allocated_share', 'whole_basket']),
    quantity: context.quantity === null ? null : integer(context.quantity),
    basket_members: list(context.basket_members, text), consignment_members: list(context.consignment_members, text) }
}
function costEvidence(value: unknown) {
  const claim = record(value)
  return { id: text(claim.id), issuer: text(claim.issuer),
    issuer_kind: choice(claim.issuer_kind, ['seller', 'carrier', 'payment_provider', 'customs', 'ai_inference', 'human_correction', 'search_lead']),
    extractor: text(claim.extractor), extractor_kind: choice(claim.extractor_kind, ['structured_data', 'deterministic_dom', 'ai', 'human']),
    observed_at: claim.observed_at === null ? null : date(claim.observed_at), retrieved_at: date(claim.retrieved_at),
    effective_at: claim.effective_at === null ? null : date(claim.effective_at), expires_at: claim.expires_at === null ? null : date(claim.expires_at),
    capture_id: text(claim.capture_id), route: text(claim.route), pointer: link(claim.pointer), locator: text(claim.locator),
    derived_from: list(claim.derived_from, text), input_claim_ids: list(claim.input_claim_ids, text),
    permission_reference: text(claim.permission_reference), retention: choice(claim.retention, ['minimal_fields', 'synthetic']),
    context: costContext(claim.context) }
}
function moneyMap(value: unknown) {
  return Object.fromEntries(Object.entries(record(value)).map(([currency, raw]) => {
    const parsed = amount(raw)
    if (parsed === null || !/^[A-Z]{3}$/.test(currency)) throw new Error('Invalid cost subtotal')
    return [currency, parsed]
  }))
}
export function costScenario(value: unknown) {
  const cost = record(value), total = cost.total === null ? null : record(cost.total)
  const state = choice(cost.state, ['verified_at_observation', 'conditional', 'unknown'])
  if ((state === 'unknown') !== (total === null)) throw new Error('Inconsistent cost state')
  choice(cost.freshness, ['unvalidated'])
  return { id: text(cost.id), revision: integer(cost.revision), policy_version: text(cost.policy_version),
    offer_id: text(cost.offer_id), offer_revision: integer(cost.offer_revision), binding_id: text(cost.binding_id),
    binding_revision: integer(cost.binding_revision), configuration_id: text(cost.configuration_id), configuration_revision: integer(cost.configuration_revision),
    key: text(cost.key), kind: choice(cost.kind, ['public_no_coupon', 'public_coupon', 'personal', 'payment', 'cashback']), state,
    captured_at: date(cost.captured_at), context: costContext(cost.context), context_evidence: list(cost.context_evidence, costEvidence),
    assumptions: list(cost.assumptions, text), issues: list(cost.issues, text),
    withdrawn: cost.withdrawn === true,
    historical_total: cost.historical_total === null ? null : (() => { const historical = record(cost.historical_total); return { amount: amount(historical.amount), currency: text(historical.currency) } })(),
    total: total === null ? null : { amount: amount(total.amount), currency: text(total.currency) },
    known_subtotal: moneyMap(cost.known_subtotal), merchant_payable: moneyMap(cost.merchant_payable), additional_liabilities: moneyMap(cost.additional_liabilities),
    components: list(cost.components, raw => {
      const part = record(raw)
      return { kind: choice(part.kind, ['basket_other_items', 'item', 'shipping', 'merchant_tax', 'merchant_fee', 'import_tax', 'duty', 'carrier_fee', 'payment_fee']),
        state: choice(part.state, ['observed', 'derived', 'conditional', 'unknown', 'conflicting', 'not_applicable']),
        amount: amount(part.amount), currency: nullableText(part.currency), basis: choice(part.basis, ['per_unit', 'scenario']),
        included_in: nullableText(part.included_in), payer: text(part.payer), collector: text(part.collector), reason: text(part.reason),
        assumptions: list(part.assumptions, text), evidence: list(part.evidence, costEvidence) }
    }),
    benefits: list(cost.benefits, raw => {
      const benefit = record(raw)
      choice(benefit.accounting, ['excluded_from_payable'])
      return { kind: choice(benefit.kind, ['personal', 'payment', 'cashback']), state: choice(benefit.state, ['conditional', 'unknown', 'conflicting']),
        amount: amount(benefit.amount), currency: nullableText(benefit.currency), reason: text(benefit.reason), evidence: list(benefit.evidence, costEvidence) }
    }),
    fx_quotes: list(cost.fx_quotes, raw => {
      const fx = record(raw)
      if (typeof fx.spread_included !== 'boolean' && fx.spread_included !== null) throw new Error('Invalid FX spread state')
      return { purpose: choice(fx.purpose, ['buyer_payment', 'customs_valuation']), from_currency: text(fx.from_currency), to_currency: text(fx.to_currency),
        rate: amount(fx.rate), direction: choice(fx.direction, ['target_per_source']), converter: text(fx.converter), spread_included: fx.spread_included,
        quantum: amount(fx.quantum), rounding: choice(fx.rounding, ['ROUND_HALF_UP', 'ROUND_HALF_EVEN', 'ROUND_DOWN', 'ROUND_UP']),
        state: choice(fx.state, ['observed', 'conditional', 'unknown', 'conflicting']), assumptions: list(fx.assumptions, text), evidence: list(fx.evidence, costEvidence) }
    }) }
}

export function offer(value: unknown) {
  const item = record(value)
  choice(item.authenticity, ['unknown']); choice(item.internal_health, ['unknown'])
  return { id: text(item.id), revision: integer(item.revision), binding_id: text(item.binding_id),
    binding_revision: integer(item.binding_revision), source: text(item.source), source_listing_id: text(item.source_listing_id),
    seller: nullableText(item.seller), condition: nullableText(item.condition),
    condition_description: nullableText(item.condition_description), visible_condition: nullableText(item.visible_condition),
    quantity: item.quantity === null ? null : integer(item.quantity), availability: nullableText(item.availability),
    purchase_mode: nullableText(item.purchase_mode), item_price: amount(item.item_price), currency: nullableText(item.currency),
    destination: nullableText(item.destination), qualification: resolution(item.qualification), comparison: resolution(item.comparison),
    comparison_cohort: nullableText(item.comparison_cohort), policy_version: text(item.policy_version),
    evidence: list(item.evidence, fieldEvidence), cost_scenarios: list(item.cost_scenarios, costScenario),
    coupons: list(item.coupons, coupon) }
}

function coupon(value: unknown) {
  const item = record(value), terms = item.terms === null ? null : record(item.terms)
  const eligibility = item.eligibility === null ? null : record(item.eligibility)
  const application = item.application === null ? null : record(item.application)
  const state = choice(item.state, ['unverified_opportunity', 'conditional_eligibility', 'applicable_not_reproduced', 'reproduced_at_observation', 'rejected', 'invalidated'])
  const result = item.resulting_cost === null ? null : costScenario(item.resulting_cost)
  if ((state === 'reproduced_at_observation') !== (result !== null)) throw new Error('Inconsistent coupon result')
  const requirement = (raw: unknown) => choice(raw, ['required', 'not_required', 'unknown'])
  const nullableDate = (raw: unknown) => raw === null ? null : date(raw)
  const nullableCount = (raw: unknown) => raw === null ? null : integer(raw)
  const boolean = (raw: unknown) => { if (typeof raw !== 'boolean') throw new Error('Invalid coupon boolean'); return raw }
  const nullableBoolean = (raw: unknown) => raw === null ? null : boolean(raw)
  return {
    id: text(item.id), revision: integer(item.revision), label: text(item.label), state,
    category: choice(item.category, ['public', 'personal', 'payment', 'cashback']),
    applicability: choice(item.applicability, ['unknown', 'supported', 'conditional', 'rejected']),
    lineage: choice(item.lineage, ['observation_only', 'superseded']),
    offer_revision: integer(item.offer_revision), binding_revision: integer(item.binding_revision),
    configuration_revision: integer(item.configuration_revision), policy_version: text(item.policy_version),
    identity_policy_version: text(item.identity_policy_version), captured_at: date(item.captured_at),
    context: costContext(item.context), issues: list(item.issues, text),
    opportunity_evidence: list(item.opportunity_evidence, costEvidence),
    terms: terms === null ? null : {
      literal: text(terms.literal), codes: list(terms.codes, text), starts_at: nullableDate(terms.starts_at),
      ends_at: nullableDate(terms.ends_at), time_zone_literal: nullableText(terms.time_zone_literal),
      start_inclusive: nullableBoolean(terms.start_inclusive), end_inclusive: nullableBoolean(terms.end_inclusive),
      minimum_spend: amount(terms.minimum_spend), minimum_currency: nullableText(terms.minimum_currency),
      minimum_inclusive: nullableBoolean(terms.minimum_inclusive), minimum_basis: nullableText(terms.minimum_basis),
      min_quantity: nullableCount(terms.min_quantity), max_quantity: nullableCount(terms.max_quantity),
      channel: choice(terms.channel, ['web', 'app', 'any', 'unknown']), new_customer: requirement(terms.new_customer),
      membership: requirement(terms.membership), redemption: choice(terms.redemption, ['public_no_activation', 'conditional', 'unknown']),
      compatibility: choice(terms.compatibility, ['supported', 'forbidden', 'conditional', 'unknown']),
      combination_rule: nullableText(terms.combination_rule), evidence: list(terms.evidence, costEvidence),
      compatibility_evidence: list(terms.compatibility_evidence, costEvidence),
    },
    eligibility: eligibility === null ? null : {
      channel: choice(eligibility.channel, ['web', 'app', 'unknown']), new_customer: requirement(eligibility.new_customer),
      membership: requirement(eligibility.membership), eligible_base: amount(eligibility.eligible_base), currency: text(eligibility.currency),
      terms_satisfied: boolean(eligibility.terms_satisfied), reason: text(eligibility.reason),
      eligible_members: list(eligibility.eligible_members, text), excluded_members: list(eligibility.excluded_members, text),
      evidence: list(eligibility.evidence, costEvidence),
    },
    application: application === null ? null : {
      result: choice(application.result, ['applied', 'rejected', 'unknown']), applied_codes: list(application.applied_codes, text),
      other_promotions: list(application.other_promotions, text), before_total: amount(application.before_total),
      quoted_total: amount(application.quoted_total), currency: text(application.currency),
      selected_member: text(application.selected_member), terms_fingerprint: text(application.terms_fingerprint),
      evidence: list(application.evidence, costEvidence),
      lines: list(application.lines, raw => { const line = record(raw); return { member: text(line.member), quantity: integer(line.quantity),
        before_item_total: amount(line.before_item_total), after_item_total: amount(line.after_item_total), currency: text(line.currency),
        eligible: boolean(line.eligible), applied_codes: list(line.applied_codes, text), evidence: list(line.evidence, costEvidence) } }),
    },
    resulting_cost: result,
    historical_resulting_cost: item.historical_resulting_cost === null ? null : costScenario(item.historical_resulting_cost),
  }
}

export type DiscoveryCoupon = ReturnType<typeof coupon>

function parseCandidate(value: unknown) {
  const candidate = record(value), image = record(candidate.image)
  const total = record(candidate.public_delivered_total), usual = record(candidate.usual_price)
  if (candidate.alert_eligible !== false || candidate.savings !== null || usual.amount !== null) {
    throw new Error('Unsupported qualified discovery claim')
  }
  const identity_state = choice(candidate.identity_state, ['unresolved', 'supported', 'conflicting', 'rejected'])
  const totalState = choice(total.state, ['verified_at_observation', 'conditional', 'unknown'])
  const totalAmount = amount(total.amount)
  if ((totalState === 'unknown') !== (totalAmount === null)) throw new Error('Inconsistent public total')
  choice(usual.state, ['unavailable'])
  choice(image.kind, ['original_placeholder'])
  choice(image.permission, ['original_artwork'])
  return {
    identity_state, configuration: configuration(candidate.configuration),
    price_assessments: candidate.price_assessments === undefined ? [] : list(candidate.price_assessments, parsePriceAssessment),
    configurations: list(candidate.configurations, configuration),
    bindings: list(candidate.bindings, binding), offers: list(candidate.offers, offer),
    id: text(candidate.id), title: text(candidate.title), source: text(candidate.source),
    reported_source: text(candidate.reported_source),
    origin: choice(candidate.origin, ['category_discovery']), query: text(candidate.query),
    source_listing_id: text(candidate.source_listing_id), url: link(candidate.url),
    capture_id: text(candidate.capture_id), captured_at: date(candidate.captured_at),
    advertised_item_price: amount(candidate.advertised_item_price),
    reported_currency: candidate.reported_currency === null ? null : text(candidate.reported_currency),
    price_caveat: text(candidate.price_caveat),
    image: { attribution: text(image.attribution), provenance: text(image.provenance) },
    public_total: { state: totalState, amount: totalAmount, currency: nullableText(total.currency), scenario_id: nullableText(total.scenario_id), scenario_revision: total.scenario_revision === null ? null : integer(total.scenario_revision) },
    total_reason: text(total.reason), usual_reason: text(usual.reason),
    corrections: list(candidate.corrections, parseCorrection),
    missing_data: list(candidate.missing_data, text),
    preference_fit: list(candidate.preference_fit, item => {
      const fit = record(item)
      return { field: choice(fit.field, ['compact', 'colourful', 'budget']),
        strength: choice(fit.strength, ['hard', 'soft', 'unset']),
        state: choice(fit.state, ['unknown', 'unset', 'fits', 'outside']), reason: text(fit.reason) }
    }),
    evidence: list(candidate.evidence, item => {
      const evidence = record(item)
      return { id: text(evidence.id), field: choice(evidence.field, ['title', 'advertised_item_price']),
        value: text(evidence.value), issuer: text(evidence.issuer), issuer_kind: text(evidence.issuer_kind),
        extractor: text(evidence.extractor), captured_at: date(evidence.captured_at),
        source_observed_at: evidence.source_observed_at === null ? null : date(evidence.source_observed_at),
        capture_id: text(evidence.capture_id), route: text(evidence.route), pointer: link(evidence.pointer),
        validity_context: text(evidence.validity_context), derived_from: list(evidence.derived_from, text) }
    }),
  }
}

export function parseDiscoveryFeed(value: unknown) {
  const feed = record(value)
  choice(feed.collection_state, ['staged'])
  return {
    collection_reason: text(feed.collection_reason), preferences: parsePreferences(feed.preferences),
    candidates: list(feed.candidates, parseCandidate),
    tracking: parseTrackingList(feed.tracking),
    captures: list(feed.captures, item => {
      const capture = record(item), request = record(capture.request), admission = record(capture.admission)
      return { capture_id: text(capture.capture_id), captured_at: date(capture.captured_at),
        query: text(request.query), mode: choice(admission.mode, ['staged', 'offline_verification']),
        outcomes: list(capture.outcomes, raw => {
          const outcome = record(raw)
          return { source: text(outcome.source),
            state: choice(outcome.state, ['success', 'success_empty', 'partial', 'cache_reuse', 'blocked', 'capped', 'failed', 'not_attempted']),
            listing_count: integer(outcome.listing_count),
            reason: outcome.reason === null ? null : text(outcome.reason) }
        }) }
    }),
  }
}

export type DiscoveryFeed = ReturnType<typeof parseDiscoveryFeed>
export type PreferenceProfile = ReturnType<typeof parsePreferences>
export type DiscoveryCandidate = DiscoveryFeed['candidates'][number]

export async function loadDiscovery(signal?: AbortSignal): Promise<DiscoveryFeed> {
  const response = await fetch('/api/discovery/watches', { signal })
  if (!response.ok) throw new Error('Discovery could not load. Try reloading the feed.')
  const body: unknown = await response.json()
  return parseDiscoveryFeed(body)
}

export async function savePreferences(profile: PreferenceProfile): Promise<PreferenceProfile> {
  const response = await fetch('/api/discovery/watches/preferences', {
    method: 'PUT', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ expected_revision: profile.revision, values: profile.values }),
  })
  if (response.status === 409) throw new Error('Preferences changed in another window. Reload the feed before saving.')
  if (!response.ok) throw new Error('Preferences were not saved. Check your values and try again.')
  const body: unknown = await response.json()
  return parsePreferences(body)
}
