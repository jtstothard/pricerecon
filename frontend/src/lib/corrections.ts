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
export type CorrectionLineage = Correction['lineage'][number]

export function correctionPresentationState(
  entries: Pick<CorrectionLineage, 'state'>[]
): 'corrected' | 'disputed' | 'changed' {
  if (entries.length > 0 && entries.every((entry) => entry.state === 'corrected')) return 'corrected'
  if (entries.length > 0 && entries.every((entry) => entry.state === 'disputed')) return 'disputed'
  return 'changed'
}

export type CorrectionSummaryEntry = CorrectionLineage & { configuration_id: string }

function compareLineage(left: CorrectionLineage, right: CorrectionLineage) {
  return left.recorded_at.localeCompare(right.recorded_at) || left.id.localeCompare(right.id)
}

/** Follow retained links rather than trusting the API array's presentation order. */
function orderedLineage(entries: CorrectionLineage[]): CorrectionLineage[] {
  const ids = new Set(entries.map((entry) => entry.id))
  const children = new Map<string, CorrectionLineage[]>()
  const roots: CorrectionLineage[] = []
  for (const entry of entries) {
    if (entry.previous_correction_id && ids.has(entry.previous_correction_id)) {
      const siblings = children.get(entry.previous_correction_id) ?? []
      siblings.push(entry)
      children.set(entry.previous_correction_id, siblings)
    } else {
      roots.push(entry)
    }
  }
  const ordered: CorrectionLineage[] = []
  const visited = new Set<string>()
  const append = (entry: CorrectionLineage) => {
    if (visited.has(entry.id)) return
    visited.add(entry.id)
    ordered.push(entry)
    for (const child of (children.get(entry.id) ?? []).sort(compareLineage)) append(child)
  }
  for (const root of roots.sort(compareLineage)) append(root)
  // Malformed cycles remain visible and deterministic instead of disappearing.
  for (const entry of [...entries].sort(compareLineage)) append(entry)
  return ordered
}

/** Current values within each independent configuration journal. */
export function currentCorrectionSummary(corrections: Correction[]): CorrectionSummaryEntry[] {
  const journals = corrections
    .filter((correction) => correction.requalification === 'required')
    .sort((left, right) =>
      left.configuration_id.localeCompare(right.configuration_id) ||
      left.lineage.map((entry) => entry.id).sort().join(',').localeCompare(
        right.lineage.map((entry) => entry.id).sort().join(',')
      )
    )
  return journals.flatMap((correction) => {
    const current = new Map<IdentityField, CorrectionSummaryEntry>()
    for (const entry of orderedLineage(correction.lineage)) {
      const first = current.get(entry.field)
      current.set(entry.field, {
        ...entry,
        original_value: first ? first.original_value : entry.original_value,
        configuration_id: correction.configuration_id,
      })
    }
    return Array.from(current.values())
  })
}

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
