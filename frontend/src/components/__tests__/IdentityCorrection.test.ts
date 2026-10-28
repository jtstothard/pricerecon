import { createElement } from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { expect, it } from 'vitest'
import { IdentityCorrection } from '../discovery/IdentityCorrection'
import { parseDiscoveryFeed } from '../../lib/discovery'
import captured from './image-feed.json'

it('offers one concise correction path with required attribution and advanced dispute controls', () => {
  const candidate = parseDiscoveryFeed(captured).candidates[0]
  const html = renderToStaticMarkup(createElement(IdentityCorrection, { candidate, onSaved: async () => {} }))
  expect(html).toContain('<summary>Wrong watch details?</summary>')
  expect(html).toContain('Old prices stop applying. Your target stays; alerts wait for a matching offer.')
  expect(html).not.toContain('For example,')
  expect(html).toContain('Original acquired dial:')
  expect(html).toContain('Intended value:')
  expect(html).toContain('name="correction_actor"')
  expect(html).toContain('name="correction_rationale"')
  expect(html).toContain('<details><summary>Advanced: dispute this identity</summary>')
  expect(html).not.toContain('<details open')
})

it('explains withdrawn buying evidence beside the saved intended value', () => {
  const candidate = parseDiscoveryFeed(captured).candidates[0]
  const original = { id: 'watch-blue', revision: 1, policy_version: 'fixture', state: 'supported' as const, values: { dial: 'blue' }, evidence_ids: [], issues: [] }
  candidate.configurations = [original]
  candidate.corrections = [{
    candidate_id: candidate.id, configuration_id: original.id, revision: 1,
    state: 'corrected', requalification: 'required', values: { dial: 'green' },
    original_configuration: original, original_evidence: [], needs: [], lineage: [],
  }]
  const html = renderToStaticMarkup(createElement(IdentityCorrection, { candidate, onSaved: async () => {} }))
  expect(html).toContain('Intended dial</dt><dd>green')
  expect(html).toContain('Old prices stop applying. Your target stays; alerts wait for a matching offer.')
  expect(html).toContain('<summary>Correction history and provenance</summary>')
})
