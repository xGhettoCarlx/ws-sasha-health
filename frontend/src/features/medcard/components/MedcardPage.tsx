/**
 * Моя медкарта — full diagnosis list (off Dashboard sheet).
 * DoD HEALTH-APP-UX-REFINEMENT-V2
 */
import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { ChevronLeft, Stethoscope } from "lucide-react";
import {
  GlassCard,
  PageHeader,
  SectionHeader,
  StatusPill,
} from "../../../components/apple";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "../../../components/ui/dialog";
import { fetchOverview } from "../../../lib/navigator-api";

type Diagnosis = {
  name?: string;
  status?: string;
  date?: string;
  source?: string | null;
  content?: string | null;
  doctor?: string | null;
  trust_tier?: string;
};

function parseDiagnosisMeta(d: Diagnosis): {
  doctor: string;
  basis: string;
  date: string;
} {
  const source = (d.source || d.content || "").trim();
  const date = d.date || "—";
  let doctor = d.doctor || "";
  if (!doctor && source) {
    const m =
      source.match(
        /(?:осмотр|врач|терапевт|кардиолог|гастро|лор|проктолог|офтальмолог)\s+([А-ЯЁA-Z][а-яёa-zA-Z.\-]+(?:\s+[А-ЯЁA-Z]\.?)?)/i,
      ) ||
      source.match(
        /([А-ЯЁ][а-яё]+(?:\s+[А-ЯЁ]\.){0,2})\s+\d{1,2}[./]\d{1,2}/,
      );
    if (m?.[1]) doctor = m[1].trim();
  }
  if (!doctor && source) {
    const headPart = source.split(/[+|,]/)[0];
    const head = (headPart ?? "").trim();
    if (head && /[А-ЯЁа-яё]/.test(head) && head.length < 60) doctor = head;
  }
  return {
    doctor: doctor || "не указан",
    basis: source || "нет комментария в карточке",
    date,
  };
}

function statusTone(status?: string): "danger" | "warn" | "ok" | "neutral" {
  if (status?.includes("🔴")) return "danger";
  if (status?.includes("🟡")) return "warn";
  if (status?.includes("🟢")) return "ok";
  return "neutral";
}

export default function MedcardPage() {
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["overview"],
    queryFn: fetchOverview,
    staleTime: 30_000,
  });

  const [open, setOpen] = useState<Diagnosis | null>(null);

  const diagnoses = useMemo(() => {
    const raw = (data?.patient?.diagnoses || []) as Diagnosis[];
    return [...raw].sort((a, b) => {
      const rank = (s?: string) =>
        s?.includes("🔴") ? 0 : s?.includes("🟡") ? 1 : 2;
      return rank(a.status) - rank(b.status);
    });
  }, [data]);

  return (
    <div className="page-shell section-gap">
      <div className="flex items-center gap-2 -mb-1">
        <Link
          to="/dashboard"
          className="inline-flex items-center gap-0.5 text-[14px] text-[#007AFF] font-medium pressable"
        >
          <ChevronLeft className="w-4 h-4" />
          Обзор
        </Link>
      </div>
      <PageHeader subtitle="Диагнозы и анамнез" title="Моя медкарта" />

      {isLoading && (
        <GlassCard padding="lg">
          <p className="text-[#8E8E93]">Загрузка…</p>
        </GlassCard>
      )}
      {isError && (
        <GlassCard padding="lg">
          <p className="text-[#FF3B30]">Не удалось загрузить карточку</p>
          <button
            type="button"
            onClick={() => refetch()}
            className="mt-2 text-[14px] text-[#007AFF] font-medium"
          >
            Повторить
          </button>
        </GlassCard>
      )}

      {data && diagnoses.length === 0 && (
        <GlassCard padding="lg" className="text-center">
          <Stethoscope className="w-8 h-8 text-[#C7C7CC] mx-auto mb-2" />
          <p className="text-[15px] font-medium">Диагнозов пока нет</p>
          <p className="text-[13px] text-[#8E8E93] mt-1">
            Они появятся после разбора визитов
          </p>
        </GlassCard>
      )}

      {diagnoses.length > 0 && (
        <section>
          <SectionHeader
            title="Диагнозы"
            action={<span className="caption">{diagnoses.length}</span>}
          />
          <div className="space-y-2">
            {diagnoses.map((d, i) => {
              const meta = parseDiagnosisMeta(d);
              return (
                <button
                  key={`${d.name}-${d.date}-${i}`}
                  type="button"
                  onClick={() => setOpen(d)}
                  className="w-full text-left pressable"
                >
                  <GlassCard padding="md">
                    <div className="flex items-start gap-3">
                      <span className="text-[18px] leading-none mt-0.5">
                        {d.status || "•"}
                      </span>
                      <div className="min-w-0 flex-1">
                        <p className="text-[15px] font-semibold leading-snug">
                          {d.name}
                        </p>
                        <p className="text-[12px] text-[#8E8E93] mt-0.5">
                          {meta.date}
                          {meta.doctor !== "не указан"
                            ? ` · ${meta.doctor}`
                            : ""}
                        </p>
                      </div>
                      <StatusPill tone={statusTone(d.status)}>
                        {d.status?.includes("🔴")
                          ? "активный"
                          : d.status?.includes("🟡")
                            ? "контроль"
                            : "фон"}
                      </StatusPill>
                    </div>
                  </GlassCard>
                </button>
              );
            })}
          </div>
        </section>
      )}

      <Dialog open={!!open} onOpenChange={(o) => !o && setOpen(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="text-[18px] leading-snug pr-6">
              {open?.name || "Диагноз"}
            </DialogTitle>
          </DialogHeader>
          {open && (
            <div className="space-y-3 mt-1">
              <MetaRow label="Статус" value={open.status || "—"} />
              <MetaRow
                label="Дата фиксации"
                value={parseDiagnosisMeta(open).date}
              />
              <MetaRow
                label="Кто / откуда"
                value={parseDiagnosisMeta(open).doctor}
              />
              <div>
                <p className="text-[12px] font-semibold text-[#8E8E93] uppercase tracking-wide mb-1">
                  Основание / комментарий
                </p>
                <p className="text-[14px] leading-relaxed text-[#1C1C1E]">
                  {parseDiagnosisMeta(open).basis}
                </p>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}

function MetaRow({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-[12px] font-semibold text-[#8E8E93] uppercase tracking-wide">
        {label}
      </p>
      <p className="text-[15px] text-[#1C1C1E] mt-0.5">{value}</p>
    </div>
  );
}
