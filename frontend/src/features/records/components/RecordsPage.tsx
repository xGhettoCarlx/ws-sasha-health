import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Calendar,
  FlaskConical,
  Scan,
  Stethoscope,
} from "lucide-react";
import {
  GlassCard,
  PageHeader,
  SectionHeader,
  StatusPill,
} from "../../../components/apple";
import {
  fetchAnalytics,
  fetchUpcomingVisits,
  fetchVisits,
} from "../../../lib/services";
import { cn } from "../../../lib/utils";

type Tab = "visits" | "labs";

export default function RecordsPage() {
  const [tab, setTab] = useState<Tab>("visits");

  const visitsQ = useQuery({
    queryKey: ["records-visits"],
    queryFn: async () => {
      const [hist, upcoming] = await Promise.all([
        fetchVisits().catch(() => ({ count: 0, items: [] })),
        fetchUpcomingVisits().catch(() => ({ visits: [] })),
      ]);
      return { hist, upcoming };
    },
    staleTime: 30_000,
  });

  const labsQ = useQuery({
    queryKey: ["records-labs"],
    queryFn: () => fetchAnalytics("Анализы"),
    staleTime: 30_000,
  });

  const visitCards = useMemo(() => {
    type VisitCard = {
      key: string;
      date: string;
      doctor: string;
      purpose: string;
      status: string;
      institution?: string | null;
      source: "schedule" | "history";
    };
    const hist = visitsQ.data?.hist?.items ?? [];
    const upcoming = visitsQ.data?.upcoming?.visits ?? [];
    const fromSchedule: VisitCard[] = upcoming.map((v) => ({
      key: v.id || `${v.doctor}-${v.date}`,
      date: v.date || "—",
      doctor: v.doctor,
      purpose: v.purpose,
      status: v.status,
      institution: v.institution,
      source: "schedule",
    }));
    const fromHist: VisitCard[] = hist.map((v, i) => ({
      key: v._path || `h-${i}`,
      date: v.date || "—",
      doctor: v.doctor,
      purpose: v.purpose || v.complaint || "",
      status: v.status || "completed",
      institution: v.institution,
      source: "history",
    }));
    // prefer schedule first, then history
    const seen = new Set<string>();
    const out: VisitCard[] = [];
    for (const row of [...fromSchedule, ...fromHist]) {
      const sig = `${row.doctor}|${row.date}`;
      if (seen.has(sig)) continue;
      seen.add(sig);
      out.push(row);
    }
    return out;
  }, [visitsQ.data]);

  const labGroups = useMemo(() => {
    const items = labsQ.data?.items ?? [];
    const byTest = new Map<string, { date: string; flags: number; params: number; sample: string }>();
    for (const p of items) {
      const key = `${p.date}|${p.test_name}`;
      const cur = byTest.get(key) || {
        date: p.date,
        flags: 0,
        params: 0,
        sample: p.test_name,
      };
      cur.params += 1;
      const f = (p.flag || "").toString();
      if (f && !["✅", "ok", "normal", "n", "—", "-"].includes(f.toLowerCase()) && f !== "✅") {
        if (["🔴", "⚠️", "⚠", "high", "low", "↑", "↓", "h", "l"].some((x) => f.includes(x) || f.toLowerCase() === x)) {
          cur.flags += 1;
        }
      }
      byTest.set(key, cur);
    }
    return Array.from(byTest.values()).sort((a, b) => (a.date < b.date ? 1 : -1));
  }, [labsQ.data]);

  return (
    <div className="page-shell section-gap">
      <PageHeader title="Медкарта" subtitle="История" />

      <div className="glass rounded-[12px] p-1 flex gap-1">
        {(
          [
            ["visits", "Визиты"],
            ["labs", "Анализы"],
          ] as const
        ).map(([key, label]) => (
          <button
            key={key}
            type="button"
            onClick={() => setTab(key)}
            className={cn(
              "flex-1 h-8 rounded-[9px] text-[13px] font-semibold transition-all",
              tab === key
                ? "bg-white text-[#1C1C1E] shadow-sm"
                : "text-[#8E8E93]",
            )}
          >
            {label}
          </button>
        ))}
      </div>

      <div className="flex gap-2 overflow-x-auto scrollbar-hidden -mx-0.5 px-0.5">
        {[
          { icon: Stethoscope, label: "Приёмы", color: "#007AFF" },
          { icon: FlaskConical, label: "Лаборатория", color: "#34C759" },
          { icon: Scan, label: "УЗИ / МРТ", color: "#AF52DE" },
        ].map((c) => (
          <button
            key={c.label}
            type="button"
            onClick={() => setTab(c.label === "Лаборатория" ? "labs" : "visits")}
            className="shrink-0 flex items-center gap-2 pl-2.5 pr-3.5 py-2 rounded-full bg-white shadow-[var(--shadow-soft)] pressable"
          >
            <span
              className="w-7 h-7 rounded-full flex items-center justify-center text-white"
              style={{ background: c.color }}
            >
              <c.icon className="w-3.5 h-3.5" strokeWidth={2.2} />
            </span>
            <span className="text-[13px] font-semibold">{c.label}</span>
          </button>
        ))}
      </div>

      {tab === "visits" ? (
        <section>
          <SectionHeader
            title="Визиты"
            action={<span className="caption">{visitCards.length}</span>}
          />
          {visitsQ.isLoading && (
            <p className="text-[14px] text-[#8E8E93]">Загрузка…</p>
          )}
          {visitsQ.isError && (
            <p className="text-[14px] text-[#FF3B30]">Ошибка загрузки визитов</p>
          )}
          <div className="space-y-3">
            {visitCards.map((v, i) => (
              <GlassCard
                key={v.key}
                padding="md"
                className="fade-up"
                style={{ animationDelay: `${i * 40}ms` }}
              >
                <div className="flex items-start gap-3">
                  <div className="w-11 h-11 rounded-[12px] bg-[#E5F1FF] flex items-center justify-center shrink-0">
                    <Calendar className="w-5 h-5 text-[#007AFF]" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between gap-2">
                      <p className="text-[16px] font-semibold truncate">{v.doctor}</p>
                      <StatusPill
                        tone={
                          v.status === "completed"
                            ? "ok"
                            : v.status === "cancelled"
                              ? "neutral"
                              : "info"
                        }
                      >
                        {v.status || "—"}
                      </StatusPill>
                    </div>
                    <p className="text-[13px] text-[#8E8E93] mt-0.5">
                      {v.date}
                      {v.institution ? ` · ${v.institution}` : ""}
                    </p>
                    {v.purpose && (
                      <p className="text-[14px] text-[#1C1C1E] mt-2 leading-snug">
                        {v.purpose}
                      </p>
                    )}
                  </div>
                </div>
              </GlassCard>
            ))}
            {!visitsQ.isLoading && visitCards.length === 0 && (
              <GlassCard padding="lg">
                <p className="text-[14px] text-[#8E8E93] text-center">
                  Нет визитов в schedule/ и Терапевт/
                </p>
              </GlassCard>
            )}
          </div>
        </section>
      ) : (
        <section>
          <SectionHeader
            title="Анализы"
            action={<span className="caption">{labGroups.length}</span>}
          />
          {labsQ.isLoading && (
            <p className="text-[14px] text-[#8E8E93]">Загрузка…</p>
          )}
          {labsQ.isError && (
            <p className="text-[14px] text-[#FF3B30]">Ошибка загрузки анализов</p>
          )}
          <div className="space-y-3">
            {labGroups.map((lab, i) => (
              <GlassCard key={`${lab.date}-${lab.sample}-${i}`} padding="md">
                <div className="flex justify-between items-start gap-2">
                  <div>
                    <p className="text-[16px] font-semibold">{lab.sample}</p>
                    <p className="text-[13px] text-[#8E8E93] mt-0.5">{lab.date}</p>
                  </div>
                  <StatusPill tone={lab.flags > 0 ? "warn" : "ok"}>
                    {lab.flags > 0 ? `${lab.flags} вне нормы` : "норма"}
                  </StatusPill>
                </div>
                <p className="text-[14px] text-[#8E8E93] mt-2">
                  {lab.params} показателей из файлов Анализы/
                </p>
              </GlassCard>
            ))}
            {!labsQ.isLoading && labGroups.length === 0 && (
              <GlassCard padding="lg">
                <p className="text-[14px] text-[#8E8E93] text-center">
                  Нет анализов в data/Анализы/
                </p>
              </GlassCard>
            )}
          </div>
        </section>
      )}
    </div>
  );
}
