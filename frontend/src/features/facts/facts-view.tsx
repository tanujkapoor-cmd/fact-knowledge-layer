import { useMemo, useState } from "react"
import {
  AlertTriangle,
  Braces,
  CheckCircle2,
  Download,
  FileSearch,
  LoaderCircle,
  Search,
} from "lucide-react"

import { EmptyState } from "@/components/empty-state"
import { FactInspector } from "@/components/fact-inspector"
import { StatusBadge } from "@/components/status-badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { api } from "@/lib/api"
import type { Fact, TrackedDocument } from "@/lib/types"
import { cn, downloadJson } from "@/lib/utils"

interface FactsViewProps {
  documents: TrackedDocument[]
  selectedDocumentId: string
  onSelectedDocumentChange: (documentId: string) => void
}

export function FactsView({
  documents,
  selectedDocumentId,
  onSelectedDocumentChange,
}: FactsViewProps) {
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
    <div className="space-y-6">
      <header className="max-w-3xl">
        <p className="eyebrow">02 / Fact review</p>
        <h1 className="page-title">Inspect the claim and its source together.</h1>
        <p className="page-description">
          Verified and rejected candidates remain visible as separate outcomes. Only verified facts
          can enter relationship classification.
        </p>
      </header>

      <Card>
        <CardContent className="grid gap-4 p-4 lg:grid-cols-[minmax(220px,0.9fr)_minmax(280px,1.5fr)_auto] lg:items-end">
          <label className="space-y-2">
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
                  <SelectItem key={document.id} value={document.id}>
                    {document.file_name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </label>
          <label className="space-y-2">
            <span className="field-label">Document ID</span>
            <Input
              value={selectedDocumentId}
              onChange={(event) => onSelectedDocumentChange(event.target.value)}
              placeholder="Paste a document UUID"
              spellCheck={false}
            />
          </label>
          <Button onClick={() => void loadFacts()} disabled={!selectedDocumentId.trim() || isLoading}>
            {isLoading ? (
              <LoaderCircle className="size-4 animate-spin" aria-hidden="true" />
            ) : (
              <Search className="size-4" aria-hidden="true" />
            )}
            {isLoading ? "Loading…" : "Load ledger"}
          </Button>
        </CardContent>
      </Card>

      {error ? (
        <div role="alert" className="rounded-xl border border-rose-400/25 bg-rose-400/7 p-4 text-sm text-rose-200">
          {error}
        </div>
      ) : null}

      {!result || result.documentId !== selectedDocumentId.trim() ? (
        <EmptyState
          icon={FileSearch}
          title="Choose a fact source"
          description="Select an uploaded document or paste its identifier, then load the fact ledger."
          detail="Evidence and confidence stay attached to each claim"
        />
      ) : facts.length === 0 ? (
        <EmptyState
          icon={FileSearch}
          title="No facts are available"
          description="The document may still be processing, or extraction produced no candidate facts."
          detail="Check the document status before retrying"
        />
      ) : (
        <>
          <section className="grid gap-3 sm:grid-cols-3" aria-label="Fact ledger summary">
            {[
              { label: "Extracted", value: facts.length, icon: Braces, color: "text-sky-300" },
              {
                label: "Evidence verified",
                value: verifiedCount,
                icon: CheckCircle2,
                color: "text-emerald-300",
              },
              {
                label: "Rejected",
                value: facts.length - verifiedCount,
                icon: AlertTriangle,
                color: "text-amber-300",
              },
            ].map((metric) => (
              <Card key={metric.label} className="bg-card/70">
                <CardContent className="flex items-center justify-between p-4">
                  <div>
                    <p className="text-xs text-muted-foreground">{metric.label}</p>
                    <p className="mt-1 font-mono text-2xl font-semibold text-foreground">
                      {metric.value}
                    </p>
                  </div>
                  <metric.icon className={cn("size-5", metric.color)} aria-hidden="true" />
                </CardContent>
              </Card>
            ))}
          </section>

          <div className="grid gap-4 xl:grid-cols-[minmax(280px,0.72fr)_minmax(0,1.5fr)]">
            <Card className="h-fit bg-card/70">
              <div className="flex items-center justify-between border-b border-border p-4">
                <div>
                  <p className="eyebrow">Fact index</p>
                  <h2 className="text-sm font-semibold">{facts.length} candidates</h2>
                </div>
                <Button
                  variant="ghost"
                  size="icon"
                  aria-label="Export fact ledger"
                  title="Export fact ledger"
                  onClick={() => downloadJson(`facts-${selectedDocumentId.slice(0, 8)}.json`, facts)}
                >
                  <Download className="size-4" aria-hidden="true" />
                </Button>
              </div>
              <div className="max-h-[680px] space-y-1 overflow-y-auto p-2">
                {facts.map((fact, index) => (
                  <button
                    key={fact.id}
                    type="button"
                    className={cn(
                      "w-full cursor-pointer rounded-lg border border-transparent p-3 text-left outline-none transition-colors hover:bg-muted/70 focus-visible:ring-2 focus-visible:ring-ring",
                      selectedFact?.id === fact.id && "border-border bg-secondary",
                    )}
                    aria-pressed={selectedFact?.id === fact.id}
                    onClick={() => setSelectedFactId(fact.id)}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <span className="font-mono text-[10px] text-slate-500">
                        {String(index + 1).padStart(2, "0")}
                      </span>
                      <StatusBadge status={fact.evidence.status} />
                    </div>
                    <p className="mt-2 truncate text-sm font-semibold text-foreground">
                      {fact.subject}
                    </p>
                    <p className="mt-1 truncate text-xs text-muted-foreground">{fact.predicate}</p>
                    <p className="mt-2 truncate font-mono text-xs text-slate-300">{fact.value}</p>
                  </button>
                ))}
              </div>
            </Card>
            {selectedFact ? <FactInspector fact={selectedFact} /> : null}
          </div>
        </>
      )}
    </div>
  )
}
