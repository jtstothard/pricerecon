import { describe, it, expect } from 'vitest'
import { buildWatchCreatePayload } from '../../lib/watchPayload'

describe('WatchForm payload transformation', () => {
  it('transforms sources from string[] to object[] with connector field', () => {
    const formData = {
      name: 'Test Watch',
      query: 'RTX 4090',
      category: 'gpu',
      interval: '4h',
      enabled: true,
      sources: ['ebay', 'cex'],
      filters: {
        price_max: '',
        condition: ['new', 'refurbished'],
      },
    }

    const payload = buildWatchCreatePayload(formData)

    expect(payload.sources).toEqual([
      { connector: 'ebay', enabled: true },
      { connector: 'cex', enabled: true },
    ])
  })

  it('nests interval under schedule object', () => {
    const formData = {
      name: 'Test Watch',
      query: 'RTX 4090',
      category: 'gpu',
      interval: '4h',
      enabled: true,
      sources: ['ebay'],
      filters: {
        price_max: '',
        condition: ['new'],
      },
    }

    const payload = buildWatchCreatePayload(formData)

    expect(payload.schedule).toEqual({
      interval: '4h',
      timezone: 'UTC',
    })
    expect(payload).not.toHaveProperty('interval')
  })

  it('nests condition list under filters.condition_filter.conditions', () => {
    const formData = {
      name: 'Test Watch',
      query: 'RTX 4090',
      category: 'gpu',
      interval: '4h',
      enabled: true,
      sources: ['ebay'],
      filters: {
        price_max: '',
        condition: ['new', 'refurbished', 'used_like_new'],
      },
    }

    const payload = buildWatchCreatePayload(formData)

    expect(payload.filters.condition_filter).toEqual({
      conditions: ['new', 'refurbished', 'used_like_new'],
      dedup_enabled: false,
    })
    expect(payload.filters).not.toHaveProperty('condition')
  })

  it('converts price_max string to number or null', () => {
    const formDataWithPrice = {
      name: 'Test Watch',
      query: 'RTX 4090',
      category: 'gpu',
      interval: '4h',
      enabled: true,
      sources: ['ebay'],
      filters: {
        price_max: '1000.00',
        condition: ['new'],
      },
    }

    const payloadWithPrice = buildWatchCreatePayload(formDataWithPrice)
    expect(payloadWithPrice.filters.price_max).toBe(1000.0)

    const formDataWithoutPrice = {
      name: 'Test Watch',
      query: 'RTX 4090',
      category: 'gpu',
      interval: '4h',
      enabled: true,
      sources: ['ebay'],
      filters: {
        price_max: '',
        condition: ['new'],
      },
    }

    const payloadWithoutPrice = buildWatchCreatePayload(formDataWithoutPrice)
    expect(payloadWithoutPrice.filters.price_max).toBeNull()
  })

  it('produces complete payload matching backend schema', () => {
    const formData = {
      name: 'GPU Watch',
      query: 'RTX 4090 24GB',
      category: 'gpu',
      interval: '8h',
      enabled: true,
      sources: ['ebay', 'cex', 'amazon'],
      filters: {
        price_max: '1500.00',
        condition: ['new', 'refurbished'],
      },
    }

    const payload = buildWatchCreatePayload(formData)

    // Verify complete structure
    expect(payload).toMatchObject({
      name: 'GPU Watch',
      query: 'RTX 4090 24GB',
      category: 'gpu',
      enabled: true,
      sources: [
        { connector: 'ebay', enabled: true },
        { connector: 'cex', enabled: true },
        { connector: 'amazon', enabled: true },
      ],
      schedule: {
        interval: '8h',
        timezone: 'UTC',
      },
      filters: {
        price_max: 1500.0,
        condition_filter: {
          conditions: ['new', 'refurbished'],
          dedup_enabled: false,
        },
        currency: 'GBP',
      },
      grouping: { enabled: false },
      notifications: {
        events: ['new_listing', 'price_drop', 'stock_change'],
        channels: ['webhook'],
      },
    })
  })
})