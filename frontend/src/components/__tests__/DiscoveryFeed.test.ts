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
