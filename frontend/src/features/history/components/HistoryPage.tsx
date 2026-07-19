import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  PageHeader,
  SectionHeader,
  GlassCard,
  StatusPill,
  BarChart,
} from "../../../components/apple";
import { fetchAnalytics } from "../../../lib/services";

function parseNum(v: string | undefined | null): number | null {
  if (v == null) return null;
  const m = String(v).replace(",", ".").match(/-?\d+(?:\.\d+)?/);
  return m ? Number(m[0]) : null;
}

function isAbnormal(flag?: string | null): boolean {
  if (!flag) return false;
  const f = String(flag);
  if (["✅", "✔", "ok", "normal", "n", "—", "-"].includes(f.toLowerCase()) || f === "✅") {
    return false;
  }
  return ["🔴", "⚠️", "⚠", "↑", "↓", "high", "low", "h", "l", "abnormal"].some(
    (x) => f === x || f.toLowerCase() === x || f.includes(x),
  );
}

/** History / analytics from real lab parameters in data/Анализы */
export default function HistoryPage() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["history-analytics"],
    queryFn: () => fetchAnalytics("Анализы"),
    staleTime: 30_000,
  });

  const altSeries = useMemo(() => {
    const items = (data?.items ?? []).filter((p) =>
      /алт|alt/i.test(p.parameter || ""),
    );
    return items
      .map((p) => {
        const value = parseNum(p.value);
        if (value == null) return null;
        const label = (p.date || "").slice(5) || "—";
        const color = isAbnormal(p.flag) ? "#FF9500" : "#34C759";
        return { label, value, color };
      })
      .filter(Boolean) as { label: string; value: number; color: string }[];
  }, [data]);

  const abnormal = useMemo(
    () => (data?.items ?? []).filter((p) => isAbnormal(p.flag)),
    [data],
  );

  const lastAlt = altSeries.length ? altSeries[altSeries.length - 1] : null;

  return (
    <div className="page-shell section-gap">
      <PageHeader title="Аналитика" subtitle="Тренды из Анализы/" />

      {isLoading && (
        <GlassCard padding="lg">
          <p className="text-[#8E8E93]">Загрузка…</p>
        </GlassCard>
      )}
      {isError && (
        <GlassCard padding="lg">
          <p className="text-[#FF3B30]">Не удалось загрузить /api/history/analytics</p>
        </GlassCard>
      )}

      {lastAlt && (
        <GlassCard padding="lg">
          <div className="flex items-start justify-between mb-4">
            <div>
              <p className="text-[13px] font-semibold text-[#8E8E93]">АлАТ (ALT)</p>
              <p className="metric-value text-[34px] mt-1">
                {lastAlt.value}{" "}
                <span className="text-[15px] font-medium text-[#8E8E93]">Ед/л</span>
              </p>
            </div>
            <StatusPill tone={lastAlt.color === "#34C759" ? "ok" : "warn"}>
              {lastAlt.color === "#34C759" ? "норма" : "вне нормы"}
            </StatusPill>
          </div>
          {altSeries.length > 1 ? (
            <BarChart values={altSeries} height={130} />
          ) : (
            <p className="text-[13px] text-[#8E8E93]">
              Пока одна точка — добавьте повторные анализы для тренда.
            </p>
          )}
          <p className="caption mt-4 leading-relaxed">
            Данные из YAML parameters[] файлов агента (флаги ✅/⚠️/🔴).
          </p>
        </GlassCard>
      )}

      <section>
        <SectionHeader
          title="Вне нормы"
          action={<span className="caption">{abnormal.length}</span>}
        />
        <div className="space-y-3">
          {abnormal.map((p, i) => (
            <GlassCard key={`${p.date}-${p.parameter}-${i}`} padding="md">
              <div className="flex justify-between items-start gap-2">
                <div>
                  <p className="text-[16px] font-semibold">{p.parameter}</p>
                  <p className="text-[13px] text-[#8E8E93] mt-0.5">
                    {p.test_name} · {p.date}
                  </p>
                </div>
                <StatusPill tone="warn">{String(p.flag || "!")}</StatusPill>
              </div>
              <p className="text-[14px] text-[#1C1C1E] mt-2">
                {p.value}
                {p.unit ? ` ${p.unit}` : ""}
                {p.ref_range ? ` (норма ${p.ref_range})` : ""}
              </p>
            </GlassCard>
          ))}
          {data && abnormal.length === 0 && (
            <GlassCard padding="lg">
              <p className="text-[14px] text-[#8E8E93] text-center">
                Отклонений с флагом в файлах нет
              </p>
            </GlassCard>
          )}
        </div>
      </section>
    </div>
  );
}
