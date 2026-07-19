import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  CalendarClock,
  FileText,
  History,
  ShieldAlert,
  ShieldCheck,
} from "lucide-react";
import {
  GlassCard,
  PageHeader,
  SectionHeader,
  StatusPill,
} from "../../../components/apple";
import {
  fetchTimeline,
  requestVisitPrompt,
  setInsuranceWarned,
} from "../../../lib/services";
import type { VisitItem } from "../../../lib/types";
import { cn } from "../../../lib/utils";

function isFutureVisit(item: VisitItem, todayIso: string): boolean {
  if (item.status === "completed" || item.status === "cancelled") return false;
  const raw = item.effective_date || item.visit_date || item.date || "";
  if (!raw) return item.status === "planned" || item.status === "pending";
  const d = raw.slice(0, 10);
  return d >= todayIso.slice(0, 10);
}

type PromptFeedback = {
  visitId: string;
  telegram_sent?: boolean;
  hint?: string;
  error?: string;
};

export default function TimelinePage() {
  const qc = useQueryClient();
  const [promptFb, setPromptFb] = useState<PromptFeedback | null>(null);
  const [promptBusyId, setPromptBusyId] = useState<string | null>(null);

  const { data, isLoading, isError } = useQuery({
    queryKey: ["timeline"],
    queryFn: fetchTimeline,
    staleTime: 20_000,
  });

  const warnMut = useMutation({
    mutationFn: ({ id, v }: { id: string; v: boolean }) =>
      setInsuranceWarned(id, v),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["timeline"] });
      qc.invalidateQueries({ queryKey: ["pipeline"] });
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
      <PageHeader subtitle="Единая лента" title="Таймлайн" />
      <p className="text-[13px] text-[#8E8E93] -mt-2 leading-relaxed">
        Будущее — расписание · Прошлое — по месяцам и годам
      </p>

      {isLoading && (
        <GlassCard padding="lg">
          <p className="text-[#8E8E93]">Загрузка ленты…</p>
        </GlassCard>
      )}
      {isError && (
        <GlassCard padding="lg">
          <p className="text-[#FF3B30]">Не удалось загрузить /api/timeline</p>
        </GlassCard>
      )}

      {data && (
        <>
          <div className="grid grid-cols-3 gap-2">
            <Stat label="Впереди" value={data.counts.future} color="#007AFF" />
            <Stat label="В прошлом" value={data.counts.past} color="#8E8E93" />
            <Stat
              label="Страх. ⚠"
              value={data.counts.insurance_unwarned_future}
              color="#FF9500"
            />
          </div>

          {/* FUTURE */}
          <section>
            <SectionHeader
              title="Будущее"
              action={
                <span className="caption inline-flex items-center gap-1">
                  <CalendarClock className="w-3.5 h-3.5" />
                  {data.future.length}
                </span>
              }
            />
            {data.future.length === 0 ? (
              <GlassCard padding="md">
                <p className="text-[13px] text-[#8E8E93]">Нет предстоящих визитов</p>
              </GlassCard>
            ) : (
              <div className="space-y-2">
                {data.future.map((item) => (
                  <FutureCard
                    key={item.id || `${item.doctor}-${item.date}`}
                    item={item}
                    today={data.today}
                    busy={
                      warnMut.isPending ||
                      (!!item.id && promptBusyId === item.id)
                    }
                    feedback={
                      item.id && promptFb?.visitId === item.id ? promptFb : null
                    }
                    onToggleInsurance={(id, next) =>
                      warnMut.mutate({ id, v: next })
                    }
                    onNeedPrompt={(id) => promptMut.mutate(id)}
                  />
                ))}
              </div>
            )}
          </section>

          {/* PAST */}
          <section>
            <SectionHeader
              title="Прошлое"
              action={
                <span className="caption inline-flex items-center gap-1">
                  <History className="w-3.5 h-3.5" />
                  {data.past.count}
                </span>
              }
            />
            <div className="space-y-4">
              {data.past.groups.map((yg) => (
                <div key={yg.year}>
                  <p className="text-[20px] font-semibold tracking-tight mb-2 px-0.5">
                    {yg.year}
                  </p>
                  <div className="space-y-3">
                    {yg.months.map((mg) => (
                      <div key={`${yg.year}-${mg.month}`}>
                        <p className="text-[13px] font-semibold text-[#8E8E93] mb-1.5 px-0.5">
                          {mg.label}
                        </p>
                        <div className="space-y-2 border-l-2 border-black/10 pl-3 ml-1">
                          {mg.items.map((item, i) => (
                            <PastCard
                              key={
                                item.id ||
                                `${item.title}-${item.date}-${i}`
                              }
                              item={item}
                            />
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
              {data.past.undated.length > 0 && (
                <div>
                  <p className="text-[13px] font-semibold text-[#8E8E93] mb-1.5">
                    Без даты
                  </p>
                  <div className="space-y-2">
                    {data.past.undated.map((item, i) => (
                      <PastCard
                        key={item.id || `undated-${i}`}
                        item={item}
                      />
                    ))}
                  </div>
                </div>
              )}
              {data.past.groups.length === 0 && data.past.undated.length === 0 && (
                <GlassCard padding="md">
                  <p className="text-[13px] text-[#8E8E93]">Пока пусто</p>
                </GlassCard>
              )}
            </div>
          </section>
        </>
      )}
    </div>
  );
}

function Stat({
  label,
  value,
  color,
}: {
  label: string;
  value: number;
  color: string;
}) {
  return (
    <GlassCard padding="md" className="text-center">
      <p className="text-[22px] font-semibold" style={{ color }}>
        {value}
      </p>
      <p className="text-[11px] text-[#8E8E93] font-medium">{label}</p>
    </GlassCard>
  );
}

function FutureCard({
  item,
  today,
  busy,
  feedback,
  onToggleInsurance,
  onNeedPrompt,
}: {
  item: VisitItem;
  today: string;
  busy: boolean;
  feedback?: PromptFeedback | null;
  onToggleInsurance: (id: string, next: boolean) => void;
  onNeedPrompt: (id: string) => void;
}) {
  const warned = !!item.insurance_warned;
  const id = item.id;
  const showPrompt = isFutureVisit(item, today);
  return (
    <GlassCard padding="md">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="text-[15px] font-semibold leading-snug">
            {item.doctor || item.title}
          </p>
          <p className="text-[13px] text-[#8E8E93] mt-0.5">
            {item.effective_date || item.visit_date || item.date}
            {item.time ? ` · ${item.time}` : ""}
          </p>
          {item.pipeline_stage != null && (
            <p className="text-[12px] text-[#AEAEB2] mt-0.5">
              Этап {item.pipeline_stage}
              {item.specialty ? ` · ${item.specialty}` : ""}
            </p>
          )}
          {item.purpose && (
            <p className="text-[13px] text-[#1C1C1E]/85 mt-1.5 line-clamp-3">
              {item.purpose}
            </p>
          )}
        </div>
        <StatusPill tone={item.status === "planned" ? "info" : "warn"}>
          {item.status}
        </StatusPill>
      </div>

      {id && (
        <div className="mt-3 space-y-2">
          {showPrompt && (
            <button
              type="button"
              disabled={busy}
              onClick={() => onNeedPrompt(id)}
              className="w-full h-10 rounded-2xl text-[13px] font-semibold pressable inline-flex items-center justify-center gap-1.5 disabled:opacity-50 bg-[#007AFF] text-white"
            >
              <FileText className="w-4 h-4" />
              {busy ? "Готовлю…" : "Нужен промпт"}
            </button>
          )}
          {feedback && !feedback.error && (
            <p className="text-[12px] text-center text-[#8E8E93] leading-snug">
              {feedback.telegram_sent
                ? "✓ Markdown отправлен в Telegram"
                : feedback.hint || "Файл промпта сохранён"}
            </p>
          )}
          {feedback?.error && (
            <p className="text-[12px] text-center text-[#FF3B30]">
              {feedback.error}
            </p>
          )}
          <button
            type="button"
            disabled={busy}
            onClick={() => onToggleInsurance(id, !warned)}
            className={cn(
              "w-full h-10 rounded-2xl text-[13px] font-semibold pressable inline-flex items-center justify-center gap-1.5 disabled:opacity-50",
              warned
                ? "bg-[#34C759]/15 text-[#248A3D]"
                : "bg-[#FF9500]/15 text-[#C93400]",
            )}
          >
            {warned ? (
              <>
                <ShieldCheck className="w-4 h-4" />
                Страховая предупреждена
              </>
            ) : (
              <>
                <ShieldAlert className="w-4 h-4" />
                Отметить: страховая предупреждена
              </>
            )}
          </button>
        </div>
      )}
    </GlassCard>
  );
}

function PastCard({ item }: { item: VisitItem }) {
  return (
    <div className="rounded-2xl bg-white shadow-[var(--shadow-card)] px-3.5 py-2.5">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="text-[14px] font-semibold">
            {item.title || item.doctor || "Событие"}
          </p>
          <p className="text-[12px] text-[#8E8E93] mt-0.5">
            {item.effective_date || item.date || "—"}
            {item.kind === "history" && item.category
              ? ` · ${item.category}`
              : ""}
            {item.pipeline_stage != null ? ` · этап ${item.pipeline_stage}` : ""}
          </p>
          {(item.purpose || item.notes) && (
            <p className="text-[12px] text-[#1C1C1E]/75 mt-1 line-clamp-2">
              {item.purpose || item.notes}
            </p>
          )}
        </div>
        <StatusPill tone={item.kind === "history" ? "info" : "ok"}>
          {item.kind === "history" ? "файл" : item.status || "ok"}
        </StatusPill>
      </div>
    </div>
  );
}
