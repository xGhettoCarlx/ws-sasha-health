import type { ReactNode } from "react";
import { cn } from "../../lib/utils";

type PageHeaderProps = {
  title: string;
  subtitle?: string;
  large?: boolean;
  trailing?: ReactNode;
  className?: string;
};

export function PageHeader({
  title,
  subtitle,
  large = true,
  trailing,
  className,
}: PageHeaderProps) {
  return (
    <header
      className={cn(
        "flex items-end justify-between gap-3 mb-5 fade-up",
        className,
      )}
    >
      <div className="min-w-0">
        {subtitle && (
          <p className="caption mb-1 uppercase tracking-wide text-[11px] font-semibold">
            {subtitle}
          </p>
        )}
        <h1 className={cn(large ? "large-title" : "section-title", "truncate")}>
          {title}
        </h1>
      </div>
      {trailing && <div className="shrink-0 pb-1">{trailing}</div>}
    </header>
  );
}

export function SectionHeader({
  title,
  action,
  className,
}: {
  title: string;
  action?: ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("flex items-center justify-between mb-3 px-0.5", className)}>
      <h2 className="section-title">{title}</h2>
      {action}
    </div>
  );
}
