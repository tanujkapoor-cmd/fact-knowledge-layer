import { useMemo, useState } from "react"
import {
  ArrowLeftRight,
  Download,
  GitCompareArrows,
  ListChecks,
  LoaderCircle,
  Network,
  Search,
} from "lucide-react"

import { ConfidenceMeter } from "@/components/confidence-meter"
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
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { api } from "@/lib/api"
import type { Relationship, RelationshipType, TrackedDocument } from "@/lib/types"
import { cn, downloadJson, sentenceCase } from "@/lib/utils"

const RELATIONSHIP_OPTIONS: Array<{ label: string; value: RelationshipType | "all" }> = [
  { label: "All decisions", value: "all" },
  { label: "Corroborates", value: "corroborates" },
  { label: "Contradicts", value: "contradicts" },
  { label: "Reconciled", value: "reconciled" },
  { label: "Uncertain", value: "uncertain" },
]

interface RelationshipsViewProps {
  documents: TrackedDocument[]
  selectedDocumentId: string
  onSelectedDocumentChange: (documentId: string) => void
}

function stringifyDetails(details: Relationship["reasoning_trace"][number]["details"]) {
  const entries = Object.entries(details)
  if (!entries.length) return "No additional values"
  return entries.map(([key, value]) => `${sentenceCase(key)}: ${String(value)}`).join(" · ")
}

