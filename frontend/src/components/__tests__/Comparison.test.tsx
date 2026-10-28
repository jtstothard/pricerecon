import { createElement } from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { expect, it } from 'vitest'
import { Candidate } from '../../pages/Discovery'
import { parseDiscoveryFeed } from '../../lib/discovery'
import captured from './image-feed.json'
it('shows only decision information and a reloadable product link', () => {
  const candidate = parseDiscoveryFeed(captured).candidates[0]
  const html = renderToStaticMarkup(
    createElement(Candidate, { candidate, tracking: [], onSaved: async () => {} })
  )
  expect(html).toContain(`/discover/product/${encodeURIComponent(candidate.id)}`)
  expect(html).not.toContain('<details')
  expect(html).not.toContain('correction_actor')
  expect(html).not.toContain('Capture:')
})

import { ProductContent } from '../../pages/Discovery'
import { productNavigation } from '../../lib/productNavigation'
it.each(['overview', 'costs', 'history', 'tracking', 'correction', 'technical'])(
  'keeps the %s product view free of nested disclosure controls',
  (view) => {
    const candidate = parseDiscoveryFeed(captured).candidates[0]
    const html = renderToStaticMarkup(
      createElement(ProductContent, { candidate, tracking: [], onSaved: async () => {}, view })
    )
    expect(html).not.toContain('<details')
  }
)
it('retains local-only image mode across direct route navigation', () => {
  expect(
    productNavigation('/discover/product/watch', 'tracking', '?walkthrough=ticket12-local')
  ).toBe('/discover/product/watch?walkthrough=ticket12-local&view=tracking')
})
