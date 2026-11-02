import { readFileSync } from 'node:fs'
import { createElement } from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { expect, it } from 'vitest'
import { ProductContent } from '../../pages/Discovery'
import { parseDiscoveryFeed } from '../../lib/discovery'
import captured from './image-feed.json'

// Plain-JS test (like ProductFlow.test.jsx): it reads stylesheet sources with
// node:fs, which stays outside the tsc program because the frontend toolchain
// has no @types/node and package.json must not gain one for a test.

const VIEWS = ['overview', 'costs', 'history', 'tracking', 'correction', 'technical']

// Buyer session 2026-11-02: "the technical tab changes the background colkour
// too". Two contract points: (1) every product tab renders in the same
// container shape with no per-tab background styling; (2) the app frame's
// corner washes must not rescale with tab content height — unsized
// `radial-gradient(circle …)` layers default to farthest-corner, so the tall
// Technical tab stretched them over the whole page and shifted the background.
const discoveryCss = readFileSync(new URL('../../styles/discovery.css', import.meta.url), 'utf8')
const layoutCss = readFileSync(new URL('../../styles/layout.css', import.meta.url), 'utf8')

it.each(VIEWS)('renders the %s tab in the same container shape as every other tab', (view) => {
  const candidate = parseDiscoveryFeed(captured).candidates[1]
  const html = renderToStaticMarkup(
    createElement(ProductContent, { candidate, tracking: [], onSaved: async () => {}, view })
  )
  expect(html).toContain(`class="product-content product-view-${view}"`)
  expect(html).not.toMatch(/class="product-content product-view-[^"]* /)
})

it('keeps per-view product styling free of background declarations', () => {
  const perViewRules = discoveryCss.match(/\.product-view-[^{]*\{[^}]*\}/g) ?? []
  expect(perViewRules.length).toBeGreaterThan(0)
  for (const rule of perViewRules) {
    expect(rule).not.toMatch(/background[^:]*:/)
  }
})

it('sizes the app-shell corner washes independently of page height', () => {
  const shellRule = layoutCss.match(/\.app-shell\s*\{[^}]*\}/)?.[0]
  expect(shellRule).toBeTruthy()
  // Unsized `circle at <position>` resolves to farthest-corner: the wash grows
  // with the shell, so a taller tab (Technical) tinted the whole page.
  expect(shellRule).not.toMatch(/radial-gradient\(\s*circle\s+at/)
  expect(shellRule).toMatch(/radial-gradient\(\s*circle\s+\d[\d.]*(px|rem|em|vw|vh)\s+at/)
})
