import { forwardRef } from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const statusBadgeVariants = cva(
  "inline-flex items-center rounded-full font-medium",
  {
    variants: {
      variant: {
        normal: "text-sh-status-normal",
        warning: "bg-[rgba(234,179,8,0.1)] text-[#FDE047]",
        critical: "bg-[rgba(239,68,68,0.1)] text-[#FCA5A5]",
        verified: "text-[11px] uppercase tracking-wide bg-white/[0.10] rounded-[4px] px-[6px] py-[2px] text-sh-primary",
      },
      size: {
        sm: "h-6 px-2 text-xs",
        lg: "h-7 px-3 text-sm",
      },
    },
    defaultVariants: {
      variant: "normal",
      size: "sm",
    },
  },
);

interface StatusBadgeProps
  extends VariantProps<typeof statusBadgeVariants> {
  label: string;
  className?: string;
}

const StatusBadge = forwardRef<HTMLSpanElement, StatusBadgeProps>(
  ({ label, variant, size, className }, ref) => {
    return (
      <span
        ref={ref}
        className={cn(statusBadgeVariants({ variant, size }), className)}
      >
        {label}
      </span>
    );
  },
);

StatusBadge.displayName = "StatusBadge";

export { StatusBadge, statusBadgeVariants };
