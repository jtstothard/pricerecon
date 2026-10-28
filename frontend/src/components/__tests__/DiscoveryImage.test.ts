import manifest from '../../../../tests/fixtures/watch-images/manifest.json'
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

it('uses registered local bytes in the private walkthrough while retaining attribution', async () => {
  const { OfflineImageContext, parseOfflineImages } = await import('../discovery/OfflineImages')
  const assets = parseOfflineImages({ fixture: 'ticket12-private-images-v1', assets: [{
    source_url: manifest.assets[0].source_url,
    local_url: manifest.assets[0].local_url,
  }] })
  const html = renderToStaticMarkup(createElement(OfflineImageContext.Provider, { value: assets },
    createElement(DiscoveryImage, { image: {
      kind: 'photo', url: manifest.assets[0].source_url, attribution: manifest.attribution,
      provenance: 'Private personal walkthrough; synthetic price', permission_reference: 'Casio UK terms', identity_reference: 'Exact suffix',
    } })))
  expect(html).toContain(`src="${manifest.assets[0].local_url}"`)
  expect(html).toContain('Copyright © CASIO COMPUTER CO., LTD.')
  expect(html).not.toContain('src="https:')
  expect(() => parseOfflineImages({ fixture: 'other', assets: [] })).toThrow()
  expect(() => parseOfflineImages({ fixture: 'ticket12-private-images-v1', assets: [{ source_url: 'https://www.casio.com/product.png', local_url: '/api/watches' }] })).toThrow()
})


it('withholds remote imagery when private local assets are missing or still loading', async () => {
  const { OfflineImageContext } = await import('../discovery/OfflineImages')
  const html = renderToStaticMarkup(createElement(OfflineImageContext.Provider, { value: new Map() },
    createElement(DiscoveryImage, { image: {
      kind: 'photo', url: manifest.assets[0].source_url, attribution: manifest.attribution,
      provenance: 'Retained private copy', permission_reference: manifest.terms_url, identity_reference: manifest.product_url,
    } })))
  expect(html).not.toContain('<img')
  expect(html).toContain('Product image unavailable')
})
