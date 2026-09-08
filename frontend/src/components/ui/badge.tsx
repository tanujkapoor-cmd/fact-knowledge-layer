import { cva, type VariantProps } from "class-variance-authority"
import type { HTMLAttributes } from "react"

import { cn } from "@/lib/utils"

const badgeVariants = cva(
  "inline-flex items-center gap-1.5 rounded-[2px] border px-2 py-0.5 font-mono text-[10px] font-semibold tracking-[0.03em]",
  {
    variants: {
      variant: {
        neutral: "border-border bg-surface-low text-muted-foreground",
        success: "border-emerald-700/30 bg-emerald-50 text-emerald-800",
        danger: "border-red-700/30 bg-red-50 text-red-800",
        warning: "border-amber-700/30 bg-amber-50 text-amber-800",
        info: "border-blue-700/25 bg-blue-50 text-blue-800",
      },
    },
    defaultVariants: { variant: "neutral" },
  },
)

interface BadgeProps
  extends HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof badgeVariants> {}

export function Badge({ className, variant, ...props }: BadgeProps) {
  return <span className={cn(badgeVariants({ variant }), className)} {...props} />
}
