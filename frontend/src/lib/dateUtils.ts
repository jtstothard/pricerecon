/**
 * Safe date formatting that handles invalid dates gracefully
 */
export function formatDateTime(value: string | null | undefined): string {
  if (!value) return '—'

  const date = new Date(value)

  // Check if the date is invalid
  if (Number.isNaN(date.getTime())) {
    return 'Invalid Date'
  }

  return date.toLocaleString()
}

/**
 * Safe date formatting with relative time (e.g., "2 hours ago")
 */
export function formatRelativeTime(value: string | null | undefined): string {
  if (!value) return '—'

  const date = new Date(value)

  // Check if the date is invalid
  if (Number.isNaN(date.getTime())) {
    return 'Invalid Date'
  }

  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffSeconds = Math.floor(diffMs / 1000)
  const diffMinutes = Math.floor(diffSeconds / 60)
  const diffHours = Math.floor(diffMinutes / 60)
  const diffDays = Math.floor(diffHours / 24)

  if (diffSeconds < 60) return 'just now'
  if (diffMinutes < 60) return `${diffMinutes} minute${diffMinutes !== 1 ? 's' : ''} ago`
  if (diffHours < 24) return `${diffHours} hour${diffHours !== 1 ? 's' : ''} ago`
  if (diffDays < 7) return `${diffDays} day${diffDays !== 1 ? 's' : ''} ago`

  return date.toLocaleDateString()
}