import { useEffect, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Check,
  FlaskConical,
  Sparkles,
  Stethoscope,
  Users,
  FileCheck2,
  FileText,
  ShieldAlert,
  ShieldCheck,
  CalendarCheck2,
  CalendarPlus,
  Download,
} from "lucide-react";
import { GlassCard, PageHeader, SectionHeader, StatusPill } from "../../../components/apple";
import {
  downloadVisitPrompt,
  fetchPipeline,
  requestVisitPrompt,
  setInsuranceWarned,
} from "../../../lib/services";
import type { PipelineStage, VisitItem } from "../../../lib/types";
import { cn } from "../../../lib/utils";

const ICONS: Record<string, React.FC<{ className?: string; style?: React.CSSProperties }>> = {
  stethoscope: Stethoscope,
  users: Users,
  flask: FlaskConical,
  "file-check": FileCheck2,
  sparkles: Sparkles,
};

type PromptFeedback = {
  visitId: string;
  telegram_sent?: boolean;
  pdf_ready?: boolean;
  hint?: string;
  error?: string;
};

/** draft = recommendation (need to book); booked = real appointment */
function isDraft(visit: VisitItem): boolean {
  if (visit.status === "draft") return true;
  if (visit.booking_status === "draft") return true;
  if (visit.status === "booked" || visit.status === "completed" || visit.status === "cancelled") {
    return false;
  }
  const d = visit.effective_date || visit.visit_date || visit.date;
  return !d;
}

function isBookedOpen(visit: VisitItem): boolean {
  if (visit.status === "completed" || visit.status === "cancelled") return false;
  return !isDraft(visit);
}

function isOpenVisit(visit: VisitItem): boolean {
  return visit.status !== "completed" && visit.status !== "cancelled";
}

