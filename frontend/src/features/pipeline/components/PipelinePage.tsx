import { useState } from "react";
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
} from "lucide-react";
import { GlassCard, PageHeader, SectionHeader, StatusPill } from "../../../components/apple";
import {
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
  // legacy planned/pending without date → treat as draft
  const d = visit.effective_date || visit.visit_date || visit.date;
  return !d;
}

function isBookedOpen(visit: VisitItem): boolean {
  if (visit.status === "completed" || visit.status === "cancelled") return false;
  return !isDraft(visit);
}

export default function PipelinePage() {
  const qc = useQueryClient();
  const [promptFb, setPromptFb] = useState<PromptFeedback | null>(null);
  const [promptBusyId, setPromptBusyId] = useState<string | null>(null);

  const { data, isLoading, isError } = useQuery({
    queryKey: ["pipeline"],
    queryFn: fetchPipeline,
    staleTime: 20_000,
  });

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
        hint: res.hint,
      });
      setPromptBusyId(null);
    },
    onError: (err, visitId) => {
      setPromptFb({
        visitId,
        error: err instanceof Error ? err.message : String(err),
      });
      setPromptBusyId(null);
    },
  });

  return (
    <div className="page-shell section-gap">
      <PageHeader subtitle="5 этапов" title="Конвейер" />
      <p className="text-[13px] text-[#8E8E93] -mt-2 leading-relaxed">
        Терапевт → спецы → анализы → разбор → сливки.{" "}
        <span className="text-[#007AFF] font-medium">Записано</span> vs{" "}
        <span className="text-[#8E8E93] font-medium">нужно записаться</span>.
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
          <GlassCard padding="md">
            <div className="flex items-center justify-between gap-1">
              {data.stages.map((s, idx) => (
                <div key={s.stage} className="flex items-center flex-1 min-w-0">
                  <StageDot stage={s} active={data.active_stage === s.stage} />
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
              Этап {data.active_stage} · записано {data.summary.booked ?? "—"} ·
              записать {data.summary.draft ?? "—"} · ⚠ страх.{" "}
              {data.summary.insurance_pending}
            </p>
          </GlassCard>

          <section className="space-y-3">
            {data.stages.map((stage) => (
              <StageCard
                key={stage.stage}
                stage={stage}
                isActive={data.active_stage === stage.stage}
                promptBusyId={promptBusyId}
                promptFb={promptFb}
                warnPending={warnMut.isPending}
                onNeedPrompt={(id) => promptMut.mutate(id)}
                onToggleInsurance={(id, next) =>
                  warnMut.mutate({ id, v: next })
                }
              />
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
}: {
  stage: PipelineStage;
  active: boolean;
}) {
  const done = stage.status === "done";
  return (
    <div
      className={cn(
        "w-8 h-8 rounded-full flex items-center justify-center text-[11px] font-bold shrink-0",
        done && "bg-[#34C759] text-white",
        active && !done && "text-white",
        !active && !done && "bg-black/5 text-[#8E8E93]",
      )}
      style={active && !done ? { backgroundColor: stage.color } : undefined}
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
  promptFb,
  warnPending,
  onNeedPrompt,
  onToggleInsurance,
}: {
  stage: PipelineStage;
  isActive: boolean;
  promptBusyId: string | null;
  promptFb: PromptFeedback | null;
  warnPending: boolean;
  onNeedPrompt: (id: string) => void;
  onToggleInsurance: (id: string, next: boolean) => void;
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
            {typeof stage.counts.booked === "number" && (
              <> · записано {stage.counts.booked}</>
            )}
            {typeof stage.counts.draft === "number" && stage.counts.draft > 0 && (
              <> · записать {stage.counts.draft}</>
            )}
          </p>
        </div>
      </div>

      {stage.visits.length > 0 && (
        <div className="mt-3 space-y-3 border-t border-black/5 pt-3">
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
                <BookedVisitCard
                  key={v.id || `${v.doctor}-${v.date}`}
                  visit={v}
                  accent={stage.color}
                  busy={
                    warnPending || (!!v.id && promptBusyId === v.id)
                  }
                  feedback={
                    v.id && promptFb?.visitId === v.id ? promptFb : null
                  }
                  onNeedPrompt={onNeedPrompt}
                  onToggleInsurance={onToggleInsurance}
                />
              ))}
            </div>
          )}

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
                <DraftVisitCard
                  key={v.id || `${v.doctor}-draft`}
                  visit={v}
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

/** Bright card: real booking with date/time + prompt */
function BookedVisitCard({
  visit,
  accent,
  busy,
  feedback,
  onNeedPrompt,
  onToggleInsurance,
}: {
  visit: VisitItem;
  accent: string;
  busy: boolean;
  feedback?: PromptFeedback | null;
  onNeedPrompt: (id: string) => void;
  onToggleInsurance: (id: string, next: boolean) => void;
}) {
  const warned = !!visit.insurance_warned;
  const id = visit.id;

  return (
    <div
      className="rounded-2xl px-3 py-2.5 border border-[#007AFF]/25 bg-gradient-to-br from-[#007AFF]/[0.08] to-white"
      style={{ boxShadow: `0 0 0 1px ${accent}22` }}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 flex items-start gap-2">
          <div className="w-8 h-8 rounded-xl bg-[#007AFF]/15 flex items-center justify-center shrink-0 mt-0.5">
            <CalendarCheck2 className="w-4 h-4 text-[#007AFF]" />
          </div>
          <div className="min-w-0">
            <p className="text-[14px] font-semibold leading-snug">
              {visit.doctor || visit.title}
            </p>
            <p className="text-[13px] text-[#007AFF] font-medium mt-0.5 tabular-nums">
              {visit.effective_date || visit.visit_date || visit.date || "—"}
              {visit.time ? ` · ${visit.time}` : ""}
            </p>
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
          <StatusPill tone="info">записан</StatusPill>
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

      {id && (
        <div className="mt-2.5 space-y-2">
          <button
            type="button"
            disabled={busy}
            onClick={() => onNeedPrompt(id)}
            className="w-full h-9 rounded-xl text-[12px] font-semibold pressable inline-flex items-center justify-center gap-1.5 disabled:opacity-50 bg-[#007AFF] text-white"
          >
            <FileText className="w-3.5 h-3.5" />
            {busy ? "Готовлю…" : "Нужен промпт"}
          </button>
          {feedback && !feedback.error && (
            <p className="text-[11px] text-center text-[#8E8E93] leading-snug">
              {feedback.telegram_sent
                ? "✓ Markdown отправлен в Telegram"
                : feedback.hint || "Файл промпта сохранён"}
            </p>
          )}
          {feedback?.error && (
            <p className="text-[11px] text-center text-[#FF3B30]">
              {feedback.error}
            </p>
          )}
          <button
            type="button"
            disabled={busy}
            onClick={() => onToggleInsurance(id, !warned)}
            className={cn(
              "w-full h-9 rounded-xl text-[12px] font-semibold pressable inline-flex items-center justify-center gap-1.5 disabled:opacity-50",
              warned
                ? "bg-[#34C759]/15 text-[#248A3D]"
                : "bg-[#FF9500]/15 text-[#C93400]",
            )}
          >
            {warned ? (
              <>
                <ShieldCheck className="w-3.5 h-3.5" />
                Страховая предупреждена
              </>
            ) : (
              <>
                <ShieldAlert className="w-3.5 h-3.5" />
                Отметить: страховая предупреждена
              </>
            )}
          </button>
        </div>
      )}
    </div>
  );
}

/** Grey task card: agent recommendation, need to book */
function DraftVisitCard({ visit }: { visit: VisitItem }) {
  const who = visit.doctor || visit.specialty || visit.title || "врачу";
  return (
    <div className="rounded-2xl px-3 py-2.5 bg-[#8E8E93]/[0.08] border border-dashed border-[#C7C7CC]">
      <div className="flex items-start gap-2">
        <div className="w-8 h-8 rounded-xl bg-black/5 flex items-center justify-center shrink-0 mt-0.5">
          <CalendarPlus className="w-4 h-4 text-[#8E8E93]" />
        </div>
        <div className="min-w-0 flex-1">
          <p className="text-[14px] font-medium text-[#636366] leading-snug">
            Нужно записаться к {who}
          </p>
          {visit.purpose && (
            <p className="text-[12px] text-[#8E8E93] mt-1 line-clamp-2">
              {visit.purpose}
            </p>
          )}
          {visit.notes && (
            <p className="text-[11px] text-[#AEAEB2] mt-1 line-clamp-2">
              {visit.notes}
            </p>
          )}
        </div>
        <StatusPill tone="neutral">записать</StatusPill>
      </div>
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
