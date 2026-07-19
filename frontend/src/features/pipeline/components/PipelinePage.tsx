import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  Check,
  FlaskConical,
  Sparkles,
  Stethoscope,
  Users,
  FileCheck2,
  ChevronRight,
  ShieldAlert,
} from "lucide-react";
import { GlassCard, PageHeader, SectionHeader, StatusPill } from "../../../components/apple";
import { fetchPipeline } from "../../../lib/services";
import type { PipelineStage, VisitItem } from "../../../lib/types";
import { cn } from "../../../lib/utils";

const ICONS: Record<string, React.FC<{ className?: string; style?: React.CSSProperties }>> = {
  stethoscope: Stethoscope,
  users: Users,
  flask: FlaskConical,
  "file-check": FileCheck2,
  sparkles: Sparkles,
};

export default function PipelinePage() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["pipeline"],
    queryFn: fetchPipeline,
    staleTime: 20_000,
  });

  return (
    <div className="page-shell section-gap">
      <PageHeader subtitle="5 этапов" title="Конвейер" />
      <p className="text-[13px] text-[#8E8E93] -mt-2 leading-relaxed">
        Терапевт → спецы (1 день) → анализы → финальный разбор → сливки
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
          {/* Progress strip */}
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
              />
            ))}
          </section>

          <Link to="/timeline" className="block">
            <GlassCard padding="md" className="pressable">
              <p className="text-[15px] font-semibold">Таймлайн</p>
              <p className="text-[12px] text-[#8E8E93] mt-0.5">
                Будущие визиты · «Нужен промпт» → Gemini-файл в Telegram
              </p>
            </GlassCard>
          </Link>
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
}: {
  stage: PipelineStage;
  isActive: boolean;
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
            <VisitRow key={v.id || `${v.doctor}-${v.date}`} visit={v} />
          ))}
        </div>
      )}
    </GlassCard>
  );
}

function VisitRow({ visit }: { visit: VisitItem }) {
  const warned = !!visit.insurance_warned;
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
      <Link
        to="/timeline"
        className="inline-flex items-center gap-0.5 text-[12px] text-[#007AFF] font-medium mt-1.5"
      >
        В таймлайне <ChevronRight className="w-3.5 h-3.5" />
      </Link>
    </div>
  );
}