export default function PipelinePage() {
  const qc = useQueryClient();
  const [focusStage, setFocusStage] = useState<number | null>(null);
  const [promptFb, setPromptFb] = useState<PromptFeedback | null>(null);
  const [promptBusyId, setPromptBusyId] = useState<string | null>(null);
  const [downloadBusyId, setDownloadBusyId] = useState<string | null>(null);
  const stageRefs = useRef<Record<number, HTMLDivElement | null>>({});

  const { data, isLoading, isError } = useQuery({
    queryKey: ["pipeline"],
    queryFn: fetchPipeline,
    staleTime: 20_000,
  });

  const activeStage = focusStage ?? data?.active_stage ?? 1;

  useEffect(() => {
    if (data && focusStage == null) {
      setFocusStage(data.active_stage);
    }
  }, [data, focusStage]);

  const scrollToStage = (stage: number) => {
    setFocusStage(stage);
    const el = stageRefs.current[stage];
    if (el) {
      el.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  };

  const warnMut = useMutation({
    mutationFn: ({ id, v }: { id: string; v: boolean }) =>
      setInsuranceWarned(id, v),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["pipeline"] });
      qc.invalidateQueries({ queryKey: ["timeline"] });
    },
  });

  const promptMut = useMutation({
    mutationFn: (visitId: string) => requestVisitPrompt(visitId),
    onMutate: (visitId) => {
      setPromptBusyId(visitId);
      setPromptFb(null);
    },
    onSuccess: (res, visitId) => {
      setPromptFb({
        visitId,
        telegram_sent: res.telegram_sent,
        pdf_ready: res.pdf_ready ?? true,
        hint: res.hint,
      });
      setPromptBusyId(null);
      qc.invalidateQueries({ queryKey: ["pipeline"] });
    },
    onError: (err, visitId) => {
      setPromptFb({
        visitId,
        error: err instanceof Error ? err.message : String(err),
      });
      setPromptBusyId(null);
    },
  });

  const onDownload = async (id: string) => {
    setDownloadBusyId(id);
    try {
      await downloadVisitPrompt(id);
    } catch (err) {
      setPromptFb({
        visitId: id,
        error: err instanceof Error ? err.message : "Не удалось скачать",
      });
    } finally {
      setDownloadBusyId(null);
    }
  };

  return (
    <div className="page-shell section-gap">
      <PageHeader subtitle="5 этапов" title="Конвейер" />
      <p className="text-[13px] text-[#8E8E93] -mt-2 leading-relaxed">
        Терапевт → спецы → анализы → разбор → сливки. Кликни этап вверху.
        Открытые визиты — <span className="font-medium text-[#8E8E93]">нужно записаться</span>,
        пока нет подтверждённой даты.
      </p>

      {isLoading && (
        <GlassCard padding="lg">
          <p className="text-[#8E8E93]">Загрузка конвейера…</p>
        </GlassCard>
      )}
      {isError && (
        <GlassCard padding="lg">
          <p className="text-[#FF3B30]">Не удалось загрузить /api/pipeline</p>
        </GlassCard>
      )}

      {data && (
        <>
          {/* Sticky stage navigator 1–5 */}
          <div className="sticky top-0 z-20 -mx-1 px-1 pb-1 bg-gradient-to-b from-[#F2F2F7] via-[#F2F2F7] to-transparent">
            <GlassCard padding="md">
              <div className="flex items-center justify-between gap-1">
                {data.stages.map((s, idx) => (
                  <div key={s.stage} className="flex items-center flex-1 min-w-0">
                    <button
                      type="button"
                      onClick={() => scrollToStage(s.stage)}
                      className="pressable shrink-0 rounded-full focus:outline-none focus-visible:ring-2 focus-visible:ring-[#007AFF]/40"
                      aria-label={`Этап ${s.stage}: ${s.title}`}
                      aria-current={activeStage === s.stage ? "step" : undefined}
                    >
                      <StageDot
                        stage={s}
                        active={activeStage === s.stage}
                        selected={focusStage === s.stage}
                      />
                    </button>
                    {idx < data.stages.length - 1 && (
                      <div
                        className={cn(
                          "h-0.5 flex-1 mx-0.5 rounded-full",
                          s.status === "done" ? "bg-[#34C759]" : "bg-black/10",
                        )}
                      />
                    )}
                  </div>
                ))}
              </div>
              <p className="text-[12px] text-[#8E8E93] mt-3 text-center">
                Этап {activeStage}
                {data.stages.find((x) => x.stage === activeStage)?.title
                  ? ` · ${data.stages.find((x) => x.stage === activeStage)?.title}`
                  : ""}
                {" · "}
                записать {data.summary.draft ?? "—"} · ⚠ страх.{" "}
                {data.summary.insurance_pending}
              </p>
            </GlassCard>
          </div>

          <section className="space-y-3">
            {data.stages.map((stage) => (
              <div
                key={stage.stage}
                ref={(el) => {
                  stageRefs.current[stage.stage] = el;
                }}
                id={`pipeline-stage-${stage.stage}`}
              >
                <StageCard
                  stage={stage}
                  isActive={activeStage === stage.stage}
                  promptBusyId={promptBusyId}
                  downloadBusyId={downloadBusyId}
                  promptFb={promptFb}
                  warnPending={warnMut.isPending}
                  onNeedPrompt={(id) => promptMut.mutate(id)}
                  onDownload={onDownload}
                  onToggleInsurance={(id, next) =>
                    warnMut.mutate({ id, v: next })
                  }
                  onFocus={() => setFocusStage(stage.stage)}
                />
              </div>
            ))}
          </section>
        </>
      )}
    </div>
  );
}

