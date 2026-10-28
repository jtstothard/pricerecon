import { createElement } from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { expect, it } from 'vitest'
import { Candidate, ProductContent } from '../../pages/Discovery'
import { parseDiscoveryFeed } from '../../lib/discovery'
import captured from './image-feed.json'

// Native closed details hide their body, while their summary remains available.
function closedView(html: string): string {
  let depth = 0
  let summary = false
  return html
    .split(/(<\/?(?:details|summary)\b[^>]*>)/)
    .filter((token) => {
      if (token.startsWith('<details')) {
        depth++
        return false
      }
      if (token.startsWith('</details')) {
        depth--
        return false
      }
      if (token.startsWith('<summary')) {
        summary = depth === 1
        return false
      }
      if (token.startsWith('</summary')) {
        summary = false
        return false
      }
      return depth === 0 || summary
    })
    .join('')
}

it.each(['unknown', 'conditional', 'verified_at_observation'] as const)(
  'keeps %s price state visible while evidence and correction forms stay collapsed',
  (state) => {
    const candidate = parseDiscoveryFeed(captured).candidates[0]
    candidate.public_total = {
      ...candidate.public_total,
      state,
      amount: state === 'unknown' ? null : '70.10',
      currency: 'GBP',
    }
    candidate.configurations = [
      {
        id: 'fixture-watch',
        revision: 1,
        policy_version: 'technical-policy-v1',
        state: 'supported',
        values: { movement: 'Quartz', case_width_mm: '38' },
        evidence_ids: [],
        issues: [],
      },
    ]
    const html = renderToStaticMarkup(
      createElement(Candidate, { candidate, tracking: [], onSaved: async () => {} })
    )
    const visible = closedView(html)
    expect(visible).toContain(candidate.title)
    expect(visible).toContain(
      state === 'unknown'
        ? 'Total unknown'
        : state === 'conditional'
          ? 'Conditional'
          : 'Verified at observation'
    )
    expect(visible).toContain('Quartz')
    expect(visible).toContain('38 mm')
    expect(visible).toContain('Product details')
    expect(visible).toContain('Track this watch')
    expect(visible).not.toContain('technical-policy-v1')
    expect(visible).not.toContain('Merchant selection and comparison')
    expect(visible).not.toContain('Item lead')
    expect(visible).not.toContain('<form')
    const technical = renderToStaticMarkup(
      createElement(ProductContent, {
        candidate,
        tracking: [],
        onSaved: async () => {},
        view: 'technical',
      })
    )
    expect(technical).toContain('technical-policy-v1')
    expect(html).not.toContain('<details')
    expect(html).not.toMatch(/<details[^>]*\sopen/)
  }
)

it('keeps unresolved identity and outside-preference status visible', () => {
  const candidate = parseDiscoveryFeed(captured).candidates[0]
  candidate.identity_state = 'unresolved'
  candidate.preference_fit = [
    { field: 'compact', strength: 'hard', state: 'outside', reason: 'Too large' },
  ]
  const visible = closedView(
    renderToStaticMarkup(
      createElement(Candidate, { candidate, tracking: [], onSaved: async () => {} })
    )
  )
  expect(visible).toContain('Identity unresolved')
  expect(visible).toContain('Outside preferences')
})
