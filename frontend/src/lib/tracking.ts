// Boundary validation for exact tracking. Intent never contains collection settings.
function record(value: unknown): Record<string, unknown> {
  if (typeof value !== 'object' || value === null || Array.isArray(value)) throw new Error('Invalid tracking response')
  return Object.fromEntries(Object.entries(value))
}
function text(value: unknown): string {
  if (typeof value !== 'string') throw new Error('Invalid tracking text')
  return value
}
function integer(value: unknown): number {
  if (typeof value !== 'number' || !Number.isSafeInteger(value) || value < 0) throw new Error('Invalid tracking revision')
  return value
}
function decimal(value: unknown): string {
  const result = text(value)
  if (!/^\d+(?:\.\d+)?(?:e[+-]?\d+)?$/i.test(result)) throw new Error('Invalid delivered target')
  return result
}
function list<T>(value: unknown, parse: (item: unknown) => T): T[] {
  if (!Array.isArray(value)) throw new Error('Invalid tracking list')
  return value.map(parse)
}
function choice<const T extends readonly string[]>(value: unknown, options: T): T[number] {
  const found = options.find(option => option === value)
  if (found === undefined) throw new Error('Invalid tracking state')
  return found
}
function timestamp(value: unknown): string | null {
  if (value === null) return null
  const result = text(value)
  if (Number.isNaN(Date.parse(result))) throw new Error('Invalid tracking time')
  return result
}
export const channels = ['webhook', 'telegram', 'discord'] as const
export type TrackingChannel = typeof channels[number]
export function parseTracking(value: unknown) {
  const item = record(value), assessment = record(item.assessment)
  choice(item.collection_state, ['staged'])
  return {
    id: integer(item.id), revision: integer(item.revision),
    candidate_id: text(item.candidate_id), capture_id: text(item.capture_id),
    configuration_id: text(item.configuration_id), configuration_revision: integer(item.configuration_revision),
    target_gbp: decimal(item.target_gbp), notifications: { channels: list(record(item.notifications).channels, value => choice(value, channels)) },
    invalidation_revision: integer(item.invalidation_revision),
    invalidation_reason: item.invalidation_reason === null ? null : text(item.invalidation_reason),
    assessment: {
      state: choice(assessment.state, ['eligible', 'above_target', 'withheld']),
      reasons: list(assessment.reasons, text), assessed_at: timestamp(assessment.assessed_at), valid_until: timestamp(assessment.valid_until),
      delivered_gbp: assessment.delivered_gbp === null ? null : decimal(assessment.delivered_gbp),
      policy_version: assessment.policy_version === null ? null : text(assessment.policy_version),
    },
  }
}
export type ExactTracking = ReturnType<typeof parseTracking>
export function parseTrackingList(value: unknown) { return list(value, parseTracking) }

export async function saveTracking(input: {
  candidate_id: string; capture_id: string; configuration_id: string; configuration_revision: number;
  target_gbp: string; notifications: { channels: TrackingChannel[] };
}, existing?: ExactTracking) {
  const response = await fetch(existing ? `/api/discovery/tracking/${existing.id}` : '/api/discovery/tracking', {
    method: existing ? 'PUT' : 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(existing ? { expected_revision: existing.revision, target_gbp: input.target_gbp, notifications: input.notifications } : input),
  })
  if (response.status === 409) throw new Error('Tracking or evidence changed, or delivery is in flight. Reload before saving.')
  if (!response.ok) throw new Error('Target was not saved. Check the exact configuration and enter a positive GBP amount.')
  const body: unknown = await response.json()
  return parseTracking(body)
}

export async function loadDeliveries(trackingId: number) {
  const response = await fetch(`/api/discovery/tracking/${trackingId}/deliveries`)
  if (!response.ok) throw new Error('Delivery records could not load.')
  const body: unknown = await response.json()
  return list(record(body).items, value => {
    const delivery = record(value)
    return { event_id: integer(delivery.event_id), status: text(delivery.status), reason: text(delivery.reason),
      delivered_gbp: decimal(delivery.delivered_gbp), guarantee: text(delivery.guarantee),
      channels: Object.entries(record(delivery.channels)).map(([channel, status]) => ({ channel: choice(channel, channels), status: text(status) })) }
  })
}
export type Delivery = Awaited<ReturnType<typeof loadDeliveries>>[number]

export async function resolveDelivery(intent: ExactTracking, eventId: number, channel: TrackingChannel, resolution: 'record_sent' | 'abandon') {
  const response = await fetch(`/api/discovery/tracking/${intent.id}/deliveries/${eventId}/resolve`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ expected_revision: intent.revision, channel, resolution, confirm_no_send_in_flight: true }),
  })
  if (!response.ok) throw new Error('Delivery changed. Reload before reconciling.')
}
