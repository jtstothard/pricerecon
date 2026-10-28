import { expect, it } from 'vitest'
import { parseDiscoveryFeed } from '../../lib/discovery'
import captured from './image-feed.json'

const validImage = {
  kind: 'photo', url: 'https://assets.invalid/control.jpg', attribution: 'Fixture author',
  provenance: 'Synthetic contract only', permission_reference: 'fixture-rights',
  identity_reference: 'fixture-depiction', source_listing_id: captured.candidates[0].source_listing_id,
  depicts_exact_watch: true,
}
const feedWith = (image: unknown) => ({ ...captured, candidates: [
  { ...captured.candidates[0], image }, captured.candidates[1],
] })

it.each([
  'https://assets.invalid:999999/control.jpg', 'https://assets.invalid:no/control.jpg',
  'https://assets.invalid\\evil/control.jpg', 'https://%zz/control.jpg',
  'https://256.256.256.256/control.jpg',
])('keeps the lead and sibling with an explicit placeholder for %s', url => {
  const feed = parseDiscoveryFeed(feedWith({ ...validImage, url }))
  expect(feed.candidates).toHaveLength(2)
  expect(feed.candidates[0].source_listing_id).toBe(captured.candidates[0].source_listing_id)
  expect(feed.candidates[0].image).toMatchObject({ kind: 'original_placeholder', url: null })
  expect(feed.candidates[1].source_listing_id).toBe(captured.candidates[1].source_listing_id)
})

it.each([null, {}, { ...validImage, attribution: null }, { ...validImage, depicts_exact_watch: false }])(
  'isolates malformed persisted image metadata', image => {
    expect(parseDiscoveryFeed(feedWith(image)).candidates[0].image.kind).toBe('original_placeholder')
  },
)

it.each(['photo', 'illustration'])('retains valid %s attribution', kind => {
  expect(parseDiscoveryFeed(feedWith({ ...validImage, kind })).candidates[0].image)
    .toMatchObject({ kind, attribution: 'Fixture author', permission_reference: 'fixture-rights' })
})

it('still rejects invalid qualification even with a malformed image', () => {
  const feed = feedWith(null)
  feed.candidates[0].alert_eligible = true
  expect(() => parseDiscoveryFeed(feed)).toThrow('Unsupported qualified discovery claim')
})

const referenceImage = {
  kind: 'remote_reference', url: 'https://assets.invalid/reference.jpg?v=123&width=800&format=webp',
  attribution: 'Original reviewer', provenance: 'Public review reference',
  source_context_url: 'https://example.org/review', configuration_note: '39mm blue; target unresolved',
  source_listing_id: captured.candidates[0].source_listing_id, depicts_exact_watch: false,
}
it('decodes and renders an honest remote reference without upgrading qualification', async () => {
  const candidate = parseDiscoveryFeed(feedWith(referenceImage)).candidates[0]
  expect(candidate.image).toMatchObject({ kind: 'remote_reference', configuration_note: '39mm blue; target unresolved' })
  const invalid = feedWith(referenceImage)
  invalid.candidates[0].alert_eligible = true
  expect(() => parseDiscoveryFeed(invalid)).toThrow()
  const { createElement } = await import('react')
  const { renderToStaticMarkup } = await import('react-dom/server')
  const { default: DiscoveryImage } = await import('../discovery/DiscoveryImage')
  const html = renderToStaticMarkup(createElement(DiscoveryImage, { image: candidate.image }))
  expect(html).toContain('Remote reference image')
  expect(html).toContain('39mm blue; target unresolved')
  expect(html).toContain('href="https://example.org/review"')
  expect(html).toContain('<img')
  expect(html).not.toContain('Permission:')
})
it.each(['?&&', '?token=secret', '?width=800&X-Amz-Signature=secret', '?v=abc', '?format=1500w&sig=x', '?width=800&width=900'])('rejects unsafe remote queries %s', query => {
  expect(parseDiscoveryFeed(feedWith({ ...referenceImage, url: `https://assets.invalid/a.jpg${query}` })).candidates[0].image.kind).toBe('original_placeholder')
})
it.each(['https://assets.invalid:999999/a', 'https://%zz/a', 'https://assets.invalid/a?token=x'])('isolates malformed remote reference %s', url => {
  expect(parseDiscoveryFeed(feedWith({ ...referenceImage, url })).candidates).toHaveLength(2)
  expect(parseDiscoveryFeed(feedWith({ ...referenceImage, url })).candidates[0].image.kind).toBe('original_placeholder')
})

it.each(['HTTPS', 'HtTpS'])('retains case-insensitive %s references and source context', scheme => {
  const url = `${scheme}://assets.invalid/control.jpg?v=123&width=800&format=webp`
  const source_context_url = `${scheme}://example.org/review`
  const feed = parseDiscoveryFeed(feedWith({ ...referenceImage, url, source_context_url }))
  expect(feed.candidates).toHaveLength(2)
  expect(feed.candidates[0].image).toMatchObject({ kind: 'remote_reference', url, source_context_url })
})
