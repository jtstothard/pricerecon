import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { MoreVerticalIcon } from "lucide-react"

export interface ActionMenuItem {
  label: string
  onClick: () => void
  variant?: 'default' | 'destructive' | 'danger'
  icon?: string
}

interface ActionMenuProps {
  'aria-label': string
  items: ActionMenuItem[]
}

export default function ActionMenu({ 'aria-label': ariaLabel, items }: ActionMenuProps) {
  return (
    <DropdownMenu>
      <DropdownMenuTrigger render={
        <button
          type="button"
          className="inline-flex items-center justify-center rounded-md p-1 hover:bg-muted transition-colors outline-none focus-visible:ring-2 focus-visible:ring-ring"
          aria-label={ariaLabel}
        >
          <MoreVerticalIcon className="h-4 w-4" />
        </button>
      } />
      <DropdownMenuContent align="end">
        {items.map((item, index) => {
          const variant = item.variant === 'danger' ? 'destructive' : item.variant
          return (
            <DropdownMenuItem
              key={index}
              onClick={() => {
                item.onClick()
              }}
              variant={variant}
              className="flex items-center gap-2"
            >
              {item.icon && <span className="text-sm">{item.icon}</span>}
              {item.label}
            </DropdownMenuItem>
          )
        })}
      </DropdownMenuContent>
    </DropdownMenu>
  )
}