function StageDot({
  stage,
  active,
  selected,
}: {
  stage: PipelineStage;
  active: boolean;
  selected?: boolean;
}) {
  const done = stage.status === "done";
  const lit = active || selected;
  return (
    <div
      className={cn(
        "w-9 h-9 rounded-full flex items-center justify-center text-[12px] font-bold shrink-0 transition-transform",
        lit && "scale-110",
        done && "bg-[#34C759] text-white",
        lit && !done && "text-white",
        !lit && !done && "bg-black/5 text-[#8E8E93]",
      )}
      style={
        lit && !done
          ? {
              backgroundColor: stage.color,
              boxShadow: `0 0 0 3px ${stage.color}33`,
            }
          : selected && done
            ? { boxShadow: "0 0 0 3px rgba(52,199,89,0.25)" }
            : undefined
      }
      title={stage.title}
    >
      {done ? <Check className="w-4 h-4" /> : stage.stage}
    </div>
  );
}

function StageCard({
  stage,
  isActive,
  promptBusyId,
  downloadBusyId,
  promptFb,
  warnPending,
  onNeedPrompt,
  onDownload,
  onToggleInsurance,
  onFocus,
}: {
  stage: PipelineStage;
  isActive: boolean;
  promptBusyId: string | null;
  downloadBusyId: string | null;
  promptFb: PromptFeedback | null;
  warnPending: boolean;
  onNeedPrompt: (id: string) => void;
  onDownload: (id: string) => void;
  onToggleInsurance: (id: string, next: boolean) => void;
  onFocus: () => void;
}) {
  const Icon = ICONS[stage.icon] || Stethoscope;
  const booked = stage.visits.filter(isBookedOpen);
  const drafts = stage.visits.filter(isDraft);
  const done = stage.visits.filter(
    (v) => v.status === "completed" || v.status === "cancelled",
  );

  return (
    <GlassCard
      padding="md"
      className={cn(isActive && "ring-2 ring-offset-0")}
      style={isActive ? { boxShadow: `0 0 0 2px ${stage.color}33` } : undefined}
      onClick={onFocus}
    >
      <div className="flex items-start gap-3">
        <div
          className="w-11 h-11 rounded-2xl flex items-center justify-center shrink-0"
          style={{ backgroundColor: `${stage.color}18` }}
        >
          <Icon className="w-5 h-5" style={{ color: stage.color }} />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <p className="text-[16px] font-semibold">
              {stage.stage}. {stage.title}
            </p>
            <StatusPill
              tone={
                stage.status === "done"
                  ? "ok"
                  : stage.status === "active"
                    ? "warn"
                    : "neutral"
              }
            >
              {stage.status === "done"
                ? "готово"
                : stage.status === "active"
                  ? "сейчас"
                  : "пусто"}
            </StatusPill>
          </div>
          <p className="text-[13px] text-[#8E8E93] mt-0.5">{stage.goal}</p>
          <p className="caption mt-1">
            {stage.counts.completed}/{stage.counts.total}
            {typeof stage.counts.draft === "number" && stage.counts.draft > 0 && (
              <> · записать {stage.counts.draft}</>
            )}
            {typeof stage.counts.booked === "number" && stage.counts.booked > 0 && (
              <> · записано {stage.counts.booked}</>
            )}
          </p>
        </div>
      </div>

      {stage.visits.length > 0 && (
        <div className="mt-3 space-y-3 border-t border-black/5 pt-3">
          {drafts.length > 0 && (
            <div className="space-y-2">
              <SectionHeader
                title="Нужно записаться"
                action={
                  <span className="caption inline-flex items-center gap-1 text-[#8E8E93]">
                    <CalendarPlus className="w-3.5 h-3.5" />
                    {drafts.length}
                  </span>
                }
              />
              {drafts.map((v) => (
                <OpenVisitCard
                  key={v.id || `${v.doctor}-draft`}
                  visit={v}
                  mode="draft"
                  accent={stage.color}
                  busy={
                    warnPending ||
                    (!!v.id && (promptBusyId === v.id || downloadBusyId === v.id))
                  }
                  feedback={
                    v.id && promptFb?.visitId === v.id ? promptFb : null
                  }
                  onNeedPrompt={onNeedPrompt}
                  onDownload={onDownload}
                  onToggleInsurance={onToggleInsurance}
                />
              ))}
            </div>
          )}

          {booked.length > 0 && (
            <div className="space-y-2">
              <SectionHeader
                title="Записано"
                action={
                  <span className="caption inline-flex items-center gap-1 text-[#007AFF]">
                    <CalendarCheck2 className="w-3.5 h-3.5" />
                    {booked.length}
                  </span>
                }
              />
              {booked.map((v) => (
                <OpenVisitCard
                  key={v.id || `${v.doctor}-${v.date}`}
                  visit={v}
                  mode="booked"
                  accent={stage.color}
                  busy={
                    warnPending ||
                    (!!v.id && (promptBusyId === v.id || downloadBusyId === v.id))
                  }
                  feedback={
                    v.id && promptFb?.visitId === v.id ? promptFb : null
                  }
                  onNeedPrompt={onNeedPrompt}
                  onDownload={onDownload}
                  onToggleInsurance={onToggleInsurance}
                />
              ))}
            </div>
          )}

          {done.length > 0 && (
            <div className="space-y-2">
              <SectionHeader
                title="Готово"
                action={<span className="caption">{done.length}</span>}
              />
              {done.map((v) => (
                <DoneVisitCard
                  key={v.id || `${v.doctor}-done`}
                  visit={v}
                />
              ))}
            </div>
          )}
        </div>
      )}
    </GlassCard>
  );
}

