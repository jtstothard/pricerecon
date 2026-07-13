import * as React from "react"
import { SearchIcon, CheckIcon } from "lucide-react"
import { cn } from "@/lib/utils"
import {
  InputGroup,
  InputGroupAddon,
} from "@/components/ui/input-group"

interface SourceSummary {
  connector: string
  name: string
  status: string
  last_error: string | null
}

interface SearchableMultiselectProps {
  sources: SourceSummary[]
  selectedSources: string[]
  onSelectionChange: (sources: string[]) => void
  loading?: boolean
  error?: string | null
}

export function SearchableMultiselect({
  sources,
  selectedSources,
  onSelectionChange,
  loading = false,
  error = null,
}: SearchableMultiselectProps) {
  const [searchQuery, setSearchQuery] = React.useState('')

  const toggleSource = (connector: string) => {
    const newSelection = selectedSources.includes(connector)
      ? selectedSources.filter(s => s !== connector)
      : [...selectedSources, connector]
    onSelectionChange(newSelection)
  }

  const removeSource = (connector: string, e: React.MouseEvent) => {
    e.stopPropagation()
    onSelectionChange(selectedSources.filter(s => s !== connector))
  }

  const filteredSources = sources.filter(source =>
    source.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    source.connector.toLowerCase().includes(searchQuery.toLowerCase())
  )

  return (
    <div className="space-y-2">
      {selectedSources.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {selectedSources.map(connector => {
            const source = sources.find(s => s.connector === connector)
            return (
              <span
                key={connector}
                className="inline-flex items-center gap-1 rounded-full bg-primary/10 text-primary px-2 py-0.5 text-xs"
              >
                {source?.name || connector}
                <button
                  type="button"
                  onClick={(e) => removeSource(connector, e)}
                  className="ml-1 hover:text-primary-foreground"
                  aria-label={`Remove ${source?.name || connector}`}
                >
                  ×
                </button>
              </span>
            )
          })}
          <button
            type="button"
            onClick={() => onSelectionChange([])}
            className="text-xs text-muted-foreground hover:text-foreground"
          >
            Clear
          </button>
        </div>
      )}

      <div className="flex flex-col rounded-xl bg-popover p-1 text-popover-foreground">
        <div className="p-1 pb-0">
          <InputGroup className="h-8! rounded-lg! border-input/30 bg-input/30 shadow-none! *:data-[slot=input-group-addon]:pl-2!">
            <input
              data-slot="command-input"
              className="w-full rounded-md bg-transparent px-2 py-1 text-sm outline-none disabled:cursor-not-allowed disabled:opacity-50"
              placeholder={selectedSources.length === 0 ? "Select sources..." : "Search sources..."}
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              disabled={loading}
            />
            <InputGroupAddon>
              <SearchIcon className="size-4 shrink-0 opacity-50" />
            </InputGroupAddon>
          </InputGroup>
        </div>
        <div data-slot="command-list" className="no-scrollbar max-h-72 scroll-py-1 overflow-x-hidden overflow-y-auto outline-none">
          {loading ? (
            <div className="py-6 text-center text-sm">Loading sources...</div>
          ) : error ? (
            <div className="py-6 text-center text-sm text-destructive">{error}</div>
          ) : filteredSources.length === 0 ? (
            <div className="py-6 text-center text-sm">No sources found</div>
          ) : (
            <div data-slot="command-group" className="overflow-hidden p-1 text-foreground">
              {filteredSources.map(source => (
                <button
                  key={source.connector}
                  type="button"
                  data-slot="command-item"
                  className="group/command-item relative flex w-full cursor-default items-center gap-2 rounded-sm px-2 py-1.5 text-sm outline-none select-none hover:bg-muted"
                  onClick={() => toggleSource(source.connector)}
                >
                  <div className={cn(
                    "flex h-4 w-4 items-center justify-center rounded border",
                    selectedSources.includes(source.connector)
                      ? "border-primary bg-primary text-primary-foreground"
                      : "border-input"
                  )}>
                    {selectedSources.includes(source.connector) && (
                      <CheckIcon className="h-3 w-3" />
                    )}
                  </div>
                  <div className="flex flex-col text-left">
                    <span className="font-medium">{source.name}</span>
                    <span className="text-xs text-muted-foreground">{source.connector}</span>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {!loading && sources.length > 0 && (
        <div className="text-xs text-muted-foreground">
          {selectedSources.length} of {sources.length} selected
        </div>
      )}
    </div>
  )
}