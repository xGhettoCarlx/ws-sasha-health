import type { ReactNode } from "react";
import { ChevronRight } from "lucide-react";
import { cn } from "../../lib/utils";
import { GlassCard } from "./GlassCard";

export function ListGroup({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <GlassCard padding="none" className={cn("divide-y divide-[rgba(60,60,67,0.1)]", className)}>
      {children}
    </GlassCard>
  );
}

type ListRowProps = {
  title: string;
  subtitle?: string;
  detail?: string;
  icon?: ReactNode;
  iconBg?: string;
  trailing?: ReactNode;
  showChevron?: boolean;
  onClick?: () => void;
  destructive?: boolean;
};

export function ListRow({
  title,
  subtitle,
  detail,
  icon,
  iconBg = "#007AFF",
  trailing,
  showChevron = true,
  onClick,
  destructive,
}: ListRowProps) {
  const Comp = onClick ? "button" : "div";
  return (
    <Comp
      type={onClick ? "button" : undefined}
      onClick={onClick}
      className={cn(
        "w-full flex items-center gap-3 px-4 py-3 text-left",
        onClick && "pressable active:bg-black/[0.03]",
      )}
    >
      {icon && (
        <span
          className="w-8 h-8 rounded-[9px] flex items-center justify-center shrink-0 text-white"
          style={{ background: iconBg }}
        >
          {icon}
        </span>
      )}
      <div className="flex-1 min-w-0">
        <p
          className={cn(
            "text-[16px] font-normal leading-snug truncate",
            destructive ? "text-[#FF3B30]" : "text-[#1C1C1E]",
          )}
        >
          {title}
        </p>
        {subtitle && (
          <p className="text-[13px] text-[#8E8E93] truncate mt-0.5">{subtitle}</p>
        )}
      </div>
      {detail && (
        <span className="text-[15px] text-[#8E8E93] tabular-nums shrink-0">{detail}</span>
      )}
      {trailing}
      {showChevron && onClick && (
        <ChevronRight className="w-4 h-4 text-[#C7C7CC] shrink-0" strokeWidth={2.5} />
      )}
    </Comp>
  );
}

export function StatusPill({
  children,
  tone = "neutral",
}: {
  children: ReactNode;
  tone?: "neutral" | "ok" | "warn" | "danger" | "info";
}) {
  const tones = {
    neutral: "bg-[#E5E5EA] text-[#3A3A3C]",
    ok: "bg-[#E8F8ED] text-[#248A3D]",
    warn: "bg-[#FFF4E5] text-[#C93400]",
    danger: "bg-[#FFEBEA] text-[#D70015]",
    info: "bg-[#E5F1FF] text-[#0071E3]",
  };
  return (
    <span
      className={cn(
        "inline-flex items-center px-2.5 py-0.5 rounded-full text-[12px] font-semibold",
        tones[tone],
      )}
    >
      {children}
    </span>
  );
}
