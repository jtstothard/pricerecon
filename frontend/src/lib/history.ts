import { record, text, list, choice, integer, date, nullableText, offer, binding, configuration, costScenario } from './discovery'

function lastGood(value: unknown) {
  if (value === null) return null
  const item = record(value)
  if (typeof item.age_seconds !== 'number' || !Number.isFinite(item.age_seconds) || item.age_seconds < 0 || item.current_eligible !== false) throw new Error('Invalid retained evidence age')
  choice(item.freshness, ['unvalidated'])
  return { observation_id: text(item.observation_id), captured_at: date(item.captured_at), observed_at: date(item.observed_at), age_seconds: item.age_seconds }
}
function reference(value: unknown) {
  const item = record(value), revision = integer(item.revision)
  if (revision === 0) throw new Error('Invalid evidence revision')
  return { kind: choice(item.kind, ['configuration', 'binding', 'offer', 'cost']), id: text(item.id), revision }
}
export function parseHistory(value: unknown) {
  const data = record(value), usual = record(data.usual_price)
  if (data.legacy_events_included !== false || data.savings !== null || usual.amount !== null) throw new Error('Unsupported history claim')
  choice(usual.state, ['unavailable'])
  return { candidate_id: text(data.candidate_id), as_of: date(data.as_of),
    history_state: choice(data.history_state, ['limited', 'unavailable']),
    coverage_reason: text(data.coverage_reason), last_good: lastGood(data.last_good),
    observations: list(data.observations, raw => {
      const item = record(raw)
      if (item.current_eligible !== false || typeof item.market_history_eligible !== 'boolean') throw new Error('Invalid history eligibility')
      choice(item.freshness, ['unvalidated'])
      return { id: text(item.id), capture_id: text(item.capture_id), captured_at: date(item.captured_at),
        observed_at: item.observed_at === null ? null : date(item.observed_at), source: text(item.source),
        acquisition_state: choice(item.acquisition_state, ['success', 'partial', 'cache_reuse', 'unknown']),
        evidence_kind: choice(item.evidence_kind, ['synthetic', 'retained']),
        validity: choice(item.validity, ['supported_at_capture', 'unqualified', 'invalidated', 'legacy_unqualified']),
        change: choice(item.change, ['initial', 'unchanged', 'increased', 'decreased', 'not_comparable']),
        duplicate_of: nullableText(item.duplicate_of), reasons: list(item.reasons, text),
        lineage: list(item.lineage, text), offer: offer(item.offer), binding: binding(item.binding),
        configuration: configuration(item.configuration), costs: list(item.costs, costScenario),
        policy_versions: Object.fromEntries(Object.entries(record(item.policy_versions)).map(([key, value]) => [key, text(value)])),
        dependencies: list(item.dependencies, reference),
        invalidations: list(item.invalidations, raw => {
          const invalid = record(raw)
          return { id: text(invalid.id), target: reference(invalid.target), reason: text(invalid.reason),
            recorded_at: date(invalid.recorded_at), correction_reference: text(invalid.correction_reference) }
        }) }
    }),
    attempts: list(data.attempts, raw => {
      const item = record(raw)
      return { capture_id: text(item.capture_id), captured_at: date(item.captured_at), source: text(item.source), query: text(item.query),
        state: choice(item.state, ['success', 'success_empty', 'partial', 'cache_reuse', 'blocked', 'capped', 'failed', 'not_attempted']),
        listing_count: integer(item.listing_count), completeness: choice(item.completeness, ['unknown', 'partial', 'declared_scope']),
        reason: nullableText(item.reason), reused_capture_id: nullableText(item.reused_capture_id) }
    }),
    gaps: list(data.gaps, raw => {
      const gap = record(raw)
      return { kind: choice(gap.kind, ['unobserved_interval', 'open_interval', 'source_outcome', 'not_returned']),
        start: date(gap.start), end: date(gap.end), state: nullableText(gap.state), reason: text(gap.reason) }
    }) }
}
export type ObservationHistory = ReturnType<typeof parseHistory>
export async function loadHistory(candidateId: string, signal: AbortSignal) {
  const response = await fetch(`/api/discovery/candidates/${encodeURIComponent(candidateId)}/history`, { signal })
  if (!response.ok) throw new Error('Observation history could not load. Reopen to retry.')
  const body: unknown = await response.json()
  const history = parseHistory(body)
  if (history.candidate_id !== candidateId) throw new Error('History subject does not match this candidate')
  return history
}
