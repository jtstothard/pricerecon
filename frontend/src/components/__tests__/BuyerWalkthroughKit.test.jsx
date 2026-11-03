import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { expect, it } from 'vitest'

// The buyer walkthrough kit quotes UI copy and API field paths. This pins each
// refreshed quotation, as the full sentence, to the source that renders it, so a
// copy change cannot silently leave the kit asserting text the product no longer
// shows. It checks agent-verifiable wording only; it establishes no human
// comprehension.
const root = fileURLToPath(new URL('../../../../', import.meta.url))
const squash = (text) => text.replace(/\s+/g, ' ').trim()
const raw = (path) => readFileSync(`${root}${path}`, 'utf8')
// Source as the product would render it: comments removed (so a comment cannot
// satisfy a pin), JSX markup tags removed, JSX space expressions and same-file
// string constants resolved, whitespace collapsed. Dynamic {expressions} stay in
// place, which is why entries with dynamic parts pin the static text around them.
function rendered(path) {
  let code = raw(path).replace(/\/\*[\s\S]*?\*\//g, '').replace(/(^|\s)\/\/.*$/gm, '$1')
  for (const [, name, value] of code.matchAll(/const (\w+) = '([^']*)'/g))
    code = code.replaceAll('${' + name + '}', value).replaceAll('{' + name + '}', value)
  return squash(code.replace(/\{' '\}/g, ' ').replace(/<\/?[A-Za-z][^>]*>/g, ''))
}
const kit = squash(raw('docs/testing/buyer-walkthrough.md'))
const files = {
  correction: 'frontend/src/components/discovery/IdentityCorrection.tsx',
  discovery: 'frontend/src/pages/Discovery.tsx',
  tracking: 'frontend/src/components/ExactTracking.tsx',
  history: 'frontend/src/components/discovery/ObservationHistory.tsx',
  historyLib: 'frontend/src/lib/history.ts',
  assessmentsLib: 'frontend/src/lib/assessments.ts',
  coverage: 'frontend/src/components/discovery/CollectionCoverage.tsx',
}
const src = Object.fromEntries(Object.entries(files).map(([name, path]) => [name, rendered(path)]))
// True when every static part appears in the source, in order.
function inOrder(code, parts) {
  let at = 0
  for (const part of parts) {
    const found = code.indexOf(part, at)
    if (found < 0) return false
    at = found + part.length
  }
  return true
}

// [label, file, kit quotation, source form]. The kit quotation is the complete
// sentence as the kit prints it. The source form is the same sentence with "…"
// for each dynamic value the source computes; it defaults to the kit quotation.
const D = '…'
const canonical = [
  ['I1 preview', 'correction', 'You are changing dial from mint to …', 'You are changing … from … to'],
  [
    'I1 consequence copy',
    'correction',
    'Saving this correction withdraws the prices recorded for the old details — they are kept on record, no longer used for pricing, kept in History. Saving records your correction; it does not fetch new prices.',
  ],
  ['I1 save button', 'correction', 'Save correction — old prices will be withdrawn'],
  ['I1 post-save block', 'correction', 'Correction saved — a history entry was added below.'],
  ['I1 post-save surface', 'correction', 'old observations were marked withdrawn — kept, unchanged, in History'],
  [
    'I1 history sentence',
    'correction',
    'Old prices, coupons and buying assessments are kept on record, no longer used for pricing. Your target stays; alerts wait for a fresh matching offer.',
  ],
  ['I1 rejected write', 'correction', 'Reload the feed before retrying.'],
  [
    'I2 card caution',
    'discovery',
    'Details corrected (dial mint → salmon) · old prices kept on record, no longer used for pricing · awaiting fresh evidence',
    '… (…) · old prices kept on record, no longer used for pricing · awaiting fresh evidence',
  ],
  ['I2 card label', 'discovery', 'Details corrected (dial', "corrected: 'Details corrected'"],
  [
    'I3 tracking label',
    'tracking',
    'Prior evidence no longer applies — kept on record, no longer used for alerts · target retained',
  ],
  ['I3 intended values', 'correction', 'Show full intended configuration'],
  ['I3 intended label', 'correction', 'Intended dial', 'Intended {label(key)}'],
  ['G2 status label', 'history', 'current at capture', "supported_at_capture: 'current at capture'"],
  ['G2 status label', 'history', 'unqualified at capture', "unqualified: 'unqualified at capture'"],
  ['G2 status label', 'history', 'legacy — unqualified', "legacy_unqualified: 'legacy — unqualified'"],
  [
    'G2 status label',
    'history',
    'withdrawn after correction — kept on record',
    "invalidated: 'withdrawn after correction — kept on record'",
  ],
  ['G2 repeat marker', 'history', '· repeated evidence'],
  [
    'H1 gaps sentence',
    'coverage',
    'Capped, blocked and failed attempts leave gaps; an empty result means the declared search completed.',
  ],
  [
    'H2 supplied, reserves 0',
    'coverage',
    'No capacity is carved out of the shared allowance for tracking or potential-alert verification: every tracking reserve is 0, so discovery and tracking draw on the same allowance until a limit is used up.',
  ],
  [
    'H2 limits used up',
    'coverage',
    'N of M limits are already used up, so further attempts that need them are capped.',
    '${spent} of ${limits.length} limits are already used up, so further attempts that need them are capped.',
  ],
  [
    'H2 expired or not yet started',
    'coverage',
    'The operating envelope is not active now (its window has closed or has not opened yet): admission is closed, so no tracking reserve currently applies. The recorded figures below are exact but nothing can use them.',
  ],
  [
    'H2 changed policy',
    'coverage',
    'The supplied operating policy differs from the retained envelope, so admission is closed and no tracking reserve currently applies. The retained envelope is shown for reference; nothing can use its figures.',
  ],
  [
    'H2 invalid policy',
    'coverage',
    'A supplied operating envelope was rejected as invalid, so there is no usable operating envelope and no tracking reserve is defined. Admission is closed.',
  ],
  [
    'H2 ambiguous policy',
    'coverage',
    'More than one operating envelope is stored and none can be chosen, so there is no usable operating envelope and no tracking reserve is defined. Admission is closed.',
  ],
  [
    'H2 required policy',
    'coverage',
    'An operating envelope is required and none usable is available, so no tracking reserve is defined. Admission is closed.',
  ],
  [
    'H2 supplied without limits',
    'coverage',
    'The supplied operating envelope sets no limits, so no tracking reserve is defined.',
  ],
  [
    'H2 retained envelope row',
    'coverage',
    'Retained envelope … is not in force; recorded stop time',
    'Retained envelope ${status.scope_id} is not in force; recorded stop time',
  ],
  [
    'H3 elapsed retry time',
    'coverage',
    "By this browser's clock no spacing wait remains (recorded earliest next attempt: …); the server decides admission when an attempt starts; no run is scheduled and missed periods are not replayed.",
    "By this browser's clock no spacing wait remains (recorded earliest next attempt: ${when}); the server decides admission when an attempt starts; no run is scheduled and missed periods are not replayed.",
  ],
  [
    'H3 future retry time',
    'coverage',
    "Source spacing: recorded earliest next attempt is … (by this browser's clock, still ahead); the server decides admission when an attempt starts; no run is scheduled and missed periods are not replayed.",
    "Source spacing: recorded earliest next attempt is ${when} (by this browser's clock, still ahead); the server decides admission when an attempt starts; no run is scheduled and missed periods are not replayed.",
  ],
  [
    'H3 running lease ahead',
    'coverage',
    "This source is held for the running attempt until … (by this browser's clock, lease still ahead); the server decides admission when an attempt starts; no run is scheduled and missed periods are not replayed.",
    "This source is held for the running attempt until ${when} (by this browser's clock, lease still ahead); the server decides admission when an attempt starts; no run is scheduled and missed periods are not replayed.",
  ],
  [
    'H3 running lease expired',
    'coverage',
    "Lease expired, unconfirmed: the running attempt's lease ended … (by this browser's clock) with no recorded finish; the server decides admission when an attempt starts; no run is scheduled and missed periods are not replayed.",
    "Lease expired, unconfirmed: the running attempt's lease ended ${when} (by this browser's clock) with no recorded finish; the server decides admission when an attempt starts; no run is scheduled and missed periods are not replayed.",
  ],
]
it.each(canonical)('%s is quoted in full by the kit and still produced by the source: %s', (_label, file, quotation, form = quotation) => {
  expect(kit).toContain(quotation)
  expect(inOrder(src[file], form.split(D).filter(Boolean))).toBe(true)
})

// The helper must not accept a comment, a reordering or a partial match.
it('does not let a comment, a truncation or a reordering satisfy a source pin', () => {
  const commentOnly = rendered('frontend/src/components/discovery/CollectionCoverage.tsx')
  expect(commentOnly).not.toContain('debit() refuses every')
  expect(commentOnly).not.toContain('only for state "supplied"')
  expect(inOrder('abc def ghi', ['def', 'abc'])).toBe(false)
  expect(inOrder('Correction saved', ['Correction saved — a history entry was added below.'])).toBe(false)
})

// Field paths and row labels: the kit names them in prose; the source must still
// carry the same names (comments removed, markup left as written).
const code = (path) => squash(raw(path).replace(/\/\*[\s\S]*?\*\//g, '').replace(/(^|\s)\/\/.*$/gm, '$1'))
const emitted = [
  ['G2 direction field', 'historyLib', "change: choice(item.change, ['initial', 'unchanged', 'increased', 'decreased', 'not_comparable'])"],
  ['K1 gaps path', 'assessmentsLib', 'gaps: list(coverage.gaps'],
  ['K1 exclusions path', 'assessmentsLib', 'exclusions: list(item.exclusions'],
  ['C2 offer row', 'discovery', "['Qualification', offer.qualification.state]"],
  ['C2 offer row', 'discovery', "['Comparison', offer.comparison.state]"],
]
it.each(emitted)('%s is still emitted by the source: %s', (_label, file, text) => {
  expect(code(files[file])).toContain(text)
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
  'No capacity is held back for tracking',
  'discovery can use the whole shared allowance',
  'Source spacing: not retried before',
  'No spacing wait remains (earliest next attempt was',
  'CollectionCoverage.tsx:41-43',
  'there is no current operating envelope',
  'The operating policy is blocked',
  'The operating envelope has expired',
  'No operating envelope is supplied',
  'A crashed process leaves such a row until the next attempt starts',
]
it.each(stale)('the kit no longer quotes the retired wording %j', (text) => {
  expect(kit).not.toContain(text)
  for (const file of Object.values(src)) expect(file).not.toContain(text)
})

// The backend keeps a policy (and its rows) only for supplied, outside-window and
// operating_policy_changed; invalid, ambiguous and required select none, so the
// kit must not pair rows with them (src/pricerecon/db/collection.py).
it('pairs retained-policy wording with retained rows and rejected wording with none', () => {
  const h2 = kit.slice(kit.indexOf('#### H2 '), kit.indexOf('#### H3 '))
  expect(h2).toMatch(/operating_policy_changed[^.]*retained/)
  expect(h2).toMatch(/invalid[^.]*ambiguous[^.]*required[^.]*(no policy|no usage rows|no rows)/i)
  expect(h2).not.toMatch(/changed or invalid/)
})
it('describes the crash lease reading precisely: only the latest row per scope and source is cleared', () => {
  const h3 = kit.slice(kit.indexOf('#### H3 '), kit.indexOf('#### H4 ') > 0 ? kit.indexOf('#### H4 ') : undefined)
  expect(h3).toContain('only the latest')
  expect(h3).toContain('older')
})

it('keeps no line reference into the collection panel, which is assembled from functions', () => {
  expect(kit).not.toMatch(/CollectionCoverage\.tsx:\d/)
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
