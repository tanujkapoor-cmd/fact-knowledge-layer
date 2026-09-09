import { Badge } from "@/components/ui/badge"
import type { DocumentStatus, EvidenceStatus, RelationshipType } from "@/lib/types"

type Status = DocumentStatus | EvidenceStatus | RelationshipType

const toneByStatus = {
  completed: "success",
  verified: "success",
  corroborates: "success",
  failed: "danger",
  contradicts: "danger",
  reconciled: "info",
  uncertain: "warning",
  queued: "neutral",
  ingesting: "info",
  extracting: "info",
  verifying: "info",
  normalizing: "info",
  classifying: "info",
} as const

const registerByStatus: Record<Status, string> = {
  completed: "DOC",
  queued: "RUN",
  ingesting: "RUN",
  extracting: "RUN",
  verifying: "RUN",
  normalizing: "RUN",
  classifying: "RUN",
  verified: "EVD",
  failed: "EVD",
  corroborates: "REL",
  contradicts: "REL",
  reconciled: "REL",
  uncertain: "REL",
}

export function StatusBadge({ status, register }: { status: Status; register?: "DOC" | "RUN" | "EVD" | "REL" }) {
  return (
    <Badge variant={toneByStatus[status]} className="gap-1.5 border-l-2 font-mono text-[8px] font-semibold uppercase tracking-[0.055em] tabular">
      <span className="opacity-60">{register || registerByStatus[status]}</span>
      <span aria-hidden="true">/</span>
      {status}
    </Badge>
  )
}