export function RelationshipsView({
  documents,
  selectedDocumentId,
  onSelectedDocumentChange,
}: RelationshipsViewProps) {
  const [classification, setClassification] = useState<RelationshipType | "all">("all")
  const [result, setResult] = useState<{
    query: string
    relationships: Relationship[]
  } | null>(null)
  const [selectedRelationshipId, setSelectedRelationshipId] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const queryKey = `${classification}:${selectedDocumentId.trim()}`
  const relationships = useMemo(
    () => (result?.query === queryKey ? result.relationships : []),
    [queryKey, result],
  )
  const selectedRelationship = useMemo(
    () =>
      relationships.find((relationship) => relationship.id === selectedRelationshipId) ||
      relationships[0] ||
      null,
    [relationships, selectedRelationshipId],
  )

  async function loadRelationships() {
    setIsLoading(true)
    setError(null)
    try {
      const items = await api.relationships({
        classification: classification === "all" ? undefined : classification,
        documentId: selectedDocumentId.trim() || undefined,
      })
      setResult({ query: queryKey, relationships: items })
      setSelectedRelationshipId(items[0]?.id || null)
    } catch (loadError) {
      setError(
        loadError instanceof Error ? loadError.message : "Could not load relationship decisions.",
      )
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="space-y-6">
      <header className="max-w-3xl">
        <p className="eyebrow">03 / Decision audit</p>
        <h1 className="page-title">See exactly why two facts agree—or do not.</h1>
        <p className="page-description">
          Classification is deterministic. The interface exposes the ordered checks, both source
          facts, and any context that reconciles a difference.
        </p>
      </header>

      <Card>
        <CardContent className="grid gap-4 p-4 lg:grid-cols-[0.8fr_1fr_1.4fr_auto] lg:items-end">
          <label className="space-y-2">
            <span className="field-label">Decision type</span>
            <Select
              value={classification}
              onValueChange={(value) => setClassification(value as RelationshipType | "all")}
            >
              <SelectTrigger aria-label="Decision type">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {RELATIONSHIP_OPTIONS.map((option) => (
                  <SelectItem key={option.value} value={option.value}>
                    {option.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </label>
          <label className="space-y-2">
            <span className="field-label">Tracked document</span>
            <Select
              value={documents.some((document) => document.id === selectedDocumentId) ? selectedDocumentId : "all"}
              onValueChange={(value) => onSelectedDocumentChange(value === "all" ? "" : value)}
            >
              <SelectTrigger aria-label="Tracked document filter">
                <SelectValue placeholder="All documents" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All documents</SelectItem>
                {documents.map((document) => (
                  <SelectItem key={document.id} value={document.id}>
                    {document.file_name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </label>
          <label className="space-y-2">
            <span className="field-label">Document ID override</span>
            <Input
              value={selectedDocumentId}
              onChange={(event) => onSelectedDocumentChange(event.target.value)}
              placeholder="Optional document UUID"
              spellCheck={false}
            />
          </label>
          <Button onClick={() => void loadRelationships()} disabled={isLoading}>
            {isLoading ? (
              <LoaderCircle className="size-4 animate-spin" aria-hidden="true" />
            ) : (
              <Search className="size-4" aria-hidden="true" />
            )}
            {isLoading ? "Loading…" : "Load decisions"}
          </Button>
        </CardContent>
      </Card>

      {error ? (
        <div role="alert" className="rounded-xl border border-rose-400/25 bg-rose-400/7 p-4 text-sm text-rose-200">
          {error}
        </div>
      ) : null}

      {!result || result.query !== queryKey ? (
        <EmptyState
          icon={Network}
          title="No decision set loaded"
          description="Choose optional filters, then load deterministic relationship decisions."
          detail="The model explains decisions—it never chooses the class"
        />
      ) : relationships.length === 0 ? (
        <EmptyState
          icon={GitCompareArrows}
          title="No matching relationships"
          description="No stored relationship satisfies the current classification and document filters."
          detail="Try all decisions or remove the document filter"
        />
      ) : (
        <div className="grid gap-4 xl:grid-cols-[minmax(300px,0.72fr)_minmax(0,1.5fr)]">
          <Card className="h-fit bg-card/70">
            <div className="flex items-center justify-between border-b border-border p-4">
              <div>
                <p className="eyebrow">Decision index</p>
                <h2 className="text-sm font-semibold">{relationships.length} relationships</h2>
              </div>
              <Button
                variant="ghost"
                size="icon"
                aria-label="Export relationships"
                title="Export relationships"
                onClick={() => downloadJson("relationship-decisions.json", relationships)}
              >
                <Download className="size-4" aria-hidden="true" />
              </Button>
            </div>
            <div className="max-h-[720px] space-y-1 overflow-y-auto p-2">
              {relationships.map((relationship, index) => (
                <button
                  key={relationship.id}
                  type="button"
                  className={cn(
                    "w-full cursor-pointer rounded-lg border border-transparent p-3 text-left outline-none transition-colors hover:bg-muted/70 focus-visible:ring-2 focus-visible:ring-ring",
                    selectedRelationship?.id === relationship.id && "border-border bg-secondary",
                  )}
                  aria-pressed={selectedRelationship?.id === relationship.id}
                  onClick={() => setSelectedRelationshipId(relationship.id)}
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-mono text-[10px] text-slate-500">
                      {String(index + 1).padStart(2, "0")}
                    </span>
                    <StatusBadge status={relationship.classification} />
                  </div>
                  <div className="mt-3 flex items-center gap-2 text-sm font-semibold text-foreground">
                    <span className="truncate">{relationship.fact_a.subject}</span>
                    <ArrowLeftRight className="size-3.5 shrink-0 text-slate-500" aria-hidden="true" />
                    <span className="truncate">{relationship.fact_b.subject}</span>
                  </div>
                  <p className="mt-1 truncate text-xs text-muted-foreground">
                    {relationship.fact_a.predicate}
                  </p>
                </button>
              ))}
            </div>
          </Card>

          {selectedRelationship ? (
            <Card className="overflow-hidden">
              <div className="flex flex-col gap-4 border-b border-border p-5 sm:flex-row sm:items-start sm:justify-between">
                <div>
                  <p className="eyebrow">Deterministic outcome</p>
                  <div className="mt-1 flex flex-wrap items-center gap-3">
                    <h2 className="text-xl font-semibold tracking-tight">
                      {sentenceCase(selectedRelationship.classification)}
                    </h2>
                    <StatusBadge status={selectedRelationship.classification} />
                  </div>
                  {selectedRelationship.reconciliation_reasons.length ? (
                    <p className="mt-2 text-sm text-muted-foreground">
                      Explained by {selectedRelationship.reconciliation_reasons.join(", ")}.
                    </p>
                  ) : null}
                </div>
                <div className="w-full sm:max-w-56">
                  <ConfidenceMeter
                    label="Classification confidence"
                    score={selectedRelationship.classification_confidence}
                    tone={
                      selectedRelationship.classification === "uncertain" ? "warning" : "success"
                    }
                  />
                </div>
              </div>

              <Tabs defaultValue="trace" className="p-5">
                <TabsList>
                  <TabsTrigger value="trace">
                    <ListChecks className="mr-1.5 size-3.5" aria-hidden="true" /> Trace
                  </TabsTrigger>
                  <TabsTrigger value="sources">
                    <GitCompareArrows className="mr-1.5 size-3.5" aria-hidden="true" /> Source facts
                  </TabsTrigger>
                </TabsList>
                <TabsContent value="trace">
                  <div className="mt-2 overflow-hidden rounded-xl border border-border">
                    <div className="hidden grid-cols-[56px_1fr_120px_1.5fr] gap-3 border-b border-border bg-background/55 px-4 py-3 font-mono text-[10px] uppercase tracking-[0.1em] text-slate-500 md:grid">
                      <span>Order</span>
                      <span>Check</span>
                      <span>Outcome</span>
                      <span>Details</span>
                    </div>
                    {selectedRelationship.reasoning_trace.map((step) => (
                      <div
                        key={`${step.order}-${step.check}`}
                        className="grid gap-2 border-b border-border px-4 py-3 last:border-b-0 md:grid-cols-[56px_1fr_120px_1.5fr] md:items-center md:gap-3"
                      >
                        <span className="font-mono text-[11px] text-slate-500">
                          {String(step.order).padStart(2, "0")}
                        </span>
                        <span className="text-sm font-medium text-foreground">{step.check}</span>
                        <span
                          className={cn(
                            "w-fit font-mono text-[10px] uppercase tracking-[0.08em]",
                            step.outcome === "passed" && "text-emerald-300",
                            step.outcome === "failed" && "text-rose-300",
                            step.outcome === "skipped" && "text-slate-500",
                            step.outcome === "judgment_required" && "text-amber-300",
                          )}
                        >
                          {sentenceCase(step.outcome)}
                        </span>
                        <span className="text-xs leading-5 text-muted-foreground">
                          {stringifyDetails(step.details)}
                        </span>
                      </div>
                    ))}
                  </div>
                </TabsContent>
                <TabsContent value="sources" className="mt-2 space-y-4">
                  <FactInspector fact={selectedRelationship.fact_a} label="Fact A" />
                  <FactInspector fact={selectedRelationship.fact_b} label="Fact B" />
                </TabsContent>
              </Tabs>
            </Card>
          ) : null}
        </div>
      )}
    </div>
  )
}
