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
    <div className="rounded-lg border border-border bg-background/35 p-3.5">
      <div className="mb-2.5 flex items-center justify-between gap-3">
        <span className="text-xs font-medium text-muted-foreground">{label}</span>
        <Badge variant={tone}>{confidenceLabel(score.value)}</Badge>
      </div>
      <Progress value={score.value * 100} />
      <p className="mt-2 truncate font-mono text-[10px] text-slate-500" title={score.method}>
        {score.method}
      </p>
    </div>
  )
}
