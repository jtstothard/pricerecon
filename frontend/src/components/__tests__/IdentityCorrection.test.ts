import { createElement } from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { expect, it } from 'vitest'
import { IdentityCorrection } from '../discovery/IdentityCorrection'
import { parseDiscoveryFeed } from '../../lib/discovery'
import captured from './image-feed.json'

it('offers one concise correction path with required attribution and advanced dispute controls', () => {
  const candidate = parseDiscoveryFeed(captured).candidates[0]
  candidate.configurations = [
    {
      id: 'watch-blue',
      revision: 1,
      policy_version: 'fixture',
      state: 'supported' as const,
      values: { dial: 'mint' },
      evidence_ids: [],
      issues: [],
    },
  ]
  const html = renderToStaticMarkup(
    createElement(IdentityCorrection, { candidate, onSaved: async () => {} })
  )
  expect(html).toContain('<h3>Wrong watch details?</h3>')
  expect(html).toContain('nothing is deleted or overwritten')
  expect(html).not.toContain('For example,')
  expect(html).toContain('You are changing <strong>dial</strong> from <strong>mint</strong> to')
  expect(html).toContain('name="correction_actor"')
  expect(html).toContain('name="correction_rationale"')
  expect(html).not.toContain('<section><h3>Correction state</h3>')
  expect(html).not.toContain('Identity state')
  expect(html).toContain('How sure are you?')
  expect(html).not.toContain('<details open')
})

it('explains withdrawn buying evidence beside the saved intended value', () => {
  const candidate = parseDiscoveryFeed(captured).candidates[0]
  const original = {
    id: 'watch-blue',
    revision: 1,
    policy_version: 'fixture',
    state: 'supported' as const,
    values: { dial: 'blue' },
    evidence_ids: [],
    issues: [],
  }
  candidate.configurations = [original]
  candidate.corrections = [
    {
      candidate_id: candidate.id,
      configuration_id: original.id,
      revision: 1,
      state: 'corrected',
      requalification: 'required',
      values: { dial: 'green' },
      original_configuration: original,
      original_evidence: [],
      needs: [],
      lineage: [
        {
          id: 'correction-1',
          revision: 1,
          field: 'dial',
          value: 'green',
          state: 'corrected',
          original_value: 'blue',
          actor: 'Buyer',
          rationale: 'The recorded specification is incorrect.',
          recorded_at: '2026-10-27T12:04:48Z',
          previous_correction_id: null,
        },
      ],
    },
  ]
  const html = renderToStaticMarkup(
    createElement(IdentityCorrection, { candidate, onSaved: async () => {} })
  )
  expect(html).toContain('dial: blue → green')
  expect(html).toContain('Show full intended configuration')
  expect(html).toContain('Intended dial</dt><dd>green')
  expect(html).toContain('kept on record, no longer used for pricing')
  expect(html).toContain('<h3>Correction history and provenance</h3>')
})
