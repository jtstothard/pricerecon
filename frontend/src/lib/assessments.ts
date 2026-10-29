import { choice, date, integer, list, nullableText, record, text } from './discovery'

function claim(value: unknown) {
  const item = record(value)
  const state = choice(item.state, ['supported', 'unavailable', 'historical', 'invalidated'])
  const amount = nullableText(item.amount)
  if (amount !== null && !/^\d+(?:\.\d+)?$/.test(amount)) throw new Error('Invalid assessment amount')
  if (state === 'supported' && amount === null) throw new Error('Missing qualified amount')
  return { state, amount, reason: text(item.reason), observation_count: integer(item.observation_count),
    // Envelope provenance: fail closed like every other parsed field — a
    // payload without an explicit marker is refused rather than read as live.
    synthetic: choice(String(item.synthetic), ['true', 'false']) === 'true',
    paths: list(item.paths, value => {
      const path = record(value)
      return { observed_at: date(path.observed_at), offer_key: text(path.offer_key),
        scenario_kind: choice(path.scenario_kind, ['public_no_coupon', 'public_coupon']),
        evidence_ids: list(path.evidence_ids, text),
        synthetic: choice(String(path.synthetic), ['true', 'false']) === 'true',
        dependencies: list(path.dependencies, value => {
          const ref = record(value)
          return { kind: text(ref.kind), id: text(ref.id), revision: integer(ref.revision) }
        }) }
    }) }
}

export function parsePriceAssessment(value: unknown) {
  const item = record(value), policy = record(item.policy), coverage = record(item.coverage)
  if (typeof item.historical !== 'boolean' || item.savings !== null) throw new Error('Invalid assessment claim')
  return { id: text(item.id), revision: integer(item.revision), historical: item.historical,
    assessed_at: date(item.assessed_at), method: text(item.method),
    cohort: Object.fromEntries(Object.entries(record(item.cohort)).map(([key, value]) => [key, text(value)])),
    policy_version: text(policy.version), policy_fingerprint: text(item.policy_fingerprint),
    window_start: date(item.window_start), window_end: date(item.window_end),
    max_age: integer(policy.max_evidence_age_seconds),
    allowed_scenarios: list(policy.allowed_scenario_kinds, text),
    current_best: claim(item.current_best), observed_low: claim(item.observed_low),
    usual_price: claim(item.usual_price), personal_price: claim(item.personal_price),
    invalidation_reasons: list(item.invalidation_reasons, text),
    sources: list(coverage.sources, text), unchecked_sources: list(coverage.unchecked_sources, text),
    coverage_reason: text(coverage.reason),
    gaps: list(coverage.gaps, value => { const gap = record(value); return { start: date(gap.start), end: date(gap.end), reason: text(gap.reason) } }),
    exclusions: list(item.exclusions, value => { const excluded = record(value); return {
      observation_id: text(excluded.observation_id), scope: text(excluded.scope), reasons: list(excluded.reasons, text) } }),
  }
}

export type PriceAssessment = ReturnType<typeof parsePriceAssessment>
