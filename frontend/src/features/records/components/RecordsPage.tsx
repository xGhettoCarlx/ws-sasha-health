import { useState } from "react";
import {
  Calendar,
  FileText,
  FlaskConical,
  Scan,
  Stethoscope,
} from "lucide-react";
import {
  GlassCard,
  ListGroup,
  ListRow,
  PageHeader,
  SectionHeader,
  StatusPill,
} from "../../../components/apple";
import { mockLabs, mockVisits } from "../../../lib/mock-data";
import { cn } from "../../../lib/utils";

type Tab = "visits" | "labs";

export default function RecordsPage() {
  const [tab, setTab] = useState<Tab>("visits");

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

      {/* Category chips */}
      <div className="flex gap-2 overflow-x-auto scrollbar-hidden -mx-0.5 px-0.5">
        {[
          { icon: Stethoscope, label: "Приёмы", color: "#007AFF" },
          { icon: FlaskConical, label: "Лаборатория", color: "#34C759" },
          { icon: Scan, label: "УЗИ / МРТ", color: "#AF52DE" },
          { icon: FileText, label: "Документы", color: "#FF9500" },
        ].map((c) => (
          <button
            key={c.label}
            type="button"
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
          <SectionHeader title="Визиты" />
          <div className="space-y-3">
            {mockVisits.map((v, i) => (
              <GlassCard
                key={v.id}
                padding="md"
                pressable
                className="fade-up"
                style={{ animationDelay: `${i * 40}ms` }}
              >
                <div className="flex items-start gap-3">
                  <div className="w-11 h-11 rounded-[12px] bg-[#E5F1FF] flex items-center justify-center shrink-0">
                    <Calendar className="w-5 h-5 text-[#007AFF]" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between gap-2">
                      <p className="text-[16px] font-semibold truncate">{v.specialty}</p>
                      <StatusPill
                        tone={
                          v.status === "planned"
                            ? "info"
                            : v.status === "completed"
                              ? "ok"
                              : "neutral"
                        }
                      >
                        {v.status === "planned"
                          ? "план"
                          : v.status === "completed"
                            ? "было"
                            : "отмена"}
                      </StatusPill>
                    </div>
                    <p className="text-[14px] text-[#8E8E93] mt-0.5">{v.doctor}</p>
                    <p className="text-[13px] text-[#AEAEB2] mt-1">
                      {formatDate(v.date)}
                      {v.time ? ` · ${v.time}` : ""} · {v.institution}
                    </p>
                    <p className="text-[14px] text-[#1C1C1E] mt-2 leading-snug">{v.purpose}</p>
                  </div>
                </div>
              </GlassCard>
            ))}
          </div>
        </section>
      ) : (
        <section>
          <SectionHeader title="Результаты" />
          <div className="space-y-3">
            {mockLabs.map((lab, i) => (
              <GlassCard
                key={lab.id}
                padding="md"
                pressable
                className="fade-up"
                style={{ animationDelay: `${i * 40}ms` }}
              >
                <div className="flex items-start justify-between gap-2 mb-2">
                  <div>
                    <p className="text-[16px] font-semibold">{lab.name}</p>
                    <p className="text-[13px] text-[#8E8E93] mt-0.5">
                      {formatDate(lab.date)} · {lab.category}
                    </p>
                  </div>
                  <StatusPill
                    tone={
                      lab.status === "normal"
                        ? "ok"
                        : lab.status === "attention"
                          ? "warn"
                          : "danger"
                    }
                  >
                    {lab.status === "normal"
                      ? "норма"
                      : lab.status === "attention"
                        ? "внимание"
                        : "критично"}
                  </StatusPill>
                </div>
                <p className="text-[14px] text-[#8E8E93] mb-3">{lab.summary}</p>
                <ListGroup className="!shadow-none border border-[rgba(60,60,67,0.08)]">
                  {lab.params.slice(0, 4).map((p) => (
                    <ListRow
                      key={p.name}
                      title={p.name}
                      detail={`${p.value}${p.unit ? ` ${p.unit}` : ""}`}
                      showChevron={false}
                      trailing={
                        p.flag === "high" ? (
                          <span className="text-[#FF3B30] text-[12px] font-bold">↑</span>
                        ) : p.flag === "low" ? (
                          <span className="text-[#007AFF] text-[12px] font-bold">↓</span>
                        ) : (
                          <span className="text-[#34C759] text-[12px]">✓</span>
                        )
                      }
                    />
                  ))}
                </ListGroup>
              </GlassCard>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString("ru-RU", {
    day: "numeric",
    month: "long",
    year: "numeric",
  });
}
