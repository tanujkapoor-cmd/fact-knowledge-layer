import { useEffect, useMemo, useRef, useState } from "react"
import {
  ArrowLeftRight,
  ChevronLeft,
  ChevronRight,
  FilePlus2,
  FileSearch,
  LoaderCircle,
  Search,
  UploadCloud,
} from "lucide-react"

import { ConfidenceMeter } from "@/components/confidence-meter"
import { FactInspector } from "@/components/fact-inspector"
import { StatusBadge } from "@/components/status-badge"
import { Button } from "@/components/ui/button"
import { api } from "@/lib/api"
import type { Fact, Relationship, TrackedDocument } from "@/lib/types"
import { cn, sentenceCase } from "@/lib/utils"

const ACTIVE_STATUSES = new Set(["queued", "ingesting", "extracting", "verifying", "normalizing", "classifying"])

interface EvidenceWorkspaceProps {
  documents: TrackedDocument[]
  selectedDocumentId: string
  onSelectedDocumentChange: (documentId: string) => void
  onDocumentUpdate: (document: TrackedDocument) => void
}

function traceDetails(details: Relationship["reasoning_trace"][number]["details"]) {
  const entries = Object.entries(details)
  return entries.length
    ? entries.map(([key, value]) => `${sentenceCase(key)}: ${String(value)}`).join(" · ")
    : "No additional values"
}

