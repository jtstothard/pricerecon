import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { expect, it } from 'vitest'

// The buyer walkthrough kit quotes UI copy and API field paths. This pins every
// quotation to the source that renders or emits it, so a copy change cannot
// silently leave the kit asserting text the product no longer shows. It checks
// agent-verifiable wording only; it establishes no human comprehension.
const root = fileURLToPath(new URL('../../../../', import.meta.url))
const squash = (text) => text.replace(/\s+/g, ' ')
const read = (path) => squash(readFileSync(`${root}${path}`, 'utf8'))
const kit = read('docs/testing/buyer-walkthrough.md')
const src = {
  correction: read('frontend/src/components/discovery/IdentityCorrection.tsx'),
  discovery: read('frontend/src/pages/Discovery.tsx'),
  tracking: read('frontend/src/components/ExactTracking.tsx'),
  history: read('frontend/src/components/discovery/ObservationHistory.tsx'),
  historyLib: read('frontend/src/lib/history.ts'),
  assessmentsLib: read('frontend/src/lib/assessments.ts'),
  coverage: read('frontend/src/components/discovery/CollectionCoverage.tsx'),
}

// Quotation present in both the kit and the file that produces it.
const canonical = [
  ['I1 consequence copy', 'correction', 'Saving this correction withdraws the prices recorded for the old details'],
  ['I1 consequence copy', 'correction', 'Saving records your correction; it does not fetch new prices.'],
  ['I1 shared vocabulary', 'correction', 'kept on record, no longer used for pricing'],
  ['I1 save button', 'correction', 'Save correction — old prices will be withdrawn'],
  ['I1 post-save summary', 'correction', 'Correction saved'],
  ['I1 post-save summary', 'correction', 'old observations were marked withdrawn — kept, unchanged, in'],
  ['I1 history sentence', 'correction', 'Your target stays; alerts wait for a fresh matching offer.'],
  ['I1 rejected write', 'correction', 'Reload the feed before retrying.'],
  ['I2 card caution', 'discovery', 'Details corrected'],
  ['I2 card caution', 'discovery', '· awaiting fresh evidence'],
  ['I3 tracking label', 'tracking', 'Prior evidence no longer applies — kept on record, no longer used for alerts · target retained'],
  ['I3 intended values', 'correction', 'Show full intended configuration'],
  ['G2 status label', 'history', 'withdrawn after correction — kept on record'],
  ['G2 repeat marker', 'history', '· repeated evidence'],
  ['H2 reserve sentence', 'coverage', 'No capacity is held back for tracking or potential-alert verification'],
  ['H3 elapsed retry time', 'coverage', 'No spacing wait remains'],
  ['H3 future retry time', 'coverage', 'Source spacing: not retried before'],
]
it.each(canonical)('%s is quoted by the kit and still produced by the source: %s', (_label, file, text) => {
  expect(src[file]).toContain(text)
  expect(kit).toContain(text)
})

// Field paths and row labels: the kit names them in prose; the source must still
// carry the same names.
const emitted = [
  ['G2 direction field', 'historyLib', "change: choice(item.change, ['initial', 'unchanged', 'increased', 'decreased', 'not_comparable'])"],
  ['K1 gaps path', 'assessmentsLib', 'gaps: list(coverage.gaps'],
  ['K1 exclusions path', 'assessmentsLib', 'exclusions: list(item.exclusions'],
  ['C2 offer row', 'discovery', "['Qualification', offer.qualification.state]"],
  ['C2 offer row', 'discovery', "['Comparison', offer.comparison.state]"],
]
it.each(emitted)('%s is still emitted by the source: %s', (_label, file, text) => {
  expect(src[file]).toContain(text)
})

it('quotes the canonical field paths and values instead of the old names', () => {
  expect(kit).toContain('`change`')
  expect(kit).toContain('`initial` / `unchanged` / `increased` / `decreased` / `not_comparable`')
  expect(kit).toContain('`coverage.gaps`')
  expect(kit).toContain('`exclusions`')
  expect(kit).toContain('Qualification reads "unresolved"')
  expect(kit).toContain('Comparison reads "rejected"')
  expect(kit).toContain('`configuration_mismatch`')
  expect(kit).toContain('the binding resolution is `rejected`')
})

// Wording the kit used to carry; none of it is rendered any more.
const stale = [
  'Old prices stop applying',
  'Old prices withdrawn · matching offer needed',
  'Evidence withdrawn · target retained',
  'Intended dial: salmon',
  'direction label',
  'have reserved capacity',
  'Next eligible',
  '(`exclusions`, `gaps`)',
  'leaves the merchant selection unresolved',
]
it.each(stale)('the kit no longer quotes the retired wording %j', (text) => {
  expect(kit).not.toContain(text)
  for (const file of Object.values(src)) expect(file).not.toContain(text)
})

it('keeps the human-acceptance record untouched: every box blank, verdict form present', () => {
  // One box per task A1–K2; the recording-convention example above them is not a task.
  const tasks = kit.slice(kit.indexOf('## 2. Task-by-task walkthrough'))
  expect(tasks.match(/☐ Accepted/g)).toHaveLength(33)
  expect(kit.match(/☐ Pass · Flag/g)).toHaveLength(5)
  expect(kit).not.toMatch(/[☑✅✔]/)
  for (const heading of ['## 5. Verdict form', 'Overall verdict (tick one):', 'Buyer: \\_\\_\\_\\_\\_\\_\\_\\_\\_\\_ · Date:']) {
    expect(kit).toContain(heading)
  }
  expect(kit).toContain('agent verification only')
  expect(kit).toContain('establishes no human comprehension')
})

it('does not name any private deployment detail', () => {
  expect(kit).not.toMatch(/watch-pilot-2026-10-28\.consumed/)
})
