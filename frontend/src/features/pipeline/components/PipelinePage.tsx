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

function isActionableVisit(item: VisitItem): boolean {
  if (item.status === "completed" || item.status === "cancelled") return false;
  return true;
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
        Терапевт → спецы (1 день) → анализы → финальный разбор → сливки.
        Промпт и страховка — на карточках визитов.
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
              Активный этап {data.active_stage} · открыто {data.summary.open} ·
              страховка ⚠ {data.summary.insurance_pending}
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
            {stage.counts.completed}/{stage.counts.total} · открыто {stage.counts.open}
          </p>
        </div>
      </div>

      {stage.visits.length > 0 && (
        <div className="mt-3 space-y-2 border-t border-black/5 pt-3">
          <SectionHeader
            title="Визиты"
            action={<span className="caption">{stage.visits.length}</span>}
          />
          {stage.visits.map((v) => (
            <VisitRow
              key={v.id || `${v.doctor}-${v.date}`}
              visit={v}
              busy={
                warnPending ||
                (!!v.id && promptBusyId === v.id)
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
    </GlassCard>
  );
}

function VisitRow({
  visit,
  busy,
  feedback,
  onNeedPrompt,
  onToggleInsurance,
}: {
  visit: VisitItem;
  busy: boolean;
  feedback?: PromptFeedback | null;
  onNeedPrompt: (id: string) => void;
  onToggleInsurance: (id: string, next: boolean) => void;
}) {
  const warned = !!visit.insurance_warned;
  const id = visit.id;
  const showActions = !!id && isActionableVisit(visit);

  return (
    <div className="rounded-2xl bg-black/[0.03] px-3 py-2.5">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="text-[14px] font-semibold truncate">
            {visit.doctor || visit.title}
          </p>
          <p className="text-[12px] text-[#8E8E93] mt-0.5">
            {visit.effective_date || visit.visit_date || visit.date}
            {visit.time ? ` · ${visit.time}` : ""}
            {visit.institution ? ` · ${visit.institution}` : ""}
          </p>
          {visit.purpose && (
            <p className="text-[12px] text-[#1C1C1E]/80 mt-1 line-clamp-2">
              {visit.purpose}
            </p>
          )}
        </div>
        <div className="flex flex-col items-end gap-1 shrink-0">
          <StatusPill
            tone={
              visit.status === "completed"
                ? "ok"
                : visit.status === "cancelled"
                  ? "danger"
                  : "warn"
            }
          >
            {visit.status}
          </StatusPill>
          {visit.status !== "completed" && (
            <span
              className={cn(
                "inline-flex items-center gap-0.5 text-[10px] font-medium",
                warned ? "text-[#34C759]" : "text-[#FF9500]",
              )}
            >
              <ShieldAlert className="w-3 h-3" />
              {warned ? "страховка ✓" : "не предупреждена"}
            </span>
          )}
        </div>
      </div>

      {showActions && (
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
