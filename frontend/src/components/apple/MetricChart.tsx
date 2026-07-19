import { cn } from "../../lib/utils";

type MiniSparklineProps = {
  data: number[];
  color?: string;
  height?: number;
  className?: string;
};

/** Lightweight SVG sparkline — no chart lib required */
export function MiniSparkline({
  data,
  color = "#007AFF",
  height = 32,
  className,
}: MiniSparklineProps) {
  if (!data.length) return null;
  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;
  const w = 100;
  const h = height;
  const pts = data
    .map((v, i) => {
      const x = (i / (data.length - 1 || 1)) * w;
      const y = h - ((v - min) / range) * (h - 4) - 2;
      return `${x},${y}`;
    })
    .join(" ");

  return (
    <svg
      viewBox={`0 0 ${w} ${h}`}
      className={cn("w-full", className)}
      style={{ height }}
      preserveAspectRatio="none"
      aria-hidden
    >
      <defs>
        <linearGradient id={`sg-${color.replace("#", "")}`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity="0.28" />
          <stop offset="100%" stopColor={color} stopOpacity="0" />
        </linearGradient>
      </defs>
      <polyline
        fill="none"
        stroke={color}
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        points={pts}
        vectorEffect="non-scaling-stroke"
      />
      <polygon
        points={`0,${h} ${pts} ${w},${h}`}
        fill={`url(#sg-${color.replace("#", "")})`}
      />
    </svg>
  );
}

type BarChartProps = {
  values: { label: string; value: number; color?: string }[];
  max?: number;
  height?: number;
  className?: string;
};

export function BarChart({
  values,
  max,
  height = 120,
  className,
}: BarChartProps) {
  const peak = max ?? Math.max(...values.map((v) => v.value), 1);

  return (
    <div className={cn("flex items-end gap-1.5 w-full", className)} style={{ height }}>
      {values.map((v, i) => {
        const pct = Math.max(6, (v.value / peak) * 100);
        return (
          <div key={v.label + i} className="flex-1 flex flex-col items-center gap-1.5 h-full justify-end">
            <div
              className="w-full rounded-t-[6px] chart-bar"
              style={{
                height: `${pct}%`,
                background: v.color ?? "#007AFF",
                animationDelay: `${i * 40}ms`,
                opacity: 0.9,
              }}
            />
            <span className="text-[10px] text-[#8E8E93] font-medium tabular-nums">
              {v.label}
            </span>
          </div>
        );
      })}
    </div>
  );
}

type BpChartProps = {
  series: { day: string; sys: number; dia: number }[];
  className?: string;
};

/** Dual-series blood pressure bars (sys/dia) */
export function BpChart({ series, className }: BpChartProps) {
  const max = Math.max(...series.flatMap((s) => [s.sys, s.dia]), 140);
  const min = 60;
  const range = max - min;

  return (
    <div className={cn("w-full", className)}>
      <div className="flex items-end gap-1 h-[140px]">
        {series.map((s, i) => {
          const sysH = ((s.sys - min) / range) * 100;
          const diaH = ((s.dia - min) / range) * 100;
          return (
            <div key={s.day + i} className="flex-1 flex flex-col items-center justify-end h-full gap-0.5">
              <div className="relative w-full flex items-end justify-center gap-[2px] h-full">
                <div
                  className="w-[45%] max-w-[10px] rounded-full chart-bar"
                  style={{
                    height: `${sysH}%`,
                    background: "linear-gradient(180deg,#FF2D55,#FF6B8A)",
                    animationDelay: `${i * 30}ms`,
                  }}
                />
                <div
                  className="w-[45%] max-w-[10px] rounded-full chart-bar"
                  style={{
                    height: `${diaH}%`,
                    background: "linear-gradient(180deg,#5AC8FA,#A8E0FF)",
                    animationDelay: `${i * 30 + 20}ms`,
                  }}
                />
              </div>
              {i % 2 === 0 && (
                <span className="text-[9px] text-[#AEAEB2] tabular-nums">{s.day}</span>
              )}
            </div>
          );
        })}
      </div>
      <div className="flex gap-4 mt-3 justify-center">
        <LegendDot color="#FF2D55" label="Систола" />
        <LegendDot color="#5AC8FA" label="Диастола" />
      </div>
    </div>
  );
}

function LegendDot({ color, label }: { color: string; label: string }) {
  return (
    <span className="flex items-center gap-1.5 text-[12px] text-[#8E8E93]">
      <span className="w-2 h-2 rounded-full" style={{ background: color }} />
      {label}
    </span>
  );
}

type ActivityRingsProps = {
  move: number;
  moveGoal: number;
  exercise: number;
  exerciseGoal: number;
  stand: number;
  standGoal: number;
  size?: number;
};

/** Apple Watch–style activity rings */
export function ActivityRings({
  move,
  moveGoal,
  exercise,
  exerciseGoal,
  stand,
  standGoal,
  size = 120,
}: ActivityRingsProps) {
  const rings = [
    { value: move / moveGoal, color: "#FF2D55", label: "Move" },
    { value: exercise / exerciseGoal, color: "#34C759", label: "Exercise" },
    { value: stand / standGoal, color: "#5AC8FA", label: "Stand" },
  ];
  const stroke = 10;
  const gap = 4;
  const cx = size / 2;
  const cy = size / 2;

  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
      {rings.map((r, i) => {
        const radius = size / 2 - stroke / 2 - i * (stroke + gap);
        const circ = 2 * Math.PI * radius;
        const pct = Math.min(1, Math.max(0, r.value));
        return (
          <g key={r.label}>
            <circle
              cx={cx}
              cy={cy}
              r={radius}
              fill="none"
              stroke={`${r.color}22`}
              strokeWidth={stroke}
            />
            <circle
              cx={cx}
              cy={cy}
              r={radius}
              fill="none"
              stroke={r.color}
              strokeWidth={stroke}
              strokeLinecap="round"
              strokeDasharray={circ}
              strokeDashoffset={circ * (1 - pct)}
              transform={`rotate(-90 ${cx} ${cy})`}
              style={{
                filter: `drop-shadow(0 0 4px ${r.color}66)`,
                transition: "stroke-dashoffset 0.8s cubic-bezier(0.22,1,0.36,1)",
              }}
            />
          </g>
        );
      })}
    </svg>
  );
}
