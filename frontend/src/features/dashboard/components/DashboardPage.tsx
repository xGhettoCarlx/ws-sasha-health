import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ChevronDown, ChevronRight, Shield } from "lucide-react";
import {
  GlassCard,
  PageHeader,
  SectionHeader,
  StatusPill,
  BpChart,
  MiniSparkline,
} from "../../../components/apple";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "../../../components/ui/dialog";
import {
  fetchComplaints,
  fetchOverview,
  fetchVitals,
  postVital,
  type ComplaintItem,
} from "../../../lib/navigator-api";
import { cn } from "../../../lib/utils";

type VitalItem = {
  id?: string;
  date?: string;
  bp?: string | null;
  weight_kg?: number | null;
  when?: string | null;
};

type Diagnosis = {
  name?: string;
  status?: string;
  date?: string;
  source?: string | null;
  content?: string | null;
  doctor?: string | null;
  trust_tier?: string;
};

function parseBp(bp?: string | null): { sys: number; dia: number } | null {
  if (!bp) return null;
  const m = String(bp).match(/(\d{2,3})\s*\/\s*(\d{2,3})/);
  if (!m) return null;
  return { sys: Number(m[1]), dia: Number(m[2]) };
}

/** Extract doctor/clinic hint from diagnosis source free-text */
function parseDiagnosisMeta(d: Diagnosis): {
  doctor: string;
  basis: string;
  date: string;
} {
  const source = (d.source || d.content || "").trim();
  const date = d.date || "—";
  // "осмотр Кабаев 10.06.2026" / "Кабаев 10.06.2026" / "УЗИ …"
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
    // fall back to leading human name before + or comma
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

export function DashboardPage() {
  const qc = useQueryClient();
  const { data, isLoading, isError } = useQuery({
    queryKey: ["overview"],
    queryFn: fetchOverview,
    staleTime: 30_000,
  });

  const { data: vitalsData } = useQuery({
    queryKey: ["vitals"],
    queryFn: () => fetchVitals(60),
    staleTime: 30_000,
  });

  const { data: complaintsData } = useQuery({
    queryKey: ["complaints", false],
    queryFn: () => fetchComplaints(false),
    staleTime: 30_000,
  });

  const [expanded, setExpanded] = useState<"bp" | "weight" | null>(null);
  const [sys, setSys] = useState("");
  const [dia, setDia] = useState("");
  const [weight, setWeight] = useState("");
  const [when, setWhen] = useState<"morning" | "evening" | "other">("morning");
  const [msg, setMsg] = useState<string | null>(null);
  const [diagnosisOpen, setDiagnosisOpen] = useState<Diagnosis | null>(null);

  const saveVital = useMutation({
    mutationFn: postVital,
    onSuccess: () => {
      setMsg("Сохранено");
      setSys("");
      setDia("");
      setWeight("");
      qc.invalidateQueries({ queryKey: ["overview"] });
      qc.invalidateQueries({ queryKey: ["vitals"] });
      setTimeout(() => setMsg(null), 2000);
    },
    onError: (e: Error) => setMsg(e.message || "Ошибка сохранения"),
  });

  const greeting = useMemo(() => {
    const h = new Date().getHours();
    if (h < 12) return "Доброе утро";
    if (h < 18) return "Добрый день";
    return "Добрый вечер";
  }, []);

  const items = useMemo(
    () => (vitalsData?.items || []) as VitalItem[],
    [vitalsData],
  );

  const bpSeries = useMemo(() => {
    return items
      .map((it) => {
        const p = parseBp(it.bp);
        if (!p) return null;
        const day = (it.date || "").slice(5) || "—";
        return { day, sys: p.sys, dia: p.dia, full: it.date || "" };
      })
      .filter(Boolean)
      .reverse() as { day: string; sys: number; dia: number; full: string }[];
  }, [items]);

  const weightSeries = useMemo(() => {
    return items
      .filter((it) => it.weight_kg != null && !Number.isNaN(Number(it.weight_kg)))
      .map((it) => ({
        day: (it.date || "").slice(5) || "—",
        value: Number(it.weight_kg),
        full: it.date || "",
      }))
      .reverse();
  }, [items]);

  const weightSpark = weightSeries.map((w) => w.value);

  const openComplaints: ComplaintItem[] = complaintsData?.items || [];

  const diagnoses = useMemo(() => {
    const raw = (data?.patient?.diagnoses || []) as Diagnosis[];
    // Prefer active (🔴/🟡) first
    return [...raw].sort((a, b) => {
      const rank = (s?: string) =>
        s?.includes("🔴") ? 0 : s?.includes("🟡") ? 1 : 2;
      return rank(a.status) - rank(b.status);
    });
  }, [data]);

  const saveBp = () => {
    if (!sys || !dia) {
      setMsg("Введите систолу и диастолу");
      return;
    }
    saveVital.mutate({ bp: `${sys}/${dia}`, when });
  };

  const saveWeight = () => {
    if (!weight) {
      setMsg("Введите вес");
      return;
    }
    saveVital.mutate({ weight_kg: Number(weight.replace(",", ".")), when });
  };

  if (isLoading) {
    return (
      <div className="page-shell section-gap">
        <PageHeader subtitle={greeting} title="…" />
        <GlassCard padding="lg">
          <p className="text-[15px] text-[#8E8E93]">Загрузка реальных данных…</p>
        </GlassCard>
      </div>
    );
  }

  if (isError || !data) {
    return (
      <div className="page-shell section-gap">
        <PageHeader subtitle={greeting} title="Медик" />
        <GlassCard padding="lg">
          <p className="text-[15px] text-[#FF3B30] font-medium">
            Не удалось загрузить данные API
          </p>
          <p className="text-[13px] text-[#8E8E93] mt-2">
            Проверьте бэкенд на 127.0.0.1:8000 (launchd com.sasha-health.backend).
          </p>
        </GlassCard>
      </div>
    );
  }

  return (
    <div className="page-shell section-gap">
      <PageHeader
        subtitle={greeting}
        title={data.patient.short_name || "Саша"}
      />

      <p className="text-[13px] text-[#8E8E93] -mt-2 leading-relaxed">
        {data.patient.summary_line || "Реальные файлы агента · без лишних экранов"}
      </p>

      {/* Interactive metrics */}
      <section>
        <SectionHeader
          title="Контроль"
          action={<span className="caption">нажми · график</span>}
        />
        <div className="grid grid-cols-2 gap-3">
          <MetricTile
            label="Давление"
            value={data.vitals.last_bp?.bp || "—"}
            unit="мм рт.ст."
            accent="#FF2D55"
            meta={
              data.vitals.last_bp?.date
                ? `замер ${data.vitals.last_bp.date}`
                : "нет записей"
            }
            open={expanded === "bp"}
            onClick={() => setExpanded((e) => (e === "bp" ? null : "bp"))}
          />
          <MetricTile
            label="Вес"
            value={
              data.vitals.last_weight?.weight_kg != null
                ? String(data.vitals.last_weight.weight_kg)
                : "—"
            }
            unit="кг"
            accent="#34C759"
            meta={
              data.vitals.last_weight?.date
                ? `замер ${data.vitals.last_weight.date}`
                : data.vitals.last_weight?.source || "из карточки"
            }
            open={expanded === "weight"}
            onClick={() =>
              setExpanded((e) => (e === "weight" ? null : "weight"))
            }
          />
        </div>

        {expanded === "bp" && (
          <GlassCard padding="lg" className="mt-3">
            <div className="flex items-center justify-between mb-2">
              <p className="text-[15px] font-semibold">Динамика АД</p>
              <span className="caption">{bpSeries.length} точек</span>
            </div>
            {bpSeries.length >= 1 ? (
              <BpChart series={bpSeries.map(({ day, sys: s, dia: d }) => ({ day, sys: s, dia: d }))} />
            ) : (
              <p className="text-[13px] text-[#8E8E93]">
                Пока нет истории — добавьте замер ниже.
              </p>
            )}
            <p className="text-[12px] font-semibold mt-4 mb-2">Быстрый ввод</p>
            <WhenPills when={when} setWhen={setWhen} />
            <div className="grid grid-cols-2 gap-2 mb-2">
              <input
                inputMode="numeric"
                placeholder="Сис"
                value={sys}
                onChange={(e) =>
                  setSys(e.target.value.replace(/\D/g, "").slice(0, 3))
                }
                className="h-11 rounded-2xl bg-black/[0.04] px-3 text-[16px] text-center outline-none focus:ring-2 focus:ring-[#FF2D55]/40"
              />
              <input
                inputMode="numeric"
                placeholder="Диа"
                value={dia}
                onChange={(e) =>
                  setDia(e.target.value.replace(/\D/g, "").slice(0, 3))
                }
                className="h-11 rounded-2xl bg-black/[0.04] px-3 text-[16px] text-center outline-none focus:ring-2 focus:ring-[#FF2D55]/40"
              />
            </div>
            <button
              type="button"
              onClick={saveBp}
              disabled={saveVital.isPending}
              className="w-full h-11 rounded-2xl bg-[#FF2D55] text-white font-semibold text-[15px] pressable disabled:opacity-50"
            >
              {saveVital.isPending ? "Сохраняю…" : "Сохранить АД"}
            </button>
            {msg && (
              <p className="text-[13px] text-center mt-2 text-[#8E8E93]">{msg}</p>
            )}
          </GlassCard>
        )}

        {expanded === "weight" && (
          <GlassCard padding="lg" className="mt-3">
            <div className="flex items-center justify-between mb-2">
              <p className="text-[15px] font-semibold">Динамика веса</p>
              <span className="caption">{weightSeries.length} точек</span>
            </div>
            {weightSpark.length >= 1 ? (
              <>
                <MiniSparkline data={weightSpark} color="#34C759" height={56} />
                <div className="flex justify-between mt-1">
                  {weightSeries.slice(-4).map((w) => (
                    <span key={w.full + w.value} className="text-[10px] text-[#8E8E93]">
                      {w.day}: {w.value}
                    </span>
                  ))}
                </div>
              </>
            ) : (
              <p className="text-[13px] text-[#8E8E93]">
                Пока нет истории — добавьте вес ниже.
              </p>
            )}
            <p className="text-[12px] font-semibold mt-4 mb-2">Быстрый ввод</p>
            <WhenPills when={when} setWhen={setWhen} />
            <input
              inputMode="decimal"
              placeholder="кг"
              value={weight}
              onChange={(e) => setWeight(e.target.value)}
              className="w-full h-11 rounded-2xl bg-black/[0.04] px-3 text-[16px] text-center outline-none focus:ring-2 focus:ring-[#34C759]/40 mb-2"
            />
            <button
              type="button"
              onClick={saveWeight}
              disabled={saveVital.isPending}
              className="w-full h-11 rounded-2xl bg-[#34C759] text-white font-semibold text-[15px] pressable disabled:opacity-50"
            >
              {saveVital.isPending ? "Сохраняю…" : "Сохранить вес"}
            </button>
            {msg && (
              <p className="text-[13px] text-center mt-2 text-[#8E8E93]">{msg}</p>
            )}
          </GlassCard>
        )}
      </section>

      {/* Current complaints — replaces hub links */}
      <section>
        <SectionHeader
          title="Текущие жалобы"
          action={
            <span className="caption">
              {openComplaints.length || data.complaints_open || 0}
            </span>
          }
        />
        {openComplaints.length === 0 ? (
          <GlassCard padding="md">
            <p className="text-[14px] text-[#8E8E93]">
              Открытых жалоб нет — копилка пуста.
            </p>
          </GlassCard>
        ) : (
          <div className="space-y-2">
            {openComplaints.map((c) => (
              <GlassCard key={c.id} padding="md">
                <div className="flex items-start justify-between gap-2">
                  <p className="text-[15px] font-medium leading-snug">{c.text}</p>
                  <StatusPill
                    tone={
                      c.severity >= 7 ? "danger" : c.severity >= 4 ? "warn" : "info"
                    }
                  >
                    {c.severity}/10
                  </StatusPill>
                </div>
                <p className="text-[12px] text-[#8E8E93] mt-1.5">
                  {c.date}
                  {c.specialty_hint ? ` · ${c.specialty_hint}` : ""}
                  {c.tags?.length ? ` · ${c.tags.join(", ")}` : ""}
                </p>
              </GlassCard>
            ))}
          </div>
        )}
      </section>

      {/* Insurance strip → tab Страховка */}
      {data.insurance && (
        <section>
          <SectionHeader title="Страховка" />
          <Link to="/insurance">
            <GlassCard padding="md" pressable className="flex items-center gap-3">
              <div className="w-11 h-11 rounded-2xl bg-[#34C759]/15 flex items-center justify-center">
                <Shield className="w-5 h-5 text-[#34C759]" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-[15px] font-semibold truncate">
                  {(data.insurance as { policy?: string }).policy || "ДМС"}
                </p>
                <p className="text-[13px] text-[#8E8E93]">
                  остаток{" "}
                  {Number(
                    (data.insurance as { remaining?: number }).remaining ?? 0,
                  ).toLocaleString("ru-RU")}{" "}
                  BYN
                  {(data.insurance as { expiry?: string }).expiry
                    ? ` · до ${(data.insurance as { expiry?: string }).expiry}`
                    : ""}
                </p>
              </div>
              <ChevronRight className="w-5 h-5 text-[#C7C7CC]" />
            </GlassCard>
          </Link>
        </section>
      )}

      {/* Clickable diagnoses */}
      {diagnoses.length > 0 && (
        <section>
          <SectionHeader
            title="Активные"
            action={<span className="caption">тап · анамнез</span>}
          />
          <GlassCard padding="none">
            {diagnoses.slice(0, 8).map((d, i) => {
              const meta = parseDiagnosisMeta(d);
              return (
                <div key={`${d.name}-${d.date}-${i}`}>
                  {i > 0 && <div className="hairline ml-4" />}
                  <button
                    type="button"
                    onClick={() => setDiagnosisOpen(d)}
                    className="w-full text-left px-4 py-3 flex items-start gap-3 pressable"
                  >
                    <span className="text-[16px] leading-none mt-0.5">
                      {d.status || "•"}
                    </span>
                    <div className="min-w-0 flex-1">
                      <p className="text-[15px] font-medium leading-snug">
                        {d.name}
                      </p>
                      <p className="text-[12px] text-[#8E8E93] mt-0.5">
                        {meta.date}
                        {meta.doctor !== "не указан" ? ` · ${meta.doctor}` : ""}
                      </p>
                    </div>
                    <ChevronDown className="w-4 h-4 text-[#C7C7CC] mt-1 shrink-0" />
                  </button>
                </div>
              );
            })}
          </GlassCard>
        </section>
      )}

      <Dialog
        open={!!diagnosisOpen}
        onOpenChange={(o) => !o && setDiagnosisOpen(null)}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="text-[18px] leading-snug pr-6">
              {diagnosisOpen?.name || "Диагноз"}
            </DialogTitle>
          </DialogHeader>
          {diagnosisOpen && (
            <div className="space-y-3 mt-1">
              <MetaRow label="Статус" value={diagnosisOpen.status || "—"} />
              <MetaRow
                label="Дата фиксации"
                value={parseDiagnosisMeta(diagnosisOpen).date}
              />
              <MetaRow
                label="Кто / откуда"
                value={parseDiagnosisMeta(diagnosisOpen).doctor}
              />
              <div>
                <p className="text-[12px] font-semibold text-[#8E8E93] uppercase tracking-wide mb-1">
                  Основание / комментарий
                </p>
                <p className="text-[14px] leading-relaxed text-[#1C1C1E]">
                  {parseDiagnosisMeta(diagnosisOpen).basis}
                </p>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>

      <p className="text-[11px] text-[#AEAEB2] text-center px-4 pb-2 leading-relaxed">
        {data.disclaimer}
      </p>
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

function WhenPills({
  when,
  setWhen,
}: {
  when: "morning" | "evening" | "other";
  setWhen: (w: "morning" | "evening" | "other") => void;
}) {
  return (
    <div className="flex gap-2 mb-3">
      {(["morning", "evening", "other"] as const).map((w) => (
        <button
          key={w}
          type="button"
          onClick={() => setWhen(w)}
          className={cn(
            "flex-1 h-9 rounded-full text-[13px] font-medium pressable",
            when === w ? "bg-[#007AFF] text-white" : "bg-black/5 text-[#1C1C1E]",
          )}
        >
          {w === "morning" ? "Утро" : w === "evening" ? "Вечер" : "Другое"}
        </button>
      ))}
    </div>
  );
}

function MetricTile({
  label,
  value,
  unit,
  accent,
  meta,
  open,
  onClick,
}: {
  label: string;
  value: string;
  unit: string;
  accent: string;
  meta: string;
  open?: boolean;
  onClick?: () => void;
}) {
  return (
    <button type="button" onClick={onClick} className="text-left w-full pressable">
      <GlassCard
        padding="md"
        className={cn(open && "ring-2 ring-offset-0")}
        style={open ? { boxShadow: `0 0 0 2px ${accent}44` } : undefined}
      >
        <div className="flex items-center gap-2 mb-2">
          <span className="w-2 h-2 rounded-full" style={{ background: accent }} />
          <p className="text-[12px] font-semibold text-[#8E8E93] uppercase tracking-wide">
            {label}
          </p>
          <ChevronDown
            className={cn(
              "w-3.5 h-3.5 text-[#C7C7CC] ml-auto transition-transform",
              open && "rotate-180",
            )}
          />
        </div>
        <p className="text-[28px] font-semibold tracking-tight leading-none text-[#1C1C1E]">
          {value}
        </p>
        <p className="text-[12px] text-[#8E8E93] mt-1">{unit}</p>
        <p className="text-[11px] text-[#AEAEB2] mt-2">{meta}</p>
      </GlassCard>
    </button>
  );
}
