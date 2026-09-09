import type { LucideIcon } from "lucide-react"

export function EmptyState({
  icon: Icon,
  title,
  description,
  detail,
}: {
  icon: LucideIcon
  title: string
  description: string
  detail: string
}) {
  return (
    <div className="grid min-h-56 place-items-center border border-border bg-card p-5 sm:p-7">
      <div className="w-full max-w-xl border-y border-border py-5">
        <div className="flex items-start gap-4">
          <div className="grid size-9 shrink-0 place-items-center border border-primary bg-primary text-primary-foreground">
            <Icon className="size-4" aria-hidden="true" />
          </div>
          <div className="min-w-0 text-left">
            <p className="data-label">Workflow gate · awaiting record</p>
            <h3 className="mt-1.5 text-sm font-semibold text-foreground">{title}</h3>
            <p className="mt-1 max-w-md text-xs leading-5 text-muted-foreground">
              {description}
            </p>
          </div>
        </div>
        <p className="mt-5 border-t border-border pt-2.5 font-mono text-[9px] uppercase tracking-[0.07em] text-muted-foreground">
          {detail}
        </p>
      </div>
    </div>
  )
}
