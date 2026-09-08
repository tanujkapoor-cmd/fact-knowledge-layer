import { useEffect, useMemo, useRef, useState } from "react"
import {
  ArrowLeftRight,
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
  const [loadError, setLoadError] = useState<string | null>(null)
  const [file, setFile] = useState<File | null>(null)
  const [uploading, setUploading] = useState(false)

  const selectedDocument = documents.find((document) => document.id === selectedDocumentId) ?? documents[0]
  const selectedFact = facts.find((fact) => fact.id === selectedFactId) ?? facts[0] ?? null
  const relatedDecisions = useMemo(() => {
    if (!selectedFact) return relationships
    const matches = relationships.filter(
      (relationship) => relationship.fact_a.id === selectedFact.id || relationship.fact_b.id === selectedFact.id,
    )
    return matches.length ? matches : relationships
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
  }, [selectedDocumentId])

  async function uploadDocument() {
    if (!file) return
    setUploading(true)
    setLoadError(null)
    try {
      const document = await api.uploadDocument(file)
      onDocumentUpdate(document)
      onSelectedDocumentChange(document.id)
      setFile(null)
      if (fileInput.current) fileInput.current.value = ""
    } catch (error) {
      setLoadError(error instanceof Error ? error.message : "Document upload failed.")
    } finally {
      setUploading(false)
    }
  }

  function selectDocument(documentId: string) {
    setLoadError(null)
    onSelectedDocumentChange(documentId)
  }

  return (
    <div className="space-y-4">
      <header className="flex items-end justify-between gap-6 border-b border-border pb-4">
        <div>
          <h1 className="page-title">Trace every assertion to source</h1>
          <p className="page-description">
            Documents, extracted claims, exact exhibits, and deterministic decisions remain in one audit surface.
          </p>
        </div>
        <div className="shrink-0 text-right font-mono text-[10px] uppercase tracking-[0.06em] text-muted-foreground">
          {facts.filter((fact) => fact.classification_eligible).length} verified facts · {relationships.length} decisions
        </div>
      </header>

      {loadError ? (
        <div role="alert" className="border border-red-700/30 bg-red-50 px-3 py-2 text-xs text-red-800">
          {loadError}
        </div>
      ) : null}

      <section
        className="grid min-h-[650px] overflow-hidden border border-border bg-card lg:grid-cols-[280px_minmax(320px,0.82fr)_minmax(460px,1.18fr)]"
        aria-label="Continuous evidence desk"
      >
        <aside className="flex min-h-0 flex-col border-r border-border" aria-label="Document register">
          <div className="border-b border-border bg-primary px-4 py-3 text-primary-foreground">
            <p className="font-mono text-[9px] uppercase tracking-[0.08em] text-white/65">Register</p>
            <h2 className="mt-1 text-sm font-semibold">Source documents</h2>
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
                      <span className="font-mono text-[9px] text-muted-foreground">D-{String(index + 1).padStart(2, "0")}</span>
                      <StatusBadge status={document.status} />
                    </div>
                    <p className="mt-2 line-clamp-2 text-xs font-semibold leading-5">{document.file_name}</p>
                    <p className="mt-1 font-mono text-[9px] text-muted-foreground">
                      {document.page_count ?? "—"} pages · {document.sha256.slice(0, 9)}
                    </p>
                  </button>
                )
              })
            ) : (
              <div className="p-5 text-center">
                <FileSearch className="mx-auto size-5 text-muted-foreground" />
                <p className="mt-3 text-xs font-semibold">No source registered</p>
                <p className="mt-1 text-[11px] leading-5 text-muted-foreground">Upload a PDF to begin the evidence chain.</p>
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
            <Button size="sm" className="mt-2 w-full" disabled={!file || uploading} onClick={() => void uploadDocument()}>
              {uploading ? <LoaderCircle className="size-3.5 animate-spin" /> : <UploadCloud className="size-3.5" />}
              {uploading ? "Registering…" : "Register & extract"}
            </Button>
          </div>
        </aside>

        <div className="flex min-h-0 flex-col border-r border-border" aria-label="Fact ledger">
          <div className="flex min-h-[57px] items-center justify-between border-b border-border bg-surface-low px-4 py-3">
            <div>
              <p className="data-label">Fact ledger</p>
              <p className="mt-1 text-xs font-semibold">{selectedDocument?.file_name ?? "Awaiting a source"}</p>
            </div>
            <span className="font-mono text-[10px]">{facts.length} FACTS</span>
          </div>
          <div className="grid grid-cols-[48px_minmax(0,1fr)_80px] border-b border-border px-3 py-2 font-mono text-[9px] uppercase tracking-[0.06em] text-muted-foreground">
            <span>Item</span><span>Subject / predicate</span><span>Evidence</span>
          </div>
          <div className="min-h-0 flex-1 overflow-y-auto">
            {facts.length ? (
              facts.map((fact, index) => {
                const active = fact.id === selectedFact?.id
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
                    <span className="font-mono text-[9px] text-muted-foreground">E-{String(index + 1).padStart(2, "0")}</span>
                    <span className="min-w-0 pr-2">
                      <span className="block truncate text-xs font-semibold">{fact.subject}</span>
                      <span className="mt-0.5 block truncate text-[11px] text-muted-foreground">{fact.predicate} · {fact.value}</span>
                    </span>
                    <StatusBadge status={fact.evidence.status} />
                  </button>
                )
              })
            ) : (
              <div className="grid min-h-64 place-items-center p-5 text-center">
                <div>
                  <Search className="mx-auto size-5 text-muted-foreground" />
                  <p className="mt-3 text-xs font-semibold">No extracted candidates</p>
                  <p className="mt-1 text-[11px] leading-5 text-muted-foreground">Choose a completed document to load its ledger.</p>
                </div>
              </div>
            )}
          </div>
        </div>

        <div className="min-w-0 bg-card" aria-label="Selected source exhibit">
          {selectedFact ? (
            <div className="p-4">
              <FactInspector fact={selectedFact} label={`Exhibit ${String(facts.indexOf(selectedFact) + 1).padStart(2, "0")}`} />
            </div>
          ) : (
            <div className="grid h-full min-h-64 place-items-center p-6 text-center">
              <div>
                <FileSearch className="mx-auto size-6 text-muted-foreground" />
                <p className="mt-3 text-sm font-semibold">Select a verified fact</p>
                <p className="mt-1 max-w-xs text-xs leading-5 text-muted-foreground">Its exact source substring, physical page, printed label, offsets, and confidence will appear here.</p>
              </div>
            </div>
          )}
        </div>
      </section>

      <section className="overflow-hidden border border-border bg-card" aria-label="Ordered relationship reasoning">
        <div className="grid lg:grid-cols-[280px_minmax(0,1fr)]">
          <div className="border-b border-border bg-primary p-4 text-primary-foreground lg:border-b-0 lg:border-r">
            <p className="font-mono text-[9px] uppercase tracking-[0.08em] text-white/65">Decision record</p>
            {selectedRelationship ? (
              <>
                <div className="mt-2 flex items-center gap-2">
                  <h2 className="text-lg font-semibold">{sentenceCase(selectedRelationship.classification)}</h2>
                  <StatusBadge status={selectedRelationship.classification} />
                </div>
                <div className="mt-4">
                  <ConfidenceMeter label="Classification confidence" score={selectedRelationship.classification_confidence} tone={selectedRelationship.classification === "uncertain" ? "warning" : "success"} />
                </div>
                <p className="mt-4 flex items-center gap-2 text-xs text-white/70">
                  <span className="truncate">{selectedRelationship.fact_a.subject}</span>
                  <ArrowLeftRight className="size-3 shrink-0" />
                  <span className="truncate">{selectedRelationship.fact_b.subject}</span>
                </p>
              </>
            ) : (
              <p className="mt-2 text-xs leading-5 text-white/70">No relationship decision is linked to the selected exhibit.</p>
            )}
          </div>
          <div>
            <div className="grid grid-cols-[56px_minmax(140px,0.75fr)_110px_minmax(260px,1.6fr)] border-b border-border bg-surface-low px-4 py-2 font-mono text-[9px] uppercase tracking-[0.06em] text-muted-foreground">
              <span>Order</span><span>Check</span><span>Outcome</span><span>Machine-readable details</span>
            </div>
            {selectedRelationship?.reasoning_trace.length ? (
              selectedRelationship.reasoning_trace.map((step) => (
                <div key={`${step.order}-${step.check}`} className="grid grid-cols-[56px_minmax(140px,0.75fr)_110px_minmax(260px,1.6fr)] items-center border-b border-border px-4 py-3 last:border-b-0">
                  <span className="font-mono text-[10px] text-muted-foreground">{String(step.order).padStart(2, "0")}</span>
                  <span className="text-xs font-semibold">{step.check}</span>
                  <span className={cn("font-mono text-[9px] uppercase", step.outcome === "passed" ? "text-emerald-800" : step.outcome === "failed" ? "text-red-800" : "text-amber-800")}>{sentenceCase(step.outcome)}</span>
                  <span className="text-[11px] leading-5 text-muted-foreground">{traceDetails(step.details)}</span>
                </div>
              ))
            ) : (
              <div className="grid min-h-28 place-items-center px-4 text-xs text-muted-foreground">Deterministic checks will appear here in execution order.</div>
            )}
          </div>
        </div>
      </section>
    </div>
  )
}