export function EvidenceWorkspace({
  documents,
  selectedDocumentId,
  onSelectedDocumentChange,
  onDocumentUpdate,
}: EvidenceWorkspaceProps) {
  const fileInput = useRef<HTMLInputElement>(null)
  const [facts, setFacts] = useState<Fact[]>([])
  const [relationships, setRelationships] = useState<Relationship[]>([])
  const [selectedFactId, setSelectedFactId] = useState<string | null>(null)
  const [selectedRelationshipId, setSelectedRelationshipId] = useState<string | null>(null)
  const [factQuery, setFactQuery] = useState("")
  const [loadError, setLoadError] = useState<string | null>(null)
  const [file, setFile] = useState<File | null>(null)
  const [uploading, setUploading] = useState(false)

  const selectedDocument = documents.find((document) => document.id === selectedDocumentId) ?? documents[0]
  const visibleFacts = useMemo(() => {
    const query = factQuery.trim().toLowerCase()
    if (!query) return facts
    return facts.filter((fact) =>
      [fact.subject, fact.predicate, fact.value, fact.id].some((value) => value.toLowerCase().includes(query)),
    )
  }, [factQuery, facts])
  const selectedFact = visibleFacts.find((fact) => fact.id === selectedFactId) ?? visibleFacts[0] ?? null
  const relatedDecisions = useMemo(() => {
    if (!selectedFact) return []
    return relationships.filter(
      (relationship) => relationship.fact_a.id === selectedFact.id || relationship.fact_b.id === selectedFact.id,
    )
  }, [relationships, selectedFact])
  const selectedRelationship =
    relatedDecisions.find((relationship) => relationship.id === selectedRelationshipId) ??
    relatedDecisions[0] ??
    null

  useEffect(() => {
    if (!selectedDocumentId) return

    let cancelled = false
    void Promise.allSettled([
      api.facts(selectedDocumentId),
      api.relationships({ documentId: selectedDocumentId }),
    ]).then(([factsResult, relationshipsResult]) => {
      if (cancelled) return
      if (factsResult.status === "fulfilled") {
        setFacts(factsResult.value)
        setSelectedFactId(factsResult.value[0]?.id ?? null)
        setLoadError(null)
      } else {
        setFacts([])
        setLoadError(factsResult.reason instanceof Error ? factsResult.reason.message : "Facts could not be loaded.")
      }
      if (relationshipsResult.status === "fulfilled") {
        setRelationships(relationshipsResult.value)
        setSelectedRelationshipId(relationshipsResult.value[0]?.id ?? null)
      } else {
        setRelationships([])
      }
    })

    return () => {
      cancelled = true
    }
  }, [selectedDocumentId, selectedDocument?.status])

  useEffect(() => {
    const active = documents.filter((document) => ACTIVE_STATUSES.has(document.status))
    if (!active.length) return
    const interval = window.setInterval(() => {
      active.forEach((document) => {
        void api.documentStatus(document.id).then((status) => {
          onDocumentUpdate({ ...document, ...status })
        }).catch(() => {
          // The selected document panel retains the last durable checkpoint.
        })
      })
    }, 2500)
    return () => window.clearInterval(interval)
  }, [documents, onDocumentUpdate])

  async function uploadDocument(retryFailed = false) {
    if (!file) return
    setUploading(true)
    setLoadError(null)
    try {
      const document = await api.uploadDocument(file, retryFailed)
      onDocumentUpdate(document)
      onSelectedDocumentChange(document.id)
      if (document.duplicate_reused && document.status === "failed" && !document.retry_started) {
        setLoadError("This exact PDF has a failed analysis. The reason is shown in the register; retry it to start from a clean checkpoint.")
      } else {
        setFile(null)
        if (fileInput.current) fileInput.current.value = ""
      }
    } catch (error) {
      setLoadError(error instanceof Error ? error.message : "Document upload failed.")
    } finally {
      setUploading(false)
    }
  }

  function selectDocument(documentId: string) {
    setLoadError(null)
    setFactQuery("")
    onSelectedDocumentChange(documentId)
  }

  function moveDecision(direction: -1 | 1) {
    if (!selectedRelationship || relatedDecisions.length < 2) return
    const currentIndex = relatedDecisions.findIndex((relationship) => relationship.id === selectedRelationship.id)
    const nextIndex = (currentIndex + direction + relatedDecisions.length) % relatedDecisions.length
    setSelectedRelationshipId(relatedDecisions[nextIndex].id)
  }

  return (
    <div className="space-y-3">
      <header className="grid items-center gap-3 border-b border-border pb-3 lg:grid-cols-[minmax(220px,0.8fr)_minmax(390px,1.4fr)_auto]">
        <div className="min-w-0">
          <h1 className="text-base font-semibold tracking-[-0.02em]">Active evidence review</h1>
          <p className="mt-1 truncate text-xs text-muted-foreground">{selectedDocument?.file_name || "No source registered"}</p>
        </div>
        <ol className="grid grid-cols-3 border border-border bg-card text-[10px]" aria-label="Evidence review sequence">
          {["Select source", "Inspect claim", "Verify exhibit"].map((step, index) => (
            <li key={step} className="flex items-center gap-2 border-r border-border px-2.5 py-2 last:border-r-0">
              <span className="font-mono text-[8px] text-muted-foreground">{String(index + 1).padStart(2, "0")}</span>
              <span className={index === 2 && selectedFact ? "font-semibold text-verify" : "font-medium"}>{step}</span>
            </li>
          ))}
        </ol>
        <dl className="flex shrink-0 items-center divide-x divide-border border border-border bg-card">
          <div className="px-3 py-1.5 text-right"><dt className="data-label">Verified</dt><dd className="mt-0.5 font-mono text-xs font-semibold tabular">{facts.filter((fact) => fact.classification_eligible).length}</dd></div>
          <div className="px-3 py-1.5 text-right"><dt className="data-label">Decisions</dt><dd className="mt-0.5 font-mono text-xs font-semibold tabular">{relationships.length}</dd></div>
        </dl>
      </header>

      {loadError ? (
        <div role="alert" className="border border-red-700/30 bg-red-50 px-3 py-2 text-xs text-red-800">
          {loadError}
        </div>
      ) : null}

      <section
        className="grid min-h-[calc(100vh-155px)] max-h-[calc(100vh-155px)] overflow-hidden border border-border bg-card lg:grid-cols-[240px_minmax(280px,0.82fr)_minmax(360px,1.18fr)] xl:grid-cols-[270px_minmax(340px,0.82fr)_minmax(480px,1.18fr)]"
        aria-label="Continuous evidence desk"
      >
        <aside className="flex min-h-0 flex-col border-r border-border" aria-label="Document register">
          <div className="border-b border-border bg-primary px-4 py-3 text-primary-foreground">
            <div className="flex items-end justify-between gap-3">
              <div><p className="font-mono text-[9px] uppercase tracking-[0.08em] text-white/65">Source register</p><h2 className="mt-1 text-sm font-semibold">Document docket</h2></div>
              <span className="font-mono text-[9px] text-white/65">{documents.length} DOC</span>
            </div>
          </div>
          <div className="min-h-0 flex-1 overflow-y-auto">
            {documents.length ? (
              documents.map((document, index) => {
                const active = document.id === selectedDocument?.id
                return (
                  <button
                    key={document.id}
                    type="button"
                    className={cn(
                      "relative w-full border-b border-border px-4 py-3 text-left outline-none transition-colors hover:bg-surface-low focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring",
                      active && "bg-[#e7f3ef]",
                    )}
                    onClick={() => selectDocument(document.id)}
                    aria-pressed={active}
                  >
                    {active ? <span className="absolute inset-y-0 left-0 w-px bg-verify" /> : null}
                    <div className="flex items-start justify-between gap-2">
                      <span className="font-mono text-[9px] font-semibold text-muted-foreground">SRC-{String(index + 1).padStart(2, "0")}</span>
                      <StatusBadge status={document.status} register={ACTIVE_STATUSES.has(document.status) ? "RUN" : "DOC"} />
                    </div>
                    <p className="mt-2 line-clamp-2 text-xs font-semibold leading-5">{document.file_name}</p>
                    <dl className="mt-2 grid grid-cols-2 gap-2 border-t border-border/70 pt-2 font-mono text-[8px] text-muted-foreground">
                      <div><dt className="uppercase tracking-[0.05em]">Pages</dt><dd className="mt-0.5 text-[9px] text-foreground">{document.page_count ?? "—"}</dd></div>
                      <div><dt className="uppercase tracking-[0.05em]">Source hash</dt><dd className="mt-0.5 text-[9px] text-foreground">{document.sha256.slice(0, 9)}</dd></div>
                    </dl>
                    {active ? <p className="mt-2 font-mono text-[8px] font-semibold uppercase tracking-[0.06em] text-verify">Active source</p> : null}
                    {ACTIVE_STATUSES.has(document.status) ? (
                      <p className="mt-1 font-mono text-[9px] text-muted-foreground">
                        {document.processed_page_count ?? 0}/{document.page_count ?? "?"} pages · {document.provider_attempt_count ?? 0} attempts
                      </p>
                    ) : null}
                    {document.status === "failed" ? (
                      <p className="mt-2 line-clamp-3 text-[10px] leading-4 text-red-800" role="alert">
                        {document.failure_reason || "Processing failed without a stored reason."}
                      </p>
                    ) : null}
                  </button>
                )
              })
            ) : (
              <div className="m-3 border-y border-border py-5">
                <div className="flex items-start gap-3"><FileSearch className="mt-0.5 size-4 shrink-0 text-muted-foreground" /><div><p className="data-label">Register empty</p><p className="mt-1.5 text-xs font-semibold">No source registered</p><p className="mt-1 text-[10px] leading-4 text-muted-foreground">Upload a PDF to create the first source record.</p></div></div>
              </div>
            )}
          </div>
          <div className="border-t border-border bg-surface-low p-3">
            <input
              ref={fileInput}
              id="desktop-pdf-upload"
              type="file"
              accept="application/pdf,.pdf"
              className="hidden"
              onChange={(event) => setFile(event.target.files?.item(0) ?? null)}
            />
            <Button variant="outline" size="sm" className="w-full justify-start" onClick={() => fileInput.current?.click()}>
              <FilePlus2 className="size-3.5" /> {file ? file.name : "Choose source PDF"}
            </Button>
            <Button size="sm" className="mt-2 w-full" disabled={!file || uploading} onClick={() => void uploadDocument(selectedDocument?.status === "failed")}>
              {uploading ? <LoaderCircle className="size-3.5 animate-spin" /> : <UploadCloud className="size-3.5" />}
              {uploading ? "Registering…" : selectedDocument?.status === "failed" ? "Retry failed analysis" : "Register & extract"}
            </Button>
            {selectedDocument?.status === "failed" ? (
              <p className="mt-2 text-[10px] leading-4 text-red-800">
                Choose the same PDF. Retry clears only its failed derived rows and preserves its document ID.
              </p>
            ) : null}
          </div>
        </aside>

        <div className="flex min-h-0 flex-col border-r border-border" aria-label="Fact ledger">
          <div className="flex min-h-[57px] items-center justify-between border-b border-border bg-surface-low px-3 py-2.5">
            <div>
              <p className="data-label">Fact ledger</p>
              <p className="mt-1 text-xs font-semibold">{selectedDocument?.file_name ?? "Awaiting a source"}</p>
            </div>
            <span className="font-mono text-[10px]">{facts.length} FACTS</span>
          </div>
          <label className="relative border-b border-border bg-card p-2">
            <Search className="pointer-events-none absolute left-4 top-1/2 size-3.5 -translate-y-1/2 text-muted-foreground" aria-hidden="true" />
            <input value={factQuery} onChange={(event) => setFactQuery(event.target.value)} className="h-8 w-full border border-border bg-surface-low pl-8 pr-3 text-[11px] outline-none placeholder:text-muted-foreground focus:border-primary focus:ring-1 focus:ring-ring" placeholder="Filter subject, predicate, value, or claim ID" aria-label="Filter fact ledger" />
          </label>
          <div className="grid grid-cols-[48px_minmax(0,1fr)_80px] border-b border-border px-3 py-2 font-mono text-[9px] uppercase tracking-[0.06em] text-muted-foreground">
            <span>Item</span><span>Subject / predicate</span><span>Evidence</span>
          </div>
          <div className="min-h-0 flex-1 overflow-y-auto">
            {visibleFacts.length ? (
              visibleFacts.map((fact) => {
                const active = fact.id === selectedFact?.id
                const index = facts.indexOf(fact)
                return (
                  <button
                    key={fact.id}
                    type="button"
                    className={cn(
                      "relative grid w-full grid-cols-[48px_minmax(0,1fr)_80px] items-center border-b border-border px-3 py-3 text-left outline-none transition-colors hover:bg-surface-low focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring",
                      active && "bg-[#e7f3ef]",
                    )}
                    onClick={() => setSelectedFactId(fact.id)}
                    aria-pressed={active}
                  >
                    {active ? <span className="absolute inset-y-0 left-0 w-px bg-verify" /> : null}
                    <span className="font-mono text-[8px] font-semibold text-muted-foreground">CLM-{String(index + 1).padStart(3, "0")}</span>
                    <span className="min-w-0 pr-2">
                      <span className="block truncate text-xs font-semibold">{fact.subject}</span>
                      <span className="mt-0.5 block truncate text-[11px] text-muted-foreground">{fact.predicate} · {fact.value}</span>
                    </span>
                    <StatusBadge status={fact.evidence.status} />
                  </button>
                )
              })
            ) : (
              <div className="m-4 border-y border-border py-6">
                <div className="flex items-start gap-3"><Search className="mt-0.5 size-4 shrink-0 text-muted-foreground" /><div><p className="data-label">Ledger empty</p><p className="mt-1.5 text-xs font-semibold">{facts.length ? "No claims match this filter" : "No extracted candidates"}</p><p className="mt-1 text-[10px] leading-4 text-muted-foreground">{facts.length ? "Clear or revise the filter to restore ledger rows." : "Choose a completed source to load its claim records."}</p></div></div>
              </div>
            )}
          </div>
        </div>

        <div className="min-w-0 overflow-y-auto bg-card" aria-label="Selected source exhibit">
          {selectedFact ? (
            <div className="space-y-3 p-3">
              <FactInspector fact={selectedFact} source={selectedDocument} label={`Exhibit ${String(facts.indexOf(selectedFact) + 1).padStart(3, "0")}`} />
              {selectedRelationship ? (
                <section className="overflow-hidden border border-border" aria-label="Decision record linked to selected fact">
                  <header className="flex items-start justify-between gap-3 border-b border-primary bg-primary p-3 text-primary-foreground">
                    <div className="min-w-0">
                      <p className="font-mono text-[8px] uppercase tracking-[0.08em] text-white/65">Linked decision · REL-{selectedRelationship.id.slice(0, 8)}</p>
                      <div className="mt-1.5 flex flex-wrap items-center gap-2"><h2 className="text-sm font-semibold">{sentenceCase(selectedRelationship.classification)}</h2><StatusBadge status={selectedRelationship.classification} /></div>
                      <p className="mt-1 flex items-center gap-1.5 text-[10px] text-white/70"><span className="truncate">{selectedRelationship.fact_a.subject}</span><ArrowLeftRight className="size-3 shrink-0" /><span className="truncate">{selectedRelationship.fact_b.subject}</span></p>
                    </div>
                    {relatedDecisions.length > 1 ? (
                      <div className="flex shrink-0 items-center gap-1 font-mono text-[8px] text-white/70"><button type="button" className="grid size-7 place-items-center border border-white/30 hover:bg-white/10 focus-visible:ring-2 focus-visible:ring-white" onClick={() => moveDecision(-1)} aria-label="Previous linked decision"><ChevronLeft className="size-3.5" /></button><span className="px-1 tabular">{relatedDecisions.indexOf(selectedRelationship) + 1}/{relatedDecisions.length}</span><button type="button" className="grid size-7 place-items-center border border-white/30 hover:bg-white/10 focus-visible:ring-2 focus-visible:ring-white" onClick={() => moveDecision(1)} aria-label="Next linked decision"><ChevronRight className="size-3.5" /></button></div>
                    ) : null}
                  </header>
                  <ConfidenceMeter label="Classification confidence" score={selectedRelationship.classification_confidence} tone={selectedRelationship.classification === "uncertain" ? "warning" : "success"} />
                  <div className="border-t border-border bg-surface-low px-3 py-2"><p className="data-label">Deterministic reasoning trace</p></div>
                  {selectedRelationship.reasoning_trace.map((step) => (
                    <div key={`${step.order}-${step.check}`} className="grid grid-cols-[32px_minmax(92px,0.55fr)_78px_minmax(0,1fr)] items-start gap-x-2 border-t border-border px-3 py-2 first:border-t-0">
                      <span className="font-mono text-[9px] text-muted-foreground">{String(step.order).padStart(2, "0")}</span>
                      <span className="text-[10px] font-semibold leading-4">{step.check}</span>
                      <span className={cn("font-mono text-[8px] uppercase leading-4", step.outcome === "passed" ? "text-emerald-800" : step.outcome === "failed" ? "text-red-800" : "text-amber-800")}>{sentenceCase(step.outcome)}</span>
                      <span className="text-[9px] leading-4 text-muted-foreground">{traceDetails(step.details)}</span>
                    </div>
                  ))}
                </section>
              ) : null}
            </div>
          ) : (
            <div className="grid h-full min-h-64 place-items-center p-6">
              <div className="w-full max-w-sm border-y border-border py-6"><div className="flex items-start gap-3"><FileSearch className="mt-0.5 size-5 shrink-0 text-muted-foreground" /><div><p className="data-label">Exhibit not selected</p><p className="mt-1.5 text-sm font-semibold">Choose a claim record</p><p className="mt-1 text-xs leading-5 text-muted-foreground">The exact passage, page references, offsets, provenance, confidence, and linked decision record will resolve here.</p></div></div></div>
            </div>
          )}
        </div>
      </section>
    </div>
  )
}
