import { describe, it, expect } from 'vitest'
import { buildWatchCreatePayload, validateWatchForm } from '../../lib/watchPayload'

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
      display_title: '',
      synonym_groups: [],
      excluded_terms: [],
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
      display_title: '',
      synonym_groups: [],
      excluded_terms: [],
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
      display_title: '',
      synonym_groups: [],
      excluded_terms: [],
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
      display_title: '',
      synonym_groups: [],
      excluded_terms: [],
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
      display_title: '',
      synonym_groups: [],
      excluded_terms: [],
    }

    const payloadWithoutPrice = buildWatchCreatePayload(formDataWithoutPrice)
    expect(payloadWithoutPrice.filters.price_max).toBeNull()
  })

  it('handles display_title field - non-empty value', () => {
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
      display_title: 'Custom Display Name',
      synonym_groups: [],
      excluded_terms: [],
    }

    const payload = buildWatchCreatePayload(formData)
    expect(payload.display_title).toBe('Custom Display Name')
  })

  it('handles display_title field - empty value becomes null', () => {
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
      display_title: '   ', // whitespace only
      synonym_groups: [],
      excluded_terms: [],
    }

    const payload = buildWatchCreatePayload(formData)
    expect(payload.display_title).toBeNull()
  })

  it('handles synonym_groups field', () => {
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
      display_title: 'High-End GPU Watch',
      synonym_groups: [
        ['RTX', 'Radeon'],
        ['4090', 'RX 7900'],
      ],
      excluded_terms: ['broken', 'for parts', 'not working'],
      source_queries: {},
      advancedMode: false,
    }

    const payload = buildWatchCreatePayload(formData)
    expect(payload.synonym_groups).toEqual([
      ['RTX', 'Radeon'],
      ['4090', 'RX 7900'],
    ])
  })

  it('handles excluded_terms field', () => {
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
      display_title: '',
      synonym_groups: [],
      excluded_terms: ['broken', 'for parts'],
    }

    const payload = buildWatchCreatePayload(formData)
    expect(payload.filters.exclude_patterns).toEqual(['broken', 'for parts'])
  })

  it('produces complete payload matching backend schema with new fields', () => {
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
      display_title: 'High-End GPU Watch',
      synonym_groups: [
        ['RTX', 'Radeon'],
        ['4090', 'RX 7900'],
      ],
      excluded_terms: ['broken', 'for parts', 'not working'],
      source_queries: {},
      advancedMode: false,
    }

    const payload = buildWatchCreatePayload(formData)

    // Verify complete structure
    expect(payload).toMatchObject({
      name: 'GPU Watch',
      query: 'RTX 4090 24GB',
      category: 'gpu',
      display_title: 'High-End GPU Watch',
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
        exclude_patterns: ['broken', 'for parts', 'not working'],
      },
      grouping: { enabled: false },
      notifications: {
        events: ['new_listing', 'price_drop', 'stock_change'],
        channels: ['webhook'],
      },
    })
  })

  it('handles advanced mode: passes source_queries in payload', () => {
    const formData = {
      name: 'Test Watch',
      query: 'RTX 4090',
      category: 'gpu',
      interval: '4h',
      enabled: true,
      sources: ['ebay', 'cex'],
      filters: {
        price_max: '',
        condition: ['new'],
      },
      display_title: '',
      synonym_groups: [],
      excluded_terms: [],
      source_queries: {
        ebay: 'RTX 4090 24GB -broken -for parts',
        cex: 'RTX 4090 24GB',
      },
      advancedMode: true,
    }

    const payload = buildWatchCreatePayload(formData)

    expect(payload.source_queries).toEqual({
      ebay: 'RTX 4090 24GB -broken -for parts',
      cex: 'RTX 4090 24GB',
    })
  })

  it('handles advanced mode: excludes empty source_queries values', () => {
    const formData = {
      name: 'Test Watch',
      query: 'RTX 4090',
      category: 'gpu',
      interval: '4h',
      enabled: true,
      sources: ['ebay', 'cex', 'amazon'],
      filters: {
        price_max: '',
        condition: ['new'],
      },
      display_title: '',
      synonym_groups: [],
      excluded_terms: [],
      source_queries: {
        ebay: 'RTX 4090 24GB',
        cex: '',  // Empty - should be excluded
        amazon: 'RTX 4090 24GB used',
      },
      advancedMode: true,
    }

    const payload = buildWatchCreatePayload(formData)

    expect(payload.source_queries).toEqual({
      ebay: 'RTX 4090 24GB',
      amazon: 'RTX 4090 24GB used',
    })
    expect(payload.source_queries).not.toHaveProperty('cex')
  })

  it('handles advanced mode: whitespace-only query treated as empty', () => {
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
      display_title: '',
      synonym_groups: [],
      excluded_terms: [],
      source_queries: {
        ebay: '   ',  // Whitespace only
      },
      advancedMode: true,
    }

    const payload = buildWatchCreatePayload(formData)

    expect(payload.source_queries).toEqual({})
  })

  it('validates advanced mode: rejects empty per-connector query', () => {
    const formData = {
      name: 'Test Watch',
      query: 'RTX 4090',
      category: 'gpu',
      interval: '4h',
      enabled: true,
      sources: ['ebay', 'cex'],
      filters: {
        price_max: '',
        condition: ['new'],
      },
      display_title: '',
      synonym_groups: [],
      excluded_terms: [],
      source_queries: {
        ebay: 'RTX 4090 24GB',
        cex: '',  // Empty string should fail validation
      },
      advancedMode: true,
    }

    const error = validateWatchForm(formData)
    expect(error).toContain('cex')
    expect(error).toContain('empty custom query')
  })

  it('validates advanced mode: allows empty field to use default query', () => {
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
      display_title: '',
      synonym_groups: [],
      excluded_terms: [],
      source_queries: {},  // Empty record means use default for all
      advancedMode: true,
    }

    const error = validateWatchForm(formData)
    expect(error).toBeNull()
  })

  it('validates advanced mode: disabled mode does not check source_queries', () => {
    const formData = {
      name: 'Test Watch',
      query: 'RTX 4090',
      category: 'gpu',
      interval: '4h',
      enabled: true,
      sources: ['ebay', 'cex'],
      filters: {
        price_max: '',
        condition: ['new'],
      },
      display_title: '',
      synonym_groups: [],
      excluded_terms: [],
      source_queries: {
        ebay: '',  // Empty but validation should not run
        cex: '',
      },
      advancedMode: false,
    }

    const error = validateWatchForm(formData)
    expect(error).toBeNull()
  })

  it('backwards compatible: simple mode (advancedMode false) does not populate source_queries', () => {
    const formData = {
      name: 'Test Watch',
      query: 'RTX 4090',
      category: 'gpu',
      interval: '4h',
      enabled: true,
      sources: ['ebay', 'cex'],
      filters: {
        price_max: '',
        condition: ['new'],
      },
      display_title: '',
      synonym_groups: [],
      excluded_terms: [],
      source_queries: {},
      advancedMode: false,
    }

    const payload = buildWatchCreatePayload(formData)

    expect(payload.source_queries).toEqual({})
    expect(payload).toMatchObject({
      name: 'Test Watch',
      query: 'RTX 4090',
      sources: [
        { connector: 'ebay', enabled: true },
        { connector: 'cex', enabled: true },
      ],
    })
  })

  it('advanced mode preserves raw query strings exactly', () => {
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
      display_title: '',
      synonym_groups: [],
      excluded_terms: [],
      source_queries: {
        ebay: 'RTX 4090 24GB -broken -"for parts" 2|4|8GB',  // Special chars preserved
      },
      advancedMode: true,
    }

    const payload = buildWatchCreatePayload(formData)

    expect(payload.source_queries.ebay).toBe('RTX 4090 24GB -broken -"for parts" 2|4|8GB')
  })
})