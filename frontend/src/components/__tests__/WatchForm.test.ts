import { describe, it, expect } from 'vitest'
import { buildWatchCreatePayload, buildWatchEditPayload, formDataFromWatch, validateWatchForm } from '../../lib/watchPayload'
import type { WatchSummary } from '../watchTypes'
import { createElement } from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import WatchForm from '../WatchForm'

const savedWatch: WatchSummary = {
  id: 7,
  name: 'Saved wristwatch search',
  query: 'fallback merchant query',
  category: null,
  display_title: 'My compact colourful choices',
  synonym_groups: [['ML05', 'ML05B'], ['blue', 'mint']],
  source_queries: { cex: ' (ML05 OR "ML05B") -parts  ', scan: ' saved disabled query  ' },
  sources: [
    { connector: 'cex', enabled: true, config: { region: 'UK' } },
    { connector: 'scan', enabled: false, config: { category: 'watches' } },
  ],
  filters: {
    price_max: '100.00',
    currency: 'EUR',
    condition_filter: { conditions: ['new'], dedup_enabled: true },
    exclude_patterns: ['broken'],
    spec_match: { excluded_title_terms: ['parts'], synonym_groups: [['Militado']], ram_gb: 16 },
    min_price_gbp: 20,
    component_subject_pattern: 'watch',
    enforce_component_pattern: false,
    enforce_price_floor: false,
    min_seller_feedback: 100,
    min_seller_feedback_pct: '99.5',
  },
  schedule: { interval: '30m', timezone: 'Europe/London', time_window: { start: '09:00', end: '18:00', days: ['mon'] } },
  grouping: { enabled: true, product_key: 'ML05' },
  notifications: {
    events: ['price_drop'], channels: ['webhook', 'telegram', 'discord'],
    webhook_url: 'https://notify.invalid/hook', telegram_bot_token: 'offline-placeholder',
    telegram_chat_id: 'offline-chat', discord_webhook_url: 'https://discord.invalid/hook',
  },
  enabled: false,
  last_check_at: null,
}

describe('saved watch edits', () => {
  it('changes only the display title while retaining all other saved intent', () => {
    const form = formDataFromWatch(savedWatch)
    const payload = buildWatchEditPayload({ ...form, display_title: 'Edited label' }, savedWatch)
    const { id, last_check_at, ...config } = savedWatch
    expect(payload).toEqual({ ...config, display_title: 'Edited label' })
    expect(savedWatch.display_title).toBe('My compact colourful choices')
  })

  it('renders the saved custom interval as the selected option', () => {
    const html = renderToStaticMarkup(createElement(WatchForm, {
      open: true, editingWatch: savedWatch, onClose: () => {}, onSaved: () => {},
    }))
    expect(html).toContain('<option value="30m" selected="">Every 30m (saved)</option>')
  })

  it('preserves untouched raw overrides even when another connector query is edited', () => {
    const saved = { ...savedWatch, source_queries: { ...savedWatch.source_queries, unavailable: '  ' } }
    const form = formDataFromWatch(saved)
    form.source_queries = { ...form.source_queries, cex: '  (ML05 OR mint) -parts  ' }
    expect(buildWatchEditPayload(form, saved).source_queries).toEqual({
      cex: '  (ML05 OR mint) -parts  ', scan: ' saved disabled query  ', unavailable: '  ',
    })
  })

  it('allows a title edit when every saved source is already disabled', () => {
    const saved = { ...savedWatch, sources: savedWatch.sources.map(source => ({ ...source, enabled: false })) }
    const form = { ...formDataFromWatch(saved), display_title: 'Paused intent' }
    expect(validateWatchForm(form, saved)).toBeNull()
    expect(buildWatchEditPayload(form, saved).sources).toEqual(saved.sources)
  })

  it('applies intentional source, query and filter edits without resetting hidden configuration', () => {
    const form = formDataFromWatch(savedWatch)
    const payload = buildWatchEditPayload({
      ...form,
      name: 'Changed search', query: 'new fallback', category: 'other', interval: '4h', enabled: true,
      sources: ['scan', 'ebay'],
      filters: { price_max: '80.50', condition: ['refurbished'] },
      synonym_groups: [[' ML05 ', ' mint ']], excluded_terms: [' broken ', ' damaged '],
      source_queries: { ...form.source_queries, scan: ' (ML05 OR mint) ', cex: '' },
    }, savedWatch)
    expect(payload).toMatchObject({
      name: 'Changed search', query: 'new fallback', category: null, enabled: true,
      synonym_groups: [['ML05', 'mint']],
      source_queries: { scan: ' (ML05 OR mint) ' },
      sources: [
        { connector: 'cex', enabled: false, config: { region: 'UK' } },
        { connector: 'scan', enabled: true, config: { category: 'watches' } },
        { connector: 'ebay', enabled: true },
      ],
      schedule: { interval: '4h', timezone: 'Europe/London', time_window: { start: '09:00', end: '18:00', days: ['mon'] } },
      filters: {
        ...savedWatch.filters,
        price_max: 80.5,
        condition_filter: { conditions: ['refurbished'], dedup_enabled: true },
        exclude_patterns: ['broken', 'damaged'],
      },
      notifications: savedWatch.notifications, grouping: savedWatch.grouping,
    })
    expect(payload.source_queries).not.toHaveProperty('cex')
  })

  it('clears owned filters and overrides intentionally while retaining the underlying spec rules', () => {
    const form = formDataFromWatch(savedWatch)
    const payload = buildWatchEditPayload({
      ...form, category: 'gpu', display_title: '', synonym_groups: [], excluded_terms: [],
      filters: { price_max: '', condition: [] }, advancedMode: false,
    }, savedWatch)
    expect(payload).toMatchObject({
      category: 'gpu', display_title: null, synonym_groups: [], source_queries: {},
      filters: {
        price_max: null, condition_filter: { conditions: [], dedup_enabled: true }, exclude_patterns: [],
        spec_match: { excluded_title_terms: ['parts'], synonym_groups: [['Militado']], ram_gb: 16 },
      },
    })
    // Choosing simple mode removes raw overrides for both creation and editing.
    expect(buildWatchCreatePayload({ ...form, advancedMode: false }).source_queries).toEqual({})
  })

  it('keeps form term edits separate from the saved watch until submission', () => {
    const form = formDataFromWatch(savedWatch)
    form.synonym_groups[0][0] = 'Changed'
    form.excluded_terms.push('damaged')
    form.filters.condition.push('refurbished')
    expect(savedWatch.synonym_groups).toEqual([['ML05', 'ML05B'], ['blue', 'mint']])
    expect(savedWatch.filters?.exclude_patterns).toEqual(['broken'])
    expect(savedWatch.filters?.condition_filter?.conditions).toEqual(['new'])
  })

  it('changes only enabled state when pausing or resuming a watch', () => {
    const form = formDataFromWatch(savedWatch)
    const { id, last_check_at, ...config } = savedWatch
    expect(buildWatchEditPayload({ ...form, enabled: true }, savedWatch)).toEqual({ ...config, enabled: true })
    expect(validateWatchForm({ ...form, sources: [] })).toBe('Select at least one source.')
  })
})

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

  it('validates advanced mode: allows an empty per-connector query to use the default', () => {
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
    expect(error).toBeNull()
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
