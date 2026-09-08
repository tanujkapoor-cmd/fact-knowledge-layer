import { BookOpenText, CircleAlert, MapPin } from "lucide-react"

import { ConfidenceMeter } from "@/components/confidence-meter"
import { StatusBadge } from "@/components/status-badge"
import { Badge } from "@/components/ui/badge"
import type { Fact } from "@/lib/types"

function Field({ label, value }: { label: string; value: string | null }) {
  return (
    <div className="min-w-0 border-r border-border px-3 py-2.5 last:border-r-0">
      <dt className="data-label">{label}</dt>
      <dd className="mt-1 truncate text-xs font-semibold text-foreground" title={value || undefined}>
        {value || "Not specified"}
      </dd>
    </div>
  )
}

export function FactInspector({ fact, label }: { fact: Fact; label?: string }) {
  const evidence = fact.evidence
  const offsets =
    evidence.start_offset === null || evidence.end_offset === null
      ? "Not verified"
      : `${evidence.start_offset}–${evidence.end_offset}`

  return (
    <article className="ledger-panel overflow-hidden" aria-label={label || "Selected fact exhibit"}>
      <header className="flex flex-wrap items-start justify-between gap-3 border-b border-primary bg-primary px-4 py-3 text-primary-foreground">
        <div className="min-w-0">
          <p className="font-mono text-[9px] uppercase tracking-[0.1em] text-blue-100">
            {label || "Selected exhibit"} · {fact.id.slice(0, 8)}
          </p>
          <h2 className="mt-1 truncate text-base font-semibold tracking-[-0.02em]">{fact.subject}</h2>
          <p className="mt-0.5 truncate text-xs text-blue-100">{fact.predicate}</p>
        </div>
        <StatusBadge status={evidence.status} />
      </header>

      <dl className="grid grid-cols-2 border-b border-border bg-surface-low sm:grid-cols-4">
        <Field label="Value" value={fact.value} />
        <Field label="Unit" value={fact.unit} />
        <Field label="Currency" value={fact.currency} />
        <Field label="Temporal scope" value={fact.temporal_scope} />
      </dl>

      <div className="grid border-b border-border sm:grid-cols-2">
        <ConfidenceMeter label="Extraction confidence" score={fact.confidence.extraction} />
        <ConfidenceMeter
          label="Evidence confidence"
          score={fact.confidence.evidence_verification}
          tone={evidence.status === "verified" ? "success" : "warning"}
        />
      </div>

      <section className="p-4" aria-labelledby={`evidence-${fact.id}`}>
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border pb-3">
          <div className="flex items-center gap-2">
            <span className="grid size-7 place-items-center border border-primary bg-primary text-primary-foreground">
              <BookOpenText className="size-3.5" aria-hidden="true" />
            </span>
            <div>
              <h3 id={`evidence-${fact.id}`} className="text-xs font-bold uppercase tracking-[0.04em]">
                Source evidence
              </h3>
              <p className="mt-0.5 font-mono text-[9px] text-muted-foreground">Recovered source substring</p>
            </div>
          </div>
          <Badge variant="neutral">
            <MapPin className="size-3" aria-hidden="true" />
            Physical page {evidence.physical_page_number}
          </Badge>
        </div>

        <div className="grid grid-cols-2 border-x border-b border-border bg-surface-low sm:grid-cols-3">
          <div className="border-r border-border px-3 py-2">
            <span className="data-label">Printed label</span>
            <span className="mt-1 block font-mono text-[11px] tabular">{evidence.printed_page_label || "Not available"}</span>
          </div>
          <div className="border-r border-border px-3 py-2">
            <span className="data-label">Offsets</span>
            <span className="mt-1 block font-mono text-[11px] tabular">{offsets}</span>
          </div>
          <div className="col-span-2 px-3 py-2 sm:col-span-1">
            <span className="data-label">Similarity</span>
            <span className="mt-1 block font-mono text-[11px] tabular">{fact.verification.similarity_score.toFixed(1)}%</span>
          </div>
        </div>

        <blockquote className="relative mt-4 border border-border bg-[#fffef8] px-5 py-5 text-sm leading-7 text-foreground">
          <span className="absolute left-0 top-0 h-full w-px bg-verify" aria-hidden="true" />
          “{evidence.quote}”
        </blockquote>

        {evidence.failure_reason ? (
          <div className="mt-4 flex gap-2 border border-red-700/30 bg-red-50 p-3 text-sm text-red-800" role="alert">
            <CircleAlert className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
            <span>{evidence.failure_reason}</span>
          </div>
        ) : null}
      </section>
    </article>
  )
}
