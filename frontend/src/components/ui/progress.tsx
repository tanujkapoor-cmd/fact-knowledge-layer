import { cn } from "@/lib/utils"

export function Progress({ value, className }: { value: number; className?: string }) {
  const resolved = Math.min(100, Math.max(0, value))
  return (
    <div
      className={cn("h-1.5 w-full overflow-hidden bg-muted", className)}
      role="progressbar"
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={resolved}
    >
      <div
        className="h-full bg-accent transition-[width] duration-300"
        style={{ width: `${resolved}%` }}
      />
    </div>
  )
}
