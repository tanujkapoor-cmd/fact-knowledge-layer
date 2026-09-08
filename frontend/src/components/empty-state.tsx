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
    <div className="grid min-h-64 place-items-center rounded-[4px] border border-dashed border-border bg-card p-8 text-center">
      <div className="max-w-lg">
        <div className="mx-auto mb-4 grid size-11 place-items-center border border-primary bg-primary text-primary-foreground">
          <Icon className="size-5" aria-hidden="true" />
        </div>
        <h3 className="text-base font-semibold text-foreground">{title}</h3>
        <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-muted-foreground">
          {description}
        </p>
        <p className="mt-3 font-mono text-[11px] uppercase tracking-[0.12em] text-slate-500">
          {detail}
        </p>
      </div>
    </div>
  )
}
