import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, Moon, Sun } from "lucide-react";
import {
  GlassCard,
  PageHeader,
  SectionHeader,
  StatusPill,
} from "../../../components/apple";
import { fetchMedications } from "../../../lib/services";
import type { Medication } from "../../../lib/types";
import { cn } from "../../../lib/utils";

type Filter = "all" | "daily" | "low";

const PALETTE = ["#007AFF", "#34C759", "#AF52DE", "#FF9500", "#FF2D55", "#5AC8FA"];

function stockCount(m: Medication): number {
  if (typeof m.stock === "number") return m.stock;
  if (m.stock == null) return 0;
  const match = String(m.stock).match(/(\d+)/);
  return match ? Number(match[0]) : 0;
}

function stockLabel(m: Medication): string {
  if (typeof m.stock === "string" && m.stock.trim()) return m.stock;
  const n = stockCount(m);
  return n ? `${n} таб` : "—";
}

export default function MedicationsPage() {
  const [filter, setFilter] = useState<Filter>("all");
  const { data, isLoading, isError } = useQuery({
    queryKey: ["medications"],
    queryFn: fetchMedications,
    staleTime: 30_000,
  });

  const meds = useMemo(() => {
    const list = data ?? [];
    if (filter === "daily") return list.filter((m) => m.is_daily);
    if (filter === "low") return list.filter((m) => (m.days_left ?? 999) <= 14);
    return list;
  }, [data, filter]);

  const lowStock = (data ?? []).filter((m) => (m.days_left ?? 999) <= 14);

  return (
    <div className="page-shell section-gap">
      <PageHeader title="Лекарства" subtitle="Аптечка" />

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

      {isLoading && (
        <GlassCard padding="lg">
          <p className="text-[#8E8E93]">Загрузка из лекарства/…</p>
        </GlassCard>
      )}
      {isError && (
        <GlassCard padding="lg">
          <p className="text-[#FF3B30]">Не удалось загрузить лекарства</p>
        </GlassCard>
      )}

      {lowStock.length > 0 && (
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
              {lowStock.map((m) => m.name).join(", ")} — проверьте days_left в файлах агента.
            </p>
          </div>
        </GlassCard>
      )}

      {data && (
        <section>
          <SectionHeader title={`${meds.length} препарата`} />
          <div className="space-y-3">
            {meds.map((m, i) => {
              const color = PALETTE[i % PALETTE.length];
              const days = m.days_left ?? 0;
              const night =
                (m.frequency || "").toLowerCase().includes("ночь") ||
                (m.frequency || "").toLowerCase().includes("вечер");
              return (
                <GlassCard
                  key={m.id}
                  padding="md"
                  className="fade-up"
                  style={{ animationDelay: `${i * 50}ms` }}
                >
                  <div className="flex gap-3.5">
                    <div
                      className="w-12 h-12 rounded-[14px] flex items-center justify-center shrink-0 text-white"
                      style={{
                        background: `linear-gradient(145deg, ${color}, ${color}cc)`,
                        boxShadow: `0 8px 20px ${color}33`,
                      }}
                    >
                      {night ? (
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

                      <div className="mt-3">
                        <div className="flex justify-between text-[12px] mb-1.5">
                          <span className="text-[#8E8E93]">Запас</span>
                          <span
                            className={cn(
                              "font-semibold tabular-nums",
                              days <= 14 ? "text-[#FF9500]" : "text-[#1C1C1E]",
                            )}
                          >
                            {stockLabel(m)}
                            {m.days_left != null ? ` · ~${m.days_left} дн` : ""}
                          </span>
                        </div>
                        <div className="h-1.5 rounded-full bg-[#E5E5EA] overflow-hidden">
                          <div
                            className="h-full rounded-full transition-all"
                            style={{
                              width: `${Math.min(100, (days / 60) * 100)}%`,
                              background:
                                days <= 14
                                  ? "linear-gradient(90deg,#FF9500,#FFCC00)"
                                  : `linear-gradient(90deg,${color},${color}aa)`,
                            }}
                          />
                        </div>
                      </div>
                    </div>
                  </div>
                </GlassCard>
              );
            })}
            {meds.length === 0 && (
              <GlassCard padding="lg">
                <p className="text-[14px] text-[#8E8E93] text-center">
                  Нет препаратов в data/лекарства/
                </p>
              </GlassCard>
            )}
          </div>
        </section>
      )}
    </div>
  );
}
