import { choice, configuration, date, fieldEvidence, integer, list, record, text } from './discovery'

export const identityFields = ['maker', 'reference', 'generation', 'movement', 'case_width_mm', 'dial', 'strap', 'date_display', 'product_kind'] as const
export type IdentityField = typeof identityFields[number]
export function parseCorrection(value: unknown) {
  const item = record(value)
  return {
    candidate_id: text(item.candidate_id), configuration_id: text(item.configuration_id), revision: integer(item.revision),
    state: choice(item.state, ['uncorrected', 'corrected', 'disputed']),
    requalification: choice(item.requalification, ['not_required', 'required', 'supported_by_fresh_evidence']),
    values: Object.fromEntries(Object.entries(record(item.values)).map(([field, value]) => [field, text(value)])),
    original_configuration: configuration(item.original_configuration), original_evidence: list(item.original_evidence, fieldEvidence),
    needs: list(item.needs, text),
    lineage: list(item.lineage, raw => {
      const entry = record(raw)
      return { id: text(entry.id), revision: integer(entry.revision), field: choice(entry.field, identityFields),
        value: text(entry.value), state: choice(entry.state, ['corrected', 'disputed']),
        original_value: entry.original_value === null ? null : text(entry.original_value),
        actor: text(entry.actor), rationale: text(entry.rationale), recorded_at: date(entry.recorded_at),
        previous_correction_id: entry.previous_correction_id === null ? null : text(entry.previous_correction_id) }
    }),
  }
}
export type Correction = ReturnType<typeof parseCorrection>
export async function saveCorrection(candidateId: string, subjectId: string, input: {
  capture_id: string; observed_configuration_id: string; configuration_revision: number; expected_revision: number;
  field: IdentityField; value: string; actor: string; rationale: string; state: 'corrected' | 'disputed';
}) {
  const response = await fetch(`/api/discovery/candidates/${encodeURIComponent(candidateId)}/corrections/${encodeURIComponent(subjectId)}`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(input),
  })
  if (response.status === 409) {
    const body: unknown = await response.json()
    const detail = record(body).detail
    throw new Error(typeof detail === 'string' ? detail : 'Identity changed. Reload before saving.')
  }
  if (!response.ok) throw new Error('Correction was not saved. Check the field, value, attribution and rationale.')
  const body: unknown = await response.json()
  return parseCorrection(body)
}
