import { Circle } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { sentenceCase } from "@/lib/utils"
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

export function StatusBadge({ status }: { status: Status }) {
  return (
    <Badge variant={toneByStatus[status]}>
      <Circle className="size-1.5 fill-current" aria-hidden="true" />
      {sentenceCase(status)}
    </Badge>
  )
}
