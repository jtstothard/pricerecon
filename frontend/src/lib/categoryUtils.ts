/** Format a raw category string (e.g. "gpu", "cpu") into display-friendly sentence case. */

const CATEGORY_LABELS: Record<string, string> = {
  gpu: 'GPU',
  cpu: 'CPU',
  ram: 'RAM',
  ssd: 'SSD',
  hdd: 'HDD',
  psu: 'PSU',
  motherboard: 'Motherboard',
  case: 'Case',
  cooler: 'Cooler',
  monitor: 'Monitor',
  keyboard: 'Keyboard',
  mouse: 'Mouse',
  headset: 'Headset',
  speaker: 'Speaker',
  webcam: 'Webcam',
  other: 'Other',
}

export function formatCategory(category: string | null | undefined): string {
  if (!category || !category.trim()) return 'Uncategorized'
  const key = category.trim().toLowerCase()
  if (CATEGORY_LABELS[key]) return CATEGORY_LABELS[key]
  // Sentence case for unknown values
  return category.trim().replace(/(^|[_\s])(\w)/g, (_, sep, char) => sep === '_' ? ' ' + char.toUpperCase() : char.toUpperCase())
}
