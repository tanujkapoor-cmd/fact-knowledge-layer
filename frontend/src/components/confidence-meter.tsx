import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import type { ConfidenceScore } from "@/lib/types"
import { confidenceLabel } from "@/lib/utils"

export function ConfidenceMeter({
  label,
  score,
  tone = "info",
}: {
  label: string
  score: ConfidenceScore
  tone?: "info" | "success" | "warning"
}) {
  return (
    <div className="border-r border-border bg-card px-3 py-2.5 last:border-r-0">
      <div className="mb-2 flex items-center justify-between gap-3">
        <span className="data-label">{label}</span>
        <Badge variant={tone}>{confidenceLabel(score.value)}</Badge>
      </div>
      <Progress value={score.value * 100} />
      <div className="mt-1.5 flex items-center justify-between gap-2 font-mono text-[9px] text-muted-foreground">
        <span className="truncate" title={score.method}>{score.method}</span>
        <span className="tabular">{Math.round(score.value * 100)}%</span>
      </div>
    </div>
  )
}