/** Open visit: draft (need to book) or booked — shared action buttons */
function OpenVisitCard({
  visit,
  mode,
  accent,
  busy,
  feedback,
  onNeedPrompt,
  onDownload,
  onToggleInsurance,
}: {
  visit: VisitItem;
  mode: "draft" | "booked";
  accent: string;
  busy: boolean;
  feedback?: PromptFeedback | null;
  onNeedPrompt: (id: string) => void;
  onDownload: (id: string) => void;
  onToggleInsurance: (id: string, next: boolean) => void;
}) {
  const warned = !!visit.insurance_warned;
  const id = visit.id;
  const promptReady = !!visit.prompt_ready || !!feedback?.pdf_ready;
  const bgs = visit.bgs_application_number;
  const draft = mode === "draft";

  return (
    <div
      className={cn(
        "rounded-2xl px-3 py-2.5",
        draft
          ? "bg-[#8E8E93]/[0.08] border border-dashed border-[#C7C7CC]"
          : "border border-[#007AFF]/25 bg-gradient-to-br from-[#007AFF]/[0.08] to-white",
      )}
      style={!draft ? { boxShadow: `0 0 0 1px ${accent}22` } : undefined}
      onClick={(e) => e.stopPropagation()}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 flex items-start gap-2">
          <div
            className={cn(
              "w-8 h-8 rounded-xl flex items-center justify-center shrink-0 mt-0.5",
              draft ? "bg-black/5" : "bg-[#007AFF]/15",
            )}
          >
            {draft ? (
              <CalendarPlus className="w-4 h-4 text-[#8E8E93]" />
            ) : (
              <CalendarCheck2 className="w-4 h-4 text-[#007AFF]" />
            )}
          </div>
          <div className="min-w-0">
            <p
              className={cn(
                "text-[14px] font-semibold leading-snug",
                draft && "text-[#636366] font-medium",
              )}
            >
              {draft
                ? `Нужно записаться · ${visit.doctor || visit.specialty || visit.title || "врач"}`
                : visit.doctor || visit.title}
            </p>
            {!draft && (
              <p className="text-[13px] text-[#007AFF] font-medium mt-0.5 tabular-nums">
                {visit.effective_date || visit.visit_date || visit.date || "—"}
                {visit.time ? ` · ${visit.time}` : ""}
              </p>
            )}
            {visit.institution && (
              <p className="text-[12px] text-[#8E8E93] mt-0.5">
                {visit.institution}
              </p>
            )}
            {visit.purpose && (
              <p className="text-[12px] text-[#1C1C1E]/80 mt-1 line-clamp-2">
                {visit.purpose}
              </p>
            )}
          </div>
        </div>
        <div className="flex flex-col items-end gap-1 shrink-0">
          <StatusPill tone={draft ? "neutral" : "info"}>
            {draft ? "записать" : "записан"}
          </StatusPill>
          <span
            className={cn(
              "inline-flex items-center gap-0.5 text-[10px] font-medium",
              warned ? "text-[#34C759]" : "text-[#FF9500]",
            )}
          >
            <ShieldAlert className="w-3 h-3" />
            {warned ? "страх. ✓" : "страх. ⚠"}
          </span>
        </div>
      </div>

      {warned && bgs && (
        <div className="mt-2 rounded-xl bg-[#34C759]/10 px-2.5 py-1.5">
          <p className="text-[11px] font-semibold text-[#248A3D] uppercase tracking-wide">
            Заявка Белгосстраха
          </p>
          <p className="text-[14px] font-mono font-semibold text-[#1C1C1E] mt-0.5">
            {bgs}
          </p>
        </div>
      )}

      {id && isOpenVisit(visit) && (
        <div className="mt-2.5 space-y-2">
          <div className="grid grid-cols-2 gap-2">
            <button
              type="button"
              disabled={busy}
              onClick={() => onNeedPrompt(id)}
              className="h-9 rounded-xl text-[12px] font-semibold pressable inline-flex items-center justify-center gap-1.5 disabled:opacity-50 bg-[#007AFF] text-white"
            >
              <FileText className="w-3.5 h-3.5" />
              {busy ? "…" : "Нужен промпт"}
            </button>
            <button
              type="button"
              disabled={busy}
              onClick={() => onToggleInsurance(id, !warned)}
              className={cn(
                "h-9 rounded-xl text-[12px] font-semibold pressable inline-flex items-center justify-center gap-1.5 disabled:opacity-50",
                warned
                  ? "bg-[#34C759]/15 text-[#248A3D]"
                  : "bg-[#FF9500]/15 text-[#C93400]",
              )}
            >
              {warned ? (
                <>
                  <ShieldCheck className="w-3.5 h-3.5" />
                  Страховая
                </>
              ) : (
                <>
                  <ShieldAlert className="w-3.5 h-3.5" />
                  Страховая
                </>
              )}
            </button>
          </div>

          {promptReady && (
            <button
              type="button"
              disabled={busy}
              onClick={() => onDownload(id)}
              className="w-full h-9 rounded-xl text-[12px] font-semibold pressable inline-flex items-center justify-center gap-1.5 disabled:opacity-50 bg-[#1C1C1E] text-white"
            >
              <Download className="w-3.5 h-3.5" />
              Скачать PDF для печати
            </button>
          )}

          {feedback && !feedback.error && (
            <p className="text-[11px] text-center text-[#8E8E93] leading-snug">
              {feedback.telegram_sent
                ? "✓ Промпт отправлен боту в Telegram"
                : feedback.hint || "Пакет промпта готов"}
            </p>
          )}
          {feedback?.error && (
            <p className="text-[11px] text-center text-[#FF3B30]">
              {feedback.error}
            </p>
          )}
        </div>
      )}
    </div>
  );
}

function DoneVisitCard({ visit }: { visit: VisitItem }) {
  return (
    <div className="rounded-2xl px-3 py-2 bg-black/[0.03] opacity-80">
      <div className="flex items-center justify-between gap-2">
        <div className="min-w-0">
          <p className="text-[13px] font-medium truncate">
            {visit.doctor || visit.title}
          </p>
          <p className="text-[11px] text-[#8E8E93]">
            {visit.effective_date || visit.date || "—"}
          </p>
        </div>
        <StatusPill tone={visit.status === "completed" ? "ok" : "danger"}>
          {visit.status === "completed" ? "готово" : "отмена"}
        </StatusPill>
      </div>
    </div>
  );
}
