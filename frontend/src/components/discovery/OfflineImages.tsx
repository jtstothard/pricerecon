import { createContext, useEffect, useState, type ReactNode } from 'react'
import { record, text } from '../../lib/discovery'

// null means ordinary application rendering. An empty map in private mode must
// abstain, never fall through to remote merchant requests while loading/failing.
export const OfflineImageContext = createContext<ReadonlyMap<string, string> | null>(null)

export function parseOfflineImages(value: unknown): ReadonlyMap<string, string> {
  const data = record(value)
  if (data.fixture !== 'ticket12-private-images-v1' || !Array.isArray(data.assets))
    throw new Error('Wrong private image fixture')
  return new Map(
    data.assets.map((value) => {
      const asset = record(value),
        original = text(asset.source_url),
        local = text(asset.local_url)
      const url = new URL(original)
      if (
        url.protocol !== 'https:' ||
        url.username ||
        url.password ||
        url.search ||
        url.hash ||
        !/^\/api\/offline-watch-images\/[a-f0-9]{64}\.(png|jpg)$/.test(local)
      )
        throw new Error('Invalid private image route')
      return [original, local]
    })
  )
}

export function OfflineImages({ children }: { children: ReactNode }) {
  const [mode] = useState(() => new URLSearchParams(window.location.search).get('walkthrough'))
  const enabled = mode === 'ticket12-local'
  const [assets, setAssets] = useState<ReadonlyMap<string, string>>(new Map())
  const [error, setError] = useState('')
  useEffect(() => {
    if (!enabled) return
    const controller = new AbortController()
    fetch('/api/offline-watch-images', { signal: controller.signal, cache: 'no-store' })
      .then((response) => {
        if (!response.ok) throw new Error('Private image fixture unavailable')
        return response.json()
      })
      .then((value) => setAssets(parseOfflineImages(value)))
      .catch(() => {
        if (!controller.signal.aborted)
          setError(
            'Private images unavailable. Start the marked ticket12 fixture; remote images remain disabled.'
          )
      })
    return () => controller.abort()
  }, [enabled])
  return (
    <OfflineImageContext.Provider value={enabled ? assets : null}>
      {mode === 'ticket12' && (
        <aside aria-label="Remote reference walkthrough">
          <section>
            <h3>Private reference image session</h3>
            <p>
              Images load from original public sources; no licence claimed. Militado/San Martin
              targets remain unresolved; Merkur image missing. References do not qualify prices.
            </p>
          </section>
        </aside>
      )}
      {enabled && (
        <aside aria-label="Private image walkthrough">
          <p>
            Local-only private walkthrough (remote images disabled). Real Casio reference photos.
            Four watch images remain unavailable.
          </p>
          {error && <p role="alert">{error}</p>}
        </aside>
      )}
      {children}
    </OfflineImageContext.Provider>
  )
}
