interface Source {
  name: string
  status: string
  last_error: string | null
}

interface SourceHealthProps {
  sources: Source[]
}

export default function SourceHealth({ sources }: SourceHealthProps) {
  if (sources.length === 0) return null

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'healthy': return 'green'
      case 'error': return 'red'
      case 'disabled': return 'gray'
      default: return 'gray'
    }
  }

  return (
    <div className="source-health">
      <h3>Source Health</h3>
      <div className="source-grid">
        {sources.map(source => (
          <div key={source.name} className="source-card">
            <div className="source-header">
              <strong>{source.name}</strong>
              <span
                className="status-indicator"
                style={{ backgroundColor: getStatusColor(source.status) }}
              />
            </div>
            <p className="source-status">{source.status}</p>
            {source.last_error && (
              <p className="source-error">{source.last_error}</p>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
