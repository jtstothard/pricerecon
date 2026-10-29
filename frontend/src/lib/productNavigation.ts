export function productNavigation(
  path: string,
  view?: string,
  search = typeof window === 'undefined' ? '' : window.location.search
) {
  const input = new URLSearchParams(search)
  const output = new URLSearchParams()
  const mode = input.get('walkthrough')
  if (mode === 'ticket12' || mode === 'ticket12-local') output.set('walkthrough', mode)
  if (view) output.set('view', view)
  return path + (output.size ? `?${output}` : '')
}
