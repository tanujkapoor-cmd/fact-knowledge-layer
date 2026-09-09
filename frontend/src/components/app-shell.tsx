import type { ReactNode } from "react"
import {
  Activity,
  ExternalLink,
  FilePlus2,
  FileStack,
  GitCompareArrows,
  Layers3,
  ListTree,
} from "lucide-react"

import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"

export type ViewId = "documents" | "facts" | "relationships"

const NAVIGATION = [
  { id: "documents", label: "Documents", icon: FileStack },
  { id: "facts", label: "Fact ledger", icon: ListTree },
  { id: "relationships", label: "Audit log", icon: GitCompareArrows },
] satisfies Array<{ id: ViewId; label: string; icon: typeof FileStack }>

interface AppShellProps {
  activeView: ViewId
  onViewChange: (view: ViewId) => void
  apiState: "checking" | "ready" | "offline"
  apiDocsUrl: string
  children: ReactNode
}

function Navigation({ activeView, onViewChange }: { activeView: ViewId; onViewChange: (view: ViewId) => void }) {
  return (
    <nav aria-label="Primary navigation" className="flex min-w-0 items-stretch">
      {NAVIGATION.map((item) => {
        const active = activeView === item.id
        return (
          <button
            key={item.id}
            type="button"
            className={cn(
              "relative flex min-h-11 min-w-0 flex-1 cursor-pointer items-center justify-center gap-1.5 border-x border-transparent px-2 text-[11px] font-semibold text-muted-foreground outline-none transition-colors hover:bg-surface-low hover:text-foreground focus-visible:z-10 focus-visible:ring-2 focus-visible:ring-ring sm:min-h-14 sm:flex-none sm:justify-start sm:gap-2 sm:px-4 sm:text-xs",
              active && "border-border bg-card text-foreground",
            )}
            aria-current={active ? "page" : undefined}
            onClick={() => onViewChange(item.id)}
          >
            <item.icon className="size-3.5" aria-hidden="true" />
            {item.label}
            {active ? <span className="absolute inset-x-0 bottom-0 h-0.5 bg-primary" /> : null}
          </button>
        )
      })}
    </nav>
  )
}

export function AppShell({ activeView, onViewChange, apiState, apiDocsUrl, children }: AppShellProps) {
  function openUploadPicker() {
    onViewChange("documents")
    window.setTimeout(() => {
      const inputId = window.matchMedia("(min-width: 1024px)").matches
        ? "desktop-pdf-upload"
        : "pdf-upload"
      document.getElementById(inputId)?.click()
    }, 0)
  }

  return (
    <div className="min-h-screen bg-background text-foreground">
      <header className="sticky top-0 z-20 border-b border-border bg-card">
        <div className="grid grid-cols-[minmax(0,1fr)_auto] lg:flex lg:min-h-14 lg:items-stretch">
          <button
            type="button"
            className="flex min-w-0 items-center gap-2.5 border-r border-border px-3 text-left outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring sm:min-w-64 sm:shrink-0 sm:px-5"
            onClick={() => onViewChange("documents")}
          >
            <span className="grid size-7 place-items-center border border-primary bg-primary text-primary-foreground">
              <Layers3 className="size-4" strokeWidth={1.8} aria-hidden="true" />
            </span>
            <span className="min-w-0">
              <span className="block truncate text-sm font-semibold tracking-[-0.02em]">Fact Knowledge Layer</span>
              <span className="hidden font-mono text-[9px] uppercase tracking-[0.08em] text-muted-foreground sm:block">Traceability verifier</span>
            </span>
          </button>

          <div className="order-3 col-span-2 min-w-0 border-t border-border lg:hidden">
            <Navigation activeView={activeView} onViewChange={onViewChange} />
          </div>

          <div className="hidden flex-1 items-center border-r border-border px-5 font-mono text-[10px] uppercase tracking-[0.06em] text-muted-foreground lg:flex">
            Continuous evidence workspace
          </div>

          <div className="ml-auto flex shrink-0 items-center gap-1 border-l border-border px-2 sm:gap-2 sm:px-4">
            <div className="flex items-center gap-2 font-mono text-[10px] uppercase tracking-[0.04em] text-muted-foreground" role="status" aria-live="polite" title={apiState === "ready" ? "API healthy" : apiState === "checking" ? "Checking API" : "API offline"}>
              <span
                className={cn(
                  "size-2 border",
                  apiState === "ready" && "border-verify bg-verify",
                  apiState === "checking" && "animate-pulse border-warning bg-warning",
                  apiState === "offline" && "border-destructive bg-destructive",
                )}
              />
              <Activity className="hidden size-3.5 sm:block" aria-hidden="true" />
              <span className="hidden md:inline">{apiState === "ready" ? "API healthy" : apiState === "checking" ? "Checking API" : "API offline"}</span>
              <span className="sr-only md:hidden">{apiState === "ready" ? "API healthy" : apiState === "checking" ? "Checking API" : "API offline"}</span>
            </div>
            <Button asChild variant="ghost" size="icon" aria-label="Open API documentation">
              <a href={apiDocsUrl} target="_blank" rel="noreferrer" title="API documentation">
                <ExternalLink className="size-4" aria-hidden="true" />
              </a>
            </Button>
            <Button size="sm" onClick={openUploadPicker}>
              <FilePlus2 className="size-3.5" aria-hidden="true" />
              <span className="hidden sm:inline">Upload PDF</span>
            </Button>
          </div>
        </div>
      </header>

      <main className="mx-auto w-full max-w-[1800px] px-3 py-4 sm:px-5 sm:py-5 lg:px-6">{children}</main>

      <footer className="border-t border-border bg-card px-5 py-2 font-mono text-[9px] uppercase tracking-[0.06em] text-muted-foreground">
        <div className="mx-auto flex max-w-[1800px] flex-wrap items-center justify-between gap-2">
          <span>Fact Knowledge Layer · Evidence before assertion</span>
          <span>Evidence workspace · Deterministic reasoning</span>
        </div>
      </footer>
    </div>
  )
}
