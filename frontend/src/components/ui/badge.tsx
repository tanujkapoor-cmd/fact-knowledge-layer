import { cva, type VariantProps } from "class-variance-authority"
import type { HTMLAttributes } from "react"

import { cn } from "@/lib/utils"

const badgeVariants = cva(
  "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 font-mono text-[11px] font-medium tracking-wide",
  {
    variants: {
      variant: {
        neutral: "border-border bg-muted/70 text-muted-foreground",
        success: "border-emerald-400/30 bg-emerald-400/8 text-emerald-300",
        danger: "border-rose-400/30 bg-rose-400/8 text-rose-300",
        warning: "border-amber-400/30 bg-amber-400/8 text-amber-300",
        info: "border-sky-400/30 bg-sky-400/8 text-sky-300",
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
