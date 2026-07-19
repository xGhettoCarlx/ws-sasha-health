import { cn } from "../../lib/utils";
import { GlassCard } from "./GlassCard";
import { MiniSparkline } from "./MetricChart";

type MetricCardProps = {
  label: string;
  value: string;
  unit?: string;
  accent: string;
  trendLabel?: string;
  history?: number[];
  className?: string;
  onClick?: () => void;
};

export function MetricCard({
  label,
  value,
  unit,
  accent,
  trendLabel,
  history,
  className,
  onClick,
}: MetricCardProps) {
  return (
    <GlassCard
      pressable={!!onClick}
      onClick={onClick}
      padding="md"
      className={cn("relative min-h-[132px] flex flex-col justify-between", className)}
    >
      <div className="flex items-start justify-between gap-2">
        <span className="text-[13px] font-medium text-[#8E8E93]">{label}</span>
        <span
          className="w-2 h-2 rounded-full mt-1.5 shrink-0"
          style={{ background: accent, boxShadow: `0 0 0 3px ${accent}22` }}
        />
      </div>

      <div>
        <div className="flex items-baseline gap-1.5">
          <span className="metric-value text-[28px] leading-none text-[#1C1C1E]">
            {value}
          </span>
          {unit && (
            <span className="text-[12px] text-[#8E8E93] font-medium">{unit}</span>
          )}
        </div>
        {trendLabel && (
          <p className="mt-1.5 text-[12px] font-medium" style={{ color: accent }}>
            {trendLabel}
          </p>
        )}
      </div>

      {history && history.length > 1 && (
        <div className="mt-3 -mx-0.5">
          <MiniSparkline data={history} color={accent} height={28} />
        </div>
      )}
    </GlassCard>
  );
}
