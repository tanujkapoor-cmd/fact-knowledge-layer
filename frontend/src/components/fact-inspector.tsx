import { BookOpenText, CircleAlert, MapPin } from "lucide-react"

import { ConfidenceMeter } from "@/components/confidence-meter"
import { StatusBadge } from "@/components/status-badge"
import { Badge } from "@/components/ui/badge"
import type { Fact } from "@/lib/types"

function Field({ label, value }: { label: string; value: string | null }) {
  return (
    <div>
      <dt className="font-mono text-[10px] uppercase tracking-[0.12em] text-slate-500">{label}</dt>
      <dd className="mt-1 text-sm font-medium text-foreground">{value || "Not specified"}</dd>
    </div>
  )
}

export function FactInspector({ fact, label }: { fact: Fact; label?: string }) {
  const evidence = fact.evidence
  const offsets =
    evidence.start_offset === null || evidence.end_offset === null
      ? "Not verified"
      : `${evidence.start_offset}:${evidence.end_offset}`

  return (
    <article className="rounded-xl border border-border bg-card/90 p-5 shadow-[0_18px_45px_rgba(0,0,0,0.14)]">
      <div className="flex flex-wrap items-start justify-between gap-3 border-b border-border pb-4">
        <div>
          {label ? (
            <p className="mb-1 font-mono text-[10px] uppercase tracking-[0.14em] text-accent">
              {label}
            </p>
          ) : null}
          <h3 className="text-lg font-semibold tracking-tight text-foreground">{fact.subject}</h3>
          <p className="mt-1 text-sm text-muted-foreground">{fact.predicate}</p>
        </div>
        <StatusBadge status={evidence.status} />
      </div>

      <dl className="grid gap-4 border-b border-border py-4 sm:grid-cols-2 lg:grid-cols-4">
        <Field label="Value" value={fact.value} />
        <Field label="Unit" value={fact.unit} />
        <Field label="Currency" value={fact.currency} />
        <Field label="Temporal scope" value={fact.temporal_scope} />
      </dl>

      <div className="grid gap-3 py-4 sm:grid-cols-2">
        <ConfidenceMeter label="Extraction confidence" score={fact.confidence.extraction} />
        <ConfidenceMeter
          label="Evidence confidence"
          score={fact.confidence.evidence_verification}
          tone={evidence.status === "verified" ? "success" : "warning"}
        />
      </div>

      <section className="rounded-lg border border-border bg-background/45 p-4" aria-labelledby={`evidence-${fact.id}`}>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <BookOpenText className="size-4 text-accent" aria-hidden="true" />
            <h4 id={`evidence-${fact.id}`} className="text-sm font-semibold">
              Source evidence
            </h4>
          </div>
          <Badge variant="neutral">
            <MapPin className="size-3" aria-hidden="true" />
            PDF page {evidence.physical_page_number}
          </Badge>
        </div>
        <p className="mt-2 font-mono text-[10px] uppercase tracking-[0.1em] text-slate-500">
          Printed label {evidence.printed_page_label || "not available"} · offsets {offsets}
        </p>
        <blockquote className="mt-4 border-l-2 border-accent/55 pl-4 text-sm leading-7 text-slate-200">
          “{evidence.quote}”
        </blockquote>
        {evidence.failure_reason ? (
          <div className="mt-4 flex gap-2 rounded-lg border border-rose-400/25 bg-rose-400/7 p-3 text-sm text-rose-200">
            <CircleAlert className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
            <span>{evidence.failure_reason}</span>
          </div>
        ) : null}
      </section>
    </article>
  )
}
