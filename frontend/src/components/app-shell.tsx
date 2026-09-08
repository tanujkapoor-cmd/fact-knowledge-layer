import type { ReactNode } from "react"
import {
  ExternalLink,
  FileStack,
  GitCompareArrows,
  Layers3,
  ListTree,
  Settings2,
} from "lucide-react"

import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"

export type ViewId = "documents" | "facts" | "relationships"

const NAVIGATION = [
  { id: "documents", label: "Documents", caption: "Ingest and track", icon: FileStack },
  { id: "facts", label: "Fact ledger", caption: "Verify every claim", icon: ListTree },
  {
    id: "relationships",
    label: "Relationships",
    caption: "Audit each decision",
    icon: GitCompareArrows,
  },
] satisfies Array<{ id: ViewId; label: string; caption: string; icon: typeof FileStack }>

interface AppShellProps {
  activeView: ViewId
  onViewChange: (view: ViewId) => void
  apiState: "checking" | "ready" | "offline"
  apiDocsUrl: string
  children: ReactNode
}

function Navigation({
  activeView,
  onViewChange,
  compact = false,
}: {
  activeView: ViewId
  onViewChange: (view: ViewId) => void
  compact?: boolean
}) {
  return (
    <nav
      aria-label="Primary navigation"
      className={cn("grid gap-1", compact && "grid-cols-3")}
    >
      {NAVIGATION.map((item) => {
        const active = activeView === item.id
        return (
          <button
            key={item.id}
            type="button"
            className={cn(
              "group relative flex min-h-12 cursor-pointer items-center gap-3 rounded-lg px-3 text-left outline-none transition-colors focus-visible:ring-2 focus-visible:ring-ring",
              active
                ? "bg-secondary text-foreground"
                : "text-muted-foreground hover:bg-muted/55 hover:text-foreground",
              compact && "min-w-0 justify-center px-2 sm:justify-start",
            )}
            aria-current={active ? "page" : undefined}
            onClick={() => onViewChange(item.id)}
          >
            <span
              className={cn(
                "grid size-8 shrink-0 place-items-center rounded-md border transition-colors",
                active
                  ? "border-accent/25 bg-accent/8 text-accent"
                  : "border-transparent text-slate-500 group-hover:text-slate-300",
              )}
            >
              <item.icon className="size-4" aria-hidden="true" />
            </span>
            <span className={cn("min-w-0", compact && "hidden sm:block")}>
              <span className="block truncate text-sm font-semibold">{item.label}</span>
              {!compact ? (
                <span className="mt-0.5 block text-[11px] text-slate-500">{item.caption}</span>
              ) : null}
            </span>
            {active && !compact ? (
              <span className="absolute inset-y-2 left-0 w-0.5 rounded-full bg-accent" />
            ) : null}
          </button>
        )
      })}
    </nav>
  )
}

export function AppShell({
  activeView,
  onViewChange,
  apiState,
  apiDocsUrl,
  children,
}: AppShellProps) {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <aside className="fixed inset-y-0 left-0 z-20 hidden w-64 flex-col border-r border-border bg-[#070d1a]/95 px-4 py-5 backdrop-blur lg:flex">
        <div className="flex items-center gap-3 px-2">
          <div className="grid size-10 place-items-center rounded-xl border border-accent/35 bg-accent/8 font-mono text-xs font-semibold text-accent">
            FKL
          </div>
          <div>
            <p className="text-sm font-semibold tracking-tight">Fact Knowledge Layer</p>
            <p className="mt-0.5 font-mono text-[9px] uppercase tracking-[0.14em] text-slate-500">
              Audit console
            </p>
          </div>
        </div>

        <div className="my-5 h-px bg-border" />
        <Navigation activeView={activeView} onViewChange={onViewChange} />

        <div className="mt-auto space-y-3">
          <div className="rounded-xl border border-border bg-background/45 p-3.5">
            <div className="flex items-center gap-2">
              <Layers3 className="size-4 text-accent" aria-hidden="true" />
              <p className="text-xs font-semibold text-foreground">Trust boundary</p>
            </div>
            <p className="mt-2 text-[11px] leading-5 text-muted-foreground">
              The LLM extracts candidates. Source checks and relationship decisions remain
              deterministic.
            </p>
          </div>
          <Button asChild variant="ghost" className="w-full justify-start">
            <a href={apiDocsUrl} target="_blank" rel="noreferrer">
              <Settings2 className="size-4" aria-hidden="true" />
              API documentation
              <ExternalLink className="ml-auto size-3.5" aria-hidden="true" />
            </a>
          </Button>
        </div>
      </aside>

      <div className="lg:pl-64">
        <header className="sticky top-0 z-10 border-b border-border bg-background/82 backdrop-blur-xl">
          <div className="mx-auto flex h-16 max-w-[1500px] items-center justify-between gap-4 px-4 sm:px-6 lg:px-8">
            <div>
              <p className="font-mono text-[10px] uppercase tracking-[0.14em] text-accent">
                Evidence intelligence
              </p>
              <p className="mt-0.5 text-xs text-muted-foreground">
                Trace facts. Audit decisions.
              </p>
            </div>
            <div
              className="flex min-h-9 items-center gap-2 rounded-full border border-border bg-card/65 px-3 font-mono text-[10px] uppercase tracking-[0.08em] text-muted-foreground"
              role="status"
              aria-live="polite"
            >
              <span
                className={cn(
                  "size-1.5 rounded-full",
                  apiState === "ready" && "bg-emerald-400 shadow-[0_0_0_4px_rgba(52,211,153,0.08)]",
                  apiState === "checking" && "animate-pulse bg-amber-300",
                  apiState === "offline" && "bg-rose-400",
                )}
              />
              {apiState === "ready" ? "API ready" : apiState === "checking" ? "Checking API" : "API offline"}
            </div>
          </div>
          <div className="border-t border-border px-3 py-2 lg:hidden">
            <Navigation activeView={activeView} onViewChange={onViewChange} compact />
          </div>
        </header>

        <main className="mx-auto max-w-[1500px] px-4 py-7 sm:px-6 lg:px-8 lg:py-9">
          {children}
        </main>
      </div>
    </div>
  )
}
