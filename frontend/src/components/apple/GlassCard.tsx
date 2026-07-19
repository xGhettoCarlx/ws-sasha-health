import type { ReactNode, HTMLAttributes } from "react";
import { cn } from "../../lib/utils";

type GlassCardProps = HTMLAttributes<HTMLDivElement> & {
  children: ReactNode;
  /** solid white vs frosted glass */
  variant?: "solid" | "glass" | "tinted";
  tint?: string;
  padding?: "none" | "sm" | "md" | "lg";
  pressable?: boolean;
};

const pad = {
  none: "p-0",
  sm: "p-3.5",
  md: "p-4",
  lg: "p-5",
} as const;

export function GlassCard({
  children,
  className,
  variant = "solid",
  tint,
  padding = "md",
  pressable = false,
  style,
  ...rest
}: GlassCardProps) {
  return (
    <div
      className={cn(
        "rounded-[20px] overflow-hidden",
        pad[padding],
        variant === "solid" && "bg-white shadow-[var(--shadow-card)]",
        variant === "glass" && "glass-thick",
        variant === "tinted" && "shadow-[var(--shadow-soft)]",
        pressable && "pressable cursor-pointer",
        className,
      )}
      style={{
        ...(variant === "tinted"
          ? { background: tint ?? "rgba(0,122,255,0.08)" }
          : {}),
        ...style,
      }}
      {...rest}
    >
      {children}
    </div>
  );
}
