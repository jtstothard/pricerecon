import { createElement } from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { expect, it } from 'vitest'
import { IdentityCorrection } from '../discovery/IdentityCorrection'
import { parseDiscoveryFeed } from '../../lib/discovery'
import captured from './image-feed.json'

it('explains a wrong-variant correction and buying consequences before the form', () => {
  const candidate = parseDiscoveryFeed(captured).candidates[0]
  const html = renderToStaticMarkup(createElement(IdentityCorrection, { candidate, onSaved: async () => {} }))
  const explanation = html.slice(0, html.indexOf('<form'))
  expect(explanation).toContain('Correct a wrong watch match')
  expect(explanation).toContain('For example, if the app recorded a blue dial but the watch you meant has a green dial')
  expect(explanation).toContain('Old blue-dial prices do not prove the green-dial price.')
  expect(explanation).toContain('Your saved price target stays. Price alerts pause until fresh evidence matches the corrected watch.')
  expect(explanation).toContain('Choosing another option in a shop or editing a reference photo is a different action.')
  expect(explanation).toContain('Saving does not fetch a new price, refresh the source or change the reference image.')
  expect(html).toContain('Original acquired dial:')
  expect(html).toContain('Intended value:')
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
  expect(html).toContain('Your saved price target stays, but old prices, coupons and buying assessments no longer apply to this watch.')
  expect(html).toContain('Price alerts are paused until fresh matching evidence supports the corrected watch.')
  expect(html).toContain('Saving alone does not fetch a new price or change the reference image.')
})
