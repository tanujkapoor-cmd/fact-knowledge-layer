import { useEffect, useRef, useState, type DragEvent } from "react"
import { motion } from "motion/react"
import {
  Check,
  FileCheck2,
  FileText,
  Fingerprint,
  RefreshCw,
  ScanSearch,
  ShieldCheck,
  UploadCloud,
} from "lucide-react"

import { StatusBadge } from "@/components/status-badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { api } from "@/lib/api"
import type { DocumentStatus, TrackedDocument } from "@/lib/types"
import { cn, formatFileSize } from "@/lib/utils"

const MAX_UPLOAD_BYTES = 100 * 1024 * 1024
const ACTIVE_STATUSES: DocumentStatus[] = [
  "queued",
  "ingesting",
  "extracting",
  "verifying",
  "normalizing",
  "classifying",
]

const PIPELINE_STEPS = [
  { label: "Ingest", detail: "Page text + offsets", status: "ingesting" },
  { label: "Extract", detail: "Structured candidate facts", status: "extracting" },
  { label: "Verify", detail: "Exact source recovery", status: "verifying" },
  { label: "Reason", detail: "Deterministic comparison", status: "classifying" },
] as const

function stepIndex(status?: DocumentStatus) {
  if (!status || status === "queued") return -1
  if (status === "ingesting") return 0
  if (status === "extracting") return 1
  if (status === "verifying") return 2
  if (status === "normalizing") return 2
  if (status === "classifying") return 3
  if (status === "completed") return 4
  return -1
}

function validateFile(candidate: File) {
  if (!candidate.name.toLowerCase().endsWith(".pdf")) return "Choose a PDF file."
  if (!candidate.size) return "The selected PDF is empty."
  if (candidate.size > MAX_UPLOAD_BYTES) return "The PDF exceeds the 100 MB limit."
  return null
}

interface DocumentsViewProps {
  documents: TrackedDocument[]
  onDocumentUpdate: (document: TrackedDocument) => void
  onOpenFacts: (documentId: string) => void
}

