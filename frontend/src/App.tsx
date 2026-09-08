import { useCallback, useEffect, useState } from "react"
import { AnimatePresence, motion, MotionConfig } from "motion/react"

import { AppShell, type ViewId } from "@/components/app-shell"
import { DocumentsView } from "@/features/documents/documents-view"
import { FactsView } from "@/features/facts/facts-view"
import { RelationshipsView } from "@/features/relationships/relationships-view"
import { EvidenceWorkspace } from "@/features/workspace/evidence-workspace"
import { api, API_DOCS_URL } from "@/lib/api"
import type { TrackedDocument } from "@/lib/types"

const STORAGE_KEY = "fact-knowledge-layer.documents"

function loadStoredDocuments(): TrackedDocument[] {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY)
    if (!raw) return []
    const parsed = JSON.parse(raw) as unknown
    return Array.isArray(parsed) ? (parsed as TrackedDocument[]) : []
  } catch {
    return []
  }
}

export default function App() {
  const [activeView, setActiveView] = useState<ViewId>("documents")
  const [documents, setDocuments] = useState<TrackedDocument[]>(loadStoredDocuments)
  const [selectedDocumentId, setSelectedDocumentId] = useState(() => documents[0]?.id || "")
  const [apiState, setApiState] = useState<"checking" | "ready" | "offline">("checking")

  useEffect(() => {
    let cancelled = false
    void api
      .health()
      .then(() => {
        if (!cancelled) setApiState("ready")
      })
      .catch(() => {
        if (!cancelled) setApiState("offline")
      })
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(documents))
  }, [documents])

  const updateDocument = useCallback((incoming: TrackedDocument) => {
    setDocuments((current) => [
      incoming,
      ...current.filter((document) => document.id !== incoming.id),
    ])
    setSelectedDocumentId((current) => current || incoming.id)
  }, [])

  function openFacts(documentId: string) {
    setSelectedDocumentId(documentId)
    setActiveView("facts")
  }

  return (
    <MotionConfig reducedMotion="user">
      <AppShell
        activeView={activeView}
        onViewChange={setActiveView}
        apiState={apiState}
        apiDocsUrl={API_DOCS_URL}
      >
        <div className="hidden lg:block">
          <EvidenceWorkspace
            documents={documents}
            selectedDocumentId={selectedDocumentId}
            onSelectedDocumentChange={setSelectedDocumentId}
            onDocumentUpdate={updateDocument}
          />
        </div>
        <div className="lg:hidden">
          <AnimatePresence mode="wait" initial={false}>
            <motion.div
              key={activeView}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -4 }}
              transition={{ duration: 0.2, ease: "easeOut" }}
            >
              {activeView === "documents" ? (
                <DocumentsView
                  documents={documents}
                  onDocumentUpdate={updateDocument}
                  onOpenFacts={openFacts}
                />
              ) : null}
              {activeView === "facts" ? (
                <FactsView
                  documents={documents}
                  selectedDocumentId={selectedDocumentId}
                  onSelectedDocumentChange={setSelectedDocumentId}
                />
              ) : null}
              {activeView === "relationships" ? (
                <RelationshipsView
                  documents={documents}
                  selectedDocumentId={selectedDocumentId}
                  onSelectedDocumentChange={setSelectedDocumentId}
                />
              ) : null}
            </motion.div>
          </AnimatePresence>
        </div>
      </AppShell>
    </MotionConfig>
  )
}
