// Validate the lead-only API contract once, before it reaches the buyer feed.
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
  if (!['http:', 'https:'].includes(url.protocol)) throw new Error('Invalid discovery link')
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

function parseCandidate(value: unknown) {
  const candidate = record(value), image = record(candidate.image)
  const total = record(candidate.public_delivered_total), usual = record(candidate.usual_price)
  if (candidate.alert_eligible !== false || candidate.savings !== null || total.amount !== null || usual.amount !== null) {
    throw new Error('Unsupported qualified discovery claim')
  }
  choice(candidate.identity_state, ['unresolved'])
  choice(total.state, ['unknown'])
  choice(usual.state, ['unavailable'])
  choice(image.kind, ['original_placeholder'])
  choice(image.permission, ['original_artwork'])
  return {
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
        state: choice(fit.state, ['unknown', 'unset']), reason: text(fit.reason) }
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
