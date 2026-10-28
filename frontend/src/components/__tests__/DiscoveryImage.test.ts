import { expect, it } from 'vitest'
import { createElement } from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import DiscoveryImage from '../discovery/DiscoveryImage'

it('shows an attributed photo with privacy preserving loading', () => {
  const html = renderToStaticMarkup(createElement(DiscoveryImage, { image: {
    kind: 'photo', url: 'https://assets.invalid/control.jpg', attribution: 'Fixture author',
    provenance: 'Synthetic metadata', permission_reference: 'permission-v1', identity_reference: 'depiction-v1',
  } }))
  expect(html).toContain('<img')
  expect(html).toContain('Photograph')
  expect(html).toContain('Fixture author')
  expect(html).toContain('referrerPolicy="no-referrer"')
})

it('labels placeholders as unavailable product imagery', () => {
  const html = renderToStaticMarkup(createElement(DiscoveryImage, { image: {
    kind: 'original_placeholder', url: null, attribution: 'PriceRecon', provenance: 'Generic artwork',
    permission_reference: null, identity_reference: null,
  } }))
  expect(html).not.toContain('<img')
  expect(html).toContain('Product image unavailable')
})

it('distinguishes product illustration from photography and exposes evidence', () => {
  const html = renderToStaticMarkup(createElement(DiscoveryImage, { image: {
    kind: 'illustration', url: 'https://assets.invalid/drawing.png', attribution: 'Fixture artist',
    provenance: 'Synthetic drawing metadata', permission_reference: 'rights-control', identity_reference: 'identity-control',
  } }))
  expect(html).toContain('Product illustration; not a photograph')
  expect(html).toContain('rights-control')
  expect(html).toContain('identity-control')
})
