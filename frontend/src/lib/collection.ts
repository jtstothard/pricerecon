const resources = ['requests', 'pages', 'details', 'retries', 'fallbacks', 'browser_contexts', 'browser_seconds', 'ai_calls', 'ai_tokens', 'storage_bytes', 'elapsed_seconds'] as const
const states = ['running', 'success', 'success_empty', 'partial', 'cache_reuse', 'blocked', 'capped', 'failed', 'interrupted'] as const
function object(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error('Invalid collection state')
  return value as Record<string, unknown>
}
function text(value: unknown): string {
  if (typeof value !== 'string' || !value) throw new Error('Missing collection state')
  return value
}
function integer(value: unknown): number {
  if (typeof value !== 'number' || !Number.isSafeInteger(value) || value < 0) throw new Error('Invalid collection count')
  return value
}
function choice<T extends string>(value: unknown, allowed: readonly T[]): T {
  for (const candidate of allowed) if (value === candidate) return candidate
  throw new Error('Unknown collection state')
}
function list<T>(value: unknown, parse: (item: unknown) => T): T[] {
  if (!Array.isArray(value)) throw new Error('Missing collection details')
  return value.map(parse)
}
function date(value: unknown): string {
  const result = text(value)
  if (!Number.isFinite(Date.parse(result))) throw new Error('Invalid collection time')
  return result
}
export function parseCollection(value: unknown) {
  const data = object(value)
  return {
    state: choice(data.state, ['blocked', 'supplied', 'expired']),
    activation: choice(data.activation, ['staged']), gates: list(data.gates, text),
    scope_id: data.scope_id === null ? null : text(data.scope_id),
    stops_at: data.stops_at === null ? null : date(data.stops_at),
    usage: list(data.usage, raw => { const item = object(raw); return {
      resource: choice(item.resource, resources), used: integer(item.used), limit: integer(item.limit), tracking_reserve: integer(item.tracking_reserve),
    } }),
    provider_usage: list(data.provider_usage, raw => { const item = object(raw); return {
      source: text(item.source), used: integer(item.used), limit: integer(item.limit), tracking_reserve: integer(item.tracking_reserve),
    } }),
    attempts: list(data.attempts, raw => { const item = object(raw); return {
      id: text(item.id), source: text(item.source), query: text(item.query), purpose: choice(item.purpose, ['discovery', 'tracking', 'verification']),
      state: choice(item.state, states), reason: item.reason === null ? null : text(item.reason),
      attempted_at: date(item.attempted_at), next_eligible_at: item.next_eligible_at === null ? null : date(item.next_eligible_at),
      last_good_at: item.last_good_at === null ? null : date(item.last_good_at),
      last_good_age_seconds: item.last_good_age_seconds === null ? null : integer(item.last_good_age_seconds),
      evidence_state: choice(item.evidence_state, ['unrefreshed', 'observed_at_attempt']),
    } }),
  }
}
export type CollectionStatus = ReturnType<typeof parseCollection>
