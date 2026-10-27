// Validate capture-bound qualification states before they reach the buyer feed.
function record(value: unknown): Record<string, unknown> {
  if (typeof value !== 'object' || value === null || Array.isArray(value)) throw new Error('Invalid discovery record')
  return Object.fromEntries(Object.entries(value))
}
function text(value: unknown): string {
  if (typeof value !== 'string') throw new Error('Invalid discovery text')
  return value
}
function list<T>(value: unknown, parse: (item: unknown) => T): T[] {
  if (!Array.isArray(value)) throw new Error('Invalid discovery list')
  return value.map(parse)
}
function choice<const T extends readonly string[]>(value: unknown, allowed: T): T[number] {
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
function integer(value: unknown): number {
  if (typeof value !== 'number' || !Number.isSafeInteger(value) || value < 0) throw new Error('Invalid discovery count')
  return value
}
function date(value: unknown): string {
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

function nullableText(value: unknown): string | null {
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
function configuration(value: unknown) {
  const config = record(value)
  return { ...resolution(config), id: text(config.id), revision: integer(config.revision), policy_version: text(config.policy_version) }
}
function fieldEvidence(value: unknown) {
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
function binding(value: unknown) {
  const item = record(value)
  return { id: text(item.id), revision: integer(item.revision), configuration_id: text(item.configuration_id),
    configuration_revision: integer(item.configuration_revision), merchant_key: nullableText(item.merchant_key),
    product_id: nullableText(item.product_id), variation_id: nullableText(item.variation_id), resolution: resolution(item.resolution) }
}
function offer(value: unknown) {
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
    evidence: list(item.evidence, fieldEvidence) }
}

function parseCandidate(value: unknown) {
  const candidate = record(value), image = record(candidate.image)
  const total = record(candidate.public_delivered_total), usual = record(candidate.usual_price)
  if (candidate.alert_eligible !== false || candidate.savings !== null || total.amount !== null || usual.amount !== null) {
    throw new Error('Unsupported qualified discovery claim')
  }
  const identity_state = choice(candidate.identity_state, ['unresolved', 'supported', 'conflicting', 'rejected'])
  choice(total.state, ['unknown'])
  choice(usual.state, ['unavailable'])
  choice(image.kind, ['original_placeholder'])
  choice(image.permission, ['original_artwork'])
  return {
    identity_state, configuration: configuration(candidate.configuration),
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
    total_reason: text(total.reason), usual_reason: text(usual.reason),
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
    captures: list(feed.captures, item => {
      const capture = record(item), request = record(capture.request), admission = record(capture.admission)
      return { capture_id: text(capture.capture_id), captured_at: date(capture.captured_at),
        query: text(request.query), mode: choice(admission.mode, ['staged', 'offline_verification']),
        outcomes: list(capture.outcomes, raw => {
          const outcome = record(raw)
          return { source: text(outcome.source),
            state: choice(outcome.state, ['success', 'success_empty', 'blocked', 'capped', 'failed', 'not_attempted']),
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