export function DocumentsView({
  documents,
  onDocumentUpdate,
  onOpenFacts,
}: DocumentsViewProps) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [file, setFile] = useState<File | null>(null)
  const [dragActive, setDragActive] = useState(false)
  const [isUploading, setIsUploading] = useState(false)
  const [refreshingId, setRefreshingId] = useState<string | null>(null)
  const [notice, setNotice] = useState<{ tone: "success" | "danger"; text: string } | null>(
    null,
  )

  const currentDocument = documents[0]
  const currentStep = stepIndex(currentDocument?.status)

  async function refreshDocument(document: TrackedDocument, silent = false) {
    if (!silent) setRefreshingId(document.id)
    try {
      const status = await api.documentStatus(document.id)
      onDocumentUpdate({ ...document, ...status })
    } catch (error) {
      if (!silent) {
        setNotice({
          tone: "danger",
          text: error instanceof Error ? error.message : "Could not refresh document status.",
        })
      }
    } finally {
      if (!silent) setRefreshingId(null)
    }
  }

  useEffect(() => {
    const active = documents.filter((document) => ACTIVE_STATUSES.includes(document.status))
    if (!active.length) return
    const interval = window.setInterval(() => {
      active.forEach((document) => void refreshDocument(document, true))
    }, 2500)
    return () => window.clearInterval(interval)
  })

  function chooseFile(candidate: File | null) {
    setNotice(null)
    if (!candidate) {
      setFile(null)
      return
    }
    const problem = validateFile(candidate)
    if (problem) {
      setFile(null)
      setNotice({ tone: "danger", text: problem })
      return
    }
    setFile(candidate)
  }

  function handleDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault()
    setDragActive(false)
    chooseFile(event.dataTransfer.files.item(0))
  }

  async function handleUpload(retryFailed = false) {
    if (!file) return
    setIsUploading(true)
    setNotice(null)
    try {
      const document = await api.uploadDocument(file, retryFailed)
      onDocumentUpdate(document)
      const failedDuplicate = document.duplicate_reused && document.status === "failed"
      if (!failedDuplicate) {
        setFile(null)
        if (inputRef.current) inputRef.current.value = ""
      }
      setNotice({
        tone: failedDuplicate ? "danger" : "success",
        text: document.retry_started
          ? "Retry started from a clean extraction checkpoint."
          : failedDuplicate
            ? "This exact PDF has a failed analysis. Review the failure below, then retry it."
            : document.duplicate_reused
              ? "Exact duplicate found. Existing completed analysis has been reused."
          : "Document accepted. Status updates will appear automatically.",
      })
    } catch (error) {
      setNotice({
        tone: "danger",
        text: error instanceof Error ? error.message : "Upload failed.",
      })
    } finally {
      setIsUploading(false)
    }
  }

  return (
    <div className="space-y-4">
      <header className="flex flex-wrap items-end justify-between gap-3 border-b border-border pb-3">
        <div className="max-w-3xl">
        <h1 className="page-title">Source intake register</h1>
        <p className="page-description">
          Register a PDF, monitor extraction, then open its grounded claim ledger.
        </p>
        </div>
        <span className="font-mono text-[9px] uppercase tracking-[0.06em] text-muted-foreground">{documents.length} sources tracked</span>
      </header>

      <section className="grid overflow-hidden border border-border bg-card md:grid-cols-3" aria-label="System guarantees">
        {[
          {
            icon: Fingerprint,
            title: "Content-addressed",
            text: "SHA-256 prevents duplicate processing.",
          },
          {
            icon: FileCheck2,
            title: "Evidence first",
            text: "Page, quote, and offsets stay together.",
          },
          {
            icon: ShieldCheck,
            title: "Auditable decisions",
            text: "Every comparison keeps its ordered trace.",
          },
        ].map((item, index) => (
          <motion.div
            key={item.title}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.24, delay: index * 0.04 }}
          >
            <div className="h-full border-b border-border p-3 last:border-b-0 md:border-b-0 md:border-r md:last:border-r-0">
              <div className="flex items-start gap-3">
                <div className="grid size-8 shrink-0 place-items-center border border-primary bg-primary text-primary-foreground">
                  <item.icon className="size-4" aria-hidden="true" />
                </div>
                <div>
                  <h2 className="text-sm font-semibold">{item.title}</h2>
                  <p className="mt-1 text-xs leading-5 text-muted-foreground">{item.text}</p>
                </div>
              </div>
            </div>
          </motion.div>
        ))}
      </section>

      <section className="grid gap-4 md:grid-cols-[minmax(0,1.45fr)_minmax(240px,0.75fr)]">
        <Card>
          <CardHeader>
            <div className="flex items-start justify-between gap-4">
              <div>
                <CardTitle>Upload one PDF</CardTitle>
                <CardDescription>Schema-independent extraction · maximum 100 MB</CardDescription>
              </div>
              <UploadCloud className="size-5 text-accent" aria-hidden="true" />
            </div>
          </CardHeader>
          <CardContent>
            <div
              className={cn(
                "group grid min-h-48 place-items-center rounded-[3px] border border-dashed border-border bg-surface-low p-6 text-center transition-colors",
                dragActive && "border-accent bg-accent/7",
              )}
              onDragEnter={(event) => {
                event.preventDefault()
                setDragActive(true)
              }}
              onDragOver={(event) => event.preventDefault()}
              onDragLeave={() => setDragActive(false)}
              onDrop={handleDrop}
            >
              <div>
                <div className="mx-auto grid size-11 place-items-center border border-primary bg-card text-primary transition-colors group-hover:bg-secondary">
                  <FileText className="size-5" aria-hidden="true" />
                </div>
                {file ? (
                  <>
                    <p className="mt-4 text-sm font-semibold text-foreground">{file.name}</p>
                    <p className="mt-1 font-mono text-[11px] text-muted-foreground">
                      {formatFileSize(file.size)} · PDF READY
                    </p>
                  </>
                ) : (
                  <>
                    <p className="mt-4 text-sm font-semibold text-foreground">
                      Drop a PDF here, or choose a file
                    </p>
                    <p className="mt-1 text-xs text-muted-foreground">
                      The document is parsed page by page.
                    </p>
                  </>
                )}
                <input
                  ref={inputRef}
                  id="pdf-upload"
                  type="file"
                  accept="application/pdf,.pdf"
                  className="hidden"
                  onChange={(event) => chooseFile(event.target.files?.item(0) || null)}
                />
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  className="mt-4"
                  onClick={() => inputRef.current?.click()}
                >
                  Choose PDF
                </Button>
              </div>
            </div>
            <Button
              className="mt-4 w-full"
              disabled={!file || isUploading}
              onClick={() => void handleUpload(false)}
            >
              {isUploading ? <RefreshCw className="size-4 animate-spin" aria-hidden="true" /> : null}
              {isUploading ? "Sending document…" : "Extract grounded facts"}
            </Button>
            <div aria-live="polite" aria-atomic="true">
              {notice ? (
                <p
                  className={cn(
                    "mt-3 rounded-lg border px-3 py-2 text-sm",
                    notice.tone === "success"
                      ? "border-emerald-700/30 bg-emerald-50 text-emerald-800"
                      : "border-red-700/30 bg-red-50 text-red-800",
                  )}
                >
                  {notice.text}
                </p>
              ) : null}
            </div>
          </CardContent>
        </Card>

        <Card className="overflow-hidden bg-surface-low">
          <CardHeader>
            <CardTitle>No claim without a trail.</CardTitle>
            <CardDescription>
              Model output is treated as a candidate until the quote is recovered from source.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {[
              ["Locate", "Physical PDF page plus optional printed label"],
              ["Recover", "Actual source substring with page-local offsets"],
              ["Separate", "Extraction, evidence, and classification confidence"],
            ].map(([title, detail]) => (
              <div key={title} className="border-l border-accent pl-4">
                <p className="text-sm font-semibold text-foreground">{title}</p>
                <p className="mt-1 text-xs leading-5 text-muted-foreground">{detail}</p>
              </div>
            ))}
          </CardContent>
        </Card>
      </section>

      <section className="overflow-hidden rounded-[4px] border border-border bg-card">
        <div className="grid sm:grid-cols-2 xl:grid-cols-4">
          {PIPELINE_STEPS.map((step, index) => {
            const complete = currentStep > index
            const active = currentStep === index
            return (
              <div
                key={step.label}
                className="relative flex min-h-24 gap-3 border-b border-border p-4 last:border-b-0 sm:border-r sm:[&:nth-child(2)]:border-r-0 xl:border-b-0 xl:[&:nth-child(2)]:border-r xl:last:border-r-0"
              >
                <div
                  className={cn(
                    "grid size-7 shrink-0 place-items-center border font-mono text-[10px]",
                    complete && "border-accent bg-accent text-accent-foreground",
                    active && "border-accent bg-accent/10 text-accent",
                    !complete && !active && "border-border text-slate-500",
                  )}
                >
                  {complete ? <Check className="size-3.5" aria-hidden="true" /> : `0${index + 1}`}
                </div>
                <div>
                  <p className="font-mono text-xs font-semibold uppercase tracking-[0.08em]">
                    {step.label}
                  </p>
                  <p className="mt-1 text-xs leading-5 text-muted-foreground">{step.detail}</p>
                  {active ? (
                    <span className="mt-2 inline-flex items-center gap-1.5 font-mono text-[10px] uppercase text-accent">
                      <span className="size-1.5 animate-pulse rounded-full bg-accent" /> Active
                    </span>
                  ) : null}
                </div>
              </div>
            )
          })}
        </div>
      </section>

      <section>
        <div className="mb-3 flex items-end justify-between gap-4">
          <div>
            <h2 className="text-lg font-semibold tracking-tight">Tracked documents</h2>
          </div>
          <span className="font-mono text-[11px] text-slate-500">{documents.length} TOTAL</span>
        </div>
        {documents.length ? (
          <div className="grid min-w-0 grid-cols-[minmax(0,1fr)] gap-3">
            {documents.map((document) => (
              <Card key={document.id} className="min-w-0">
                <CardContent className="flex min-w-0 flex-col gap-4 p-4 md:flex-row md:items-center md:justify-between">
                  <div className="flex min-w-0 items-center gap-3">
                    <div className="grid size-10 shrink-0 place-items-center border border-border bg-surface-low text-muted-foreground">
                      <ScanSearch className="size-4" aria-hidden="true" />
                    </div>
                    <div className="min-w-0">
                      <p className="truncate text-sm font-semibold text-foreground">
                        {document.file_name}
                      </p>
                      <p className="mt-1 truncate font-mono text-[10px] text-slate-500">
                        {document.id} · {document.page_count ?? "—"} pages
                      </p>
                      {ACTIVE_STATUSES.includes(document.status) ? (
                        <p className="mt-1 font-mono text-[10px] text-muted-foreground">
                          {document.processed_page_count ?? 0}/{document.page_count ?? "?"} pages checkpointed · {document.provider_attempt_count ?? 0} provider attempts
                        </p>
                      ) : null}
                      {document.status === "failed" ? (
                        <p className="mt-2 max-w-3xl text-xs leading-5 text-red-800" role="alert">
                          Analysis stopped: {document.failure_reason || "The backend did not provide a failure reason."} Choose this PDF again and retry; completed documents are never overwritten.
                        </p>
                      ) : null}
                    </div>
                  </div>
                  <div className="flex min-w-0 flex-wrap items-center gap-2">
                    <StatusBadge status={document.status} register={ACTIVE_STATUSES.includes(document.status) ? "RUN" : "DOC"} />
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => void refreshDocument(document)}
                      disabled={refreshingId === document.id}
                    >
                      <RefreshCw
                        className={cn("size-3.5", refreshingId === document.id && "animate-spin")}
                        aria-hidden="true"
                      />
                      Refresh
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => onOpenFacts(document.id)}
                    >
                      Review facts
                    </Button>
                    {document.status === "failed" ? (
                      <Button
                        size="sm"
                        variant="destructive"
                        disabled={!file || isUploading}
                        onClick={() => void handleUpload(true)}
                      >
                        Retry failed analysis
                      </Button>
                    ) : null}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        ) : (
          <div className="grid min-h-40 place-items-center rounded-[4px] border border-dashed border-border bg-card p-6 text-center">
            <div>
              <FileText className="mx-auto size-5 text-slate-500" aria-hidden="true" />
              <p className="mt-3 text-sm font-medium text-foreground">No documents tracked yet</p>
              <p className="mt-1 text-xs text-muted-foreground">
                Your first successful upload will appear here.
              </p>
            </div>
          </div>
        )}
      </section>
    </div>
  )
}
