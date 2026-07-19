import { CheckCircle2, Circle, Flag } from "lucide-react";
import {
  GlassCard,
  PageHeader,
  SectionHeader,
  StatusPill,
} from "../../../components/apple";
import { mockStrategy } from "../../../lib/mock-data";

export default function StrategyPage() {
  return (
    <div className="page-shell section-gap">
      <PageHeader
        title="План"
        subtitle="Стратегия"
        trailing={<StatusPill tone="info">обн. {mockStrategy.updated}</StatusPill>}
      />

      <GlassCard
        padding="lg"
        style={{
          background: "linear-gradient(145deg, rgba(0,122,255,0.12), rgba(88,86,214,0.1))",
        }}
        className="!bg-transparent border border-white/60 shadow-[var(--shadow-card)]"
      >
        <p className="text-[13px] font-semibold text-[#007AFF] mb-1">Фокус 2026</p>
        <h2 className="text-[22px] font-bold tracking-tight leading-snug">
          {mockStrategy.title}
        </h2>
      </GlassCard>

      <section>
        <SectionHeader title="Ежедневно" />
        <GlassCard padding="none">
          {mockStrategy.daily.map((item, i) => (
            <div key={i}>
              {i > 0 && <div className="hairline ml-12" />}
              <div className="flex items-start gap-3 px-4 py-3.5">
                {i < 2 ? (
                  <CheckCircle2 className="w-6 h-6 text-[#34C759] shrink-0" strokeWidth={1.8} />
                ) : (
                  <Circle className="w-6 h-6 text-[#C7C7CC] shrink-0" strokeWidth={1.8} />
                )}
                <p
                  className={
                    i < 2
                      ? "text-[16px] text-[#8E8E93] line-through decoration-[#C7C7CC]"
                      : "text-[16px] text-[#1C1C1E]"
                  }
                >
                  {item}
                </p>
              </div>
            </div>
          ))}
        </GlassCard>
      </section>

      <section>
        <SectionHeader title="Приоритеты" />
        <div className="space-y-3">
          {mockStrategy.priorities.map((p) => (
            <GlassCard key={p.priority} padding="md" pressable>
              <div className="flex gap-3">
                <div
                  className="w-10 h-10 rounded-[12px] flex items-center justify-center shrink-0 text-white font-bold"
                  style={{
                    background:
                      p.priority === 1
                        ? "linear-gradient(145deg,#FF2D55,#FF6B8A)"
                        : p.priority === 2
                          ? "linear-gradient(145deg,#FF9500,#FFCC00)"
                          : "linear-gradient(145deg,#007AFF,#5AC8FA)",
                  }}
                >
                  {p.priority}
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <p className="text-[17px] font-semibold">{p.title}</p>
                    {p.priority === 1 && <Flag className="w-4 h-4 text-[#FF2D55]" />}
                  </div>
                  <p className="text-[14px] text-[#8E8E93] mt-1 leading-relaxed">{p.detail}</p>
                </div>
              </div>
            </GlassCard>
          ))}
        </div>
      </section>
    </div>
  );
}
