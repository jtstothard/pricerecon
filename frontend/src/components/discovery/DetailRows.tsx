import type { ReactNode } from 'react'

/** Label/value pairs keep captured facts readable without inventing interpretation. */
export function DetailRows({ rows }: { rows: [string, ReactNode][] }) {
  return <dl className="discovery-detail-rows">{rows.map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{value ?? 'Unknown'}</dd></div>)}</dl>
}
