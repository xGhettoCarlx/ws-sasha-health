import { useMemo, useState } from "react";
import { AlertTriangle, Moon, Plus, Sun } from "lucide-react";
import {
  GlassCard,
  PageHeader,
  SectionHeader,
  StatusPill,
} from "../../../components/apple";
import { mockMedications } from "../../../lib/mock-data";
import { cn } from "../../../lib/utils";

type Filter = "all" | "daily" | "low";

export default function MedicationsPage() {
  const [filter, setFilter] = useState<Filter>("all");

  const meds = useMemo(() => {
    if (filter === "daily") return mockMedications.filter((m) => m.is_daily);
    if (filter === "low") return mockMedications.filter((m) => m.days_left <= 14);
    return mockMedications;
  }, [filter]);

  return (
    <div className="page-shell section-gap">
      <PageHeader
        title="Лекарства"
        subtitle="Аптечка"
        trailing={
          <button
            type="button"
            className="w-10 h-10 rounded-full bg-[#007AFF] text-white flex items-center justify-center pressable shadow-[0_6px_16px_rgba(0,122,255,0.35)]"
            aria-label="Добавить"
          >
            <Plus className="w-5 h-5" strokeWidth={2.5} />
          </button>
        }
      />

      {/* Segmented control — iOS style */}
      <div className="glass rounded-[12px] p-1 flex gap-1">
        {(
          [
            ["all", "Все"],
            ["daily", "Ежедневно"],
            ["low", "Мало"],
          ] as const
        ).map(([key, label]) => (
          <button
            key={key}
            type="button"
            onClick={() => setFilter(key)}
            className={cn(
              "flex-1 h-8 rounded-[9px] text-[13px] font-semibold transition-all",
              filter === key
                ? "bg-white text-[#1C1C1E] shadow-sm"
                : "text-[#8E8E93]",
            )}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Stock alert banner */}
      {mockMedications.some((m) => m.days_left <= 14) && (
        <GlassCard
          variant="tinted"
          tint="rgba(255,149,0,0.12)"
          padding="md"
          className="flex items-start gap-3"
        >
          <AlertTriangle className="w-5 h-5 text-[#FF9500] shrink-0 mt-0.5" />
          <div>
            <p className="text-[15px] font-semibold text-[#1C1C1E]">Запас заканчивается</p>
            <p className="text-[13px] text-[#8E8E93] mt-0.5 leading-snug">
              Аэртал — осталось ~8 дней. Запланируйте покупку или рецепт.
            </p>
          </div>
        </GlassCard>
      )}

      <section>
        <SectionHeader title={`${meds.length} препарата`} />
        <div className="space-y-3">
          {meds.map((m, i) => (
            <GlassCard
              key={m.id}
              padding="md"
              pressable
              className="fade-up"
              style={{ animationDelay: `${i * 50}ms` }}
            >
              <div className="flex gap-3.5">
                <div
                  className="w-12 h-12 rounded-[14px] flex items-center justify-center shrink-0 text-white"
                  style={{
                    background: `linear-gradient(145deg, ${m.color}, ${m.color}cc)`,
                    boxShadow: `0 8px 20px ${m.color}33`,
                  }}
                >
                  {m.frequency.includes("ночь") || m.frequency.includes("вечер") ? (
                    <Moon className="w-5 h-5" />
                  ) : (
                    <Sun className="w-5 h-5" />
                  )}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <p className="text-[17px] font-semibold tracking-tight">{m.name}</p>
                      <p className="text-[14px] text-[#8E8E93] mt-0.5">
                        {m.dose} · {m.frequency}
                      </p>
                    </div>
                    {m.is_daily && <StatusPill tone="info">ежедневно</StatusPill>}
                  </div>

                  {m.notes && (
                    <p className="text-[13px] text-[#AEAEB2] mt-2 leading-snug">{m.notes}</p>
                  )}

                  {/* Stock progress */}
                  <div className="mt-3">
                    <div className="flex justify-between text-[12px] mb-1.5">
                      <span className="text-[#8E8E93]">Запас</span>
                      <span
                        className={cn(
                          "font-semibold tabular-nums",
                          m.days_left <= 14 ? "text-[#FF9500]" : "text-[#1C1C1E]",
                        )}
                      >
                        {m.stock} таб · ~{m.days_left} дн
                      </span>
                    </div>
                    <div className="h-1.5 rounded-full bg-[#E5E5EA] overflow-hidden">
                      <div
                        className="h-full rounded-full transition-all"
                        style={{
                          width: `${Math.min(100, (m.days_left / 60) * 100)}%`,
                          background:
                            m.days_left <= 14
                              ? "linear-gradient(90deg,#FF9500,#FFCC00)"
                              : `linear-gradient(90deg,${m.color},${m.color}aa)`,
                        }}
                      />
                    </div>
                  </div>
                </div>
              </div>
            </GlassCard>
          ))}
        </div>
      </section>
    </div>
  );
}
