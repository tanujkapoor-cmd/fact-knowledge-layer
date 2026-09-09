import { useMemo, useState } from "react"
import { motion } from "motion/react"
import { AlertTriangle, CheckCircle2, Download, FileSearch, LoaderCircle, Search } from "lucide-react"

import { EmptyState } from "@/components/empty-state"
import { FactInspector } from "@/components/fact-inspector"
import { StatusBadge } from "@/components/status-badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { api } from "@/lib/api"
import type { Fact, TrackedDocument } from "@/lib/types"
import { cn, downloadJson } from "@/lib/utils"

interface FactsViewProps {
  documents: TrackedDocument[]
  selectedDocumentId: string
  onSelectedDocumentChange: (documentId: string) => void
}

export function FactsView({ documents, selectedDocumentId, onSelectedDocumentChange }: FactsViewProps) {
  const [result, setResult] = useState<{ documentId: string; facts: Fact[] } | null>(null)
  const [selectedFactId, setSelectedFactId] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const facts = useMemo(
    () => (result?.documentId === selectedDocumentId.trim() ? result.facts : []),
    [result, selectedDocumentId],
  )
  const selectedFact = useMemo(
    () => facts.find((fact) => fact.id === selectedFactId) || facts[0] || null,
    [facts, selectedFactId],
  )
  const verifiedCount = facts.filter((fact) => fact.classification_eligible).length
  const selectedDocument = documents.find((document) => document.id === selectedDocumentId)

  async function loadFacts() {
    const documentId = selectedDocumentId.trim()
    if (!documentId) return
    setIsLoading(true)
    setError(null)
    try {
      const items = await api.facts(documentId)
      setResult({ documentId, facts: items })
      setSelectedFactId(items[0]?.id || null)
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Could not load the fact ledger.")
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="space-y-4">
      <header className="flex flex-col gap-3 border-b border-border pb-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <h1 className="page-title">Fact ledger and source exhibit</h1>
          <p className="page-description">Select a candidate to inspect its exact recovered quote, physical page, offsets, and independent confidence scores.</p>
        </div>
        <div className="font-mono text-[10px] uppercase tracking-[0.06em] text-muted-foreground">
          Verified facts only enter relationship classification
        </div>
      </header>

      <section className="ledger-panel grid min-w-0 grid-cols-[minmax(0,1fr)] gap-3 p-3 lg:grid-cols-[minmax(220px,0.9fr)_minmax(280px,1.25fr)_auto] lg:items-end" aria-label="Fact source controls">
        <label className="min-w-0 space-y-1.5">
          <span className="field-label">Tracked document</span>
          <Select
            value={documents.some((document) => document.id === selectedDocumentId) ? selectedDocumentId : undefined}
            onValueChange={onSelectedDocumentChange}
            disabled={!documents.length}
          >
            <SelectTrigger aria-label="Tracked document">
              <SelectValue placeholder={documents.length ? "Choose a document" : "No tracked documents"} />
            </SelectTrigger>
            <SelectContent>
              {documents.map((document) => (
                <SelectItem key={document.id} value={document.id}>{document.file_name}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </label>
        <label className="min-w-0 space-y-1.5">
          <span className="field-label">Document identifier</span>
          <Input
            value={selectedDocumentId}
            onChange={(event) => onSelectedDocumentChange(event.target.value)}
            placeholder="Paste a document UUID"
            spellCheck={false}
            className="font-mono text-xs"
          />
        </label>
        <Button onClick={() => void loadFacts()} disabled={!selectedDocumentId.trim() || isLoading}>
          {isLoading ? <LoaderCircle className="size-4 animate-spin" aria-hidden="true" /> : <Search className="size-4" aria-hidden="true" />}
          {isLoading ? "Loading…" : "Load ledger"}
        </Button>
      </section>

      {error ? <div role="alert" className="border border-red-700/30 bg-red-50 p-3 text-sm text-red-800">{error}</div> : null}

      {!result || result.documentId !== selectedDocumentId.trim() ? (
        <EmptyState icon={FileSearch} title="Choose a fact source" description="Select an uploaded document or paste its identifier, then load the fact ledger." detail="Evidence and confidence remain attached to every candidate" />
      ) : facts.length === 0 ? (
        <EmptyState icon={FileSearch} title="No facts are available" description="The document may still be processing, or extraction produced no candidate facts." detail="Check document status before retrying" />
      ) : (
        <section className="ledger-panel overflow-hidden" aria-label="Fact evidence workspace">
          <div className="grid border-b border-border bg-surface-low sm:grid-cols-[1fr_auto] sm:items-center">
            <div className="grid grid-cols-3 divide-x divide-border">
              <div className="px-3 py-2.5">
                <span className="data-label">Extracted</span>
                <span className="mt-1 block font-mono text-sm font-semibold tabular">{facts.length}</span>
              </div>
              <div className="px-3 py-2.5">
                <span className="data-label">Evidence verified</span>
                <span className="mt-1 flex items-center gap-1.5 font-mono text-sm font-semibold text-emerald-800 tabular"><CheckCircle2 className="size-3.5" />{verifiedCount}</span>
              </div>
              <div className="px-3 py-2.5">
                <span className="data-label">Rejected</span>
                <span className="mt-1 flex items-center gap-1.5 font-mono text-sm font-semibold text-amber-800 tabular"><AlertTriangle className="size-3.5" />{facts.length - verifiedCount}</span>
              </div>
            </div>
            <Button variant="ghost" size="sm" className="m-2 justify-self-start sm:justify-self-end" onClick={() => downloadJson(`facts-${selectedDocumentId.slice(0, 8)}.json`, facts)}>
              <Download className="size-3.5" aria-hidden="true" /> Export JSON
            </Button>
          </div>

          <div className="grid min-h-[610px] xl:grid-cols-[minmax(330px,0.85fr)_minmax(520px,1.35fr)]">
            <div className="border-b border-border xl:border-b-0 xl:border-r">
              <div className="grid grid-cols-[48px_minmax(0,1.3fr)_minmax(0,1fr)_auto] border-b border-border bg-surface-low px-2 py-2 font-mono text-[9px] font-semibold uppercase tracking-[0.06em] text-muted-foreground">
                <span>Exhibit</span><span>Subject / predicate</span><span>Value</span><span>Status</span>
              </div>
              <div className="max-h-[610px] overflow-y-auto">
                {facts.map((fact, index) => {
                  const active = selectedFact?.id === fact.id
                  return (
                    <button
                      key={fact.id}
                      type="button"
                      className={cn(
                        "relative grid w-full cursor-pointer grid-cols-[48px_minmax(0,1.3fr)_minmax(0,1fr)_auto] items-center border-b border-border px-2 py-3 text-left outline-none transition-colors hover:bg-surface-low focus-visible:z-10 focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring",
                        active && "bg-[#e7f3ef]",
                      )}
                      aria-pressed={active}
                      onClick={() => setSelectedFactId(fact.id)}
                    >
                      {active ? <motion.span layoutId="selected-fact-rule" className="absolute inset-y-0 left-0 w-px bg-verify" /> : null}
                      <span className="font-mono text-[10px] font-semibold text-muted-foreground">E-{String(index + 1).padStart(2, "0")}</span>
                      <span className="min-w-0 pr-3">
                        <span className="block truncate text-xs font-semibold">{fact.subject}</span>
                        <span className="mt-0.5 block truncate text-[11px] text-muted-foreground">{fact.predicate}</span>
                      </span>
                      <span className="truncate pr-3 font-mono text-[11px] tabular">{fact.value}</span>
                      <StatusBadge status={fact.evidence.status} />
                    </button>
                  )
                })}
              </div>
            </div>

            <div className="bg-card p-3 sm:p-4">
              {selectedFact ? <FactInspector fact={selectedFact} source={selectedDocument} label={`Exhibit ${String(facts.indexOf(selectedFact) + 1).padStart(3, "0")}`} /> : null}
            </div>
          </div>
        </section>
      )}
    </div>
  )
}
