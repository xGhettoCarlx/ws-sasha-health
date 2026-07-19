import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { GlassCard, PageHeader, SectionHeader } from "../../../components/apple";
import {
  fetchComplaints,
  postComplaint,
  resolveComplaint,
  type ComplaintItem,
} from "../../../lib/navigator-api";

export default function ComplaintsPage() {
  const qc = useQueryClient();
  const { data, isLoading } = useQuery({
    queryKey: ["complaints"],
    queryFn: () => fetchComplaints(false),
  });
  const [text, setText] = useState("");
  const [severity, setSeverity] = useState(5);

  const add = useMutation({
    mutationFn: () => postComplaint({ text, severity }),
    onSuccess: () => {
      setText("");
      setSeverity(5);
      qc.invalidateQueries({ queryKey: ["complaints"] });
      qc.invalidateQueries({ queryKey: ["overview"] });
      qc.invalidateQueries({ queryKey: ["navigator"] });
    },
  });

  const resolve = useMutation({
    mutationFn: (id: string) => resolveComplaint(id, false),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["complaints"] });
      qc.invalidateQueries({ queryKey: ["overview"] });
    },
  });

  return (
    <div className="page-shell section-gap">
      <PageHeader subtitle="До визита" title="Копилка жалоб" />
      <p className="text-[13px] text-[#8E8E93] -mt-2">
        Фиксируйте симптомы — они попадут в Pre-Visit промпт
      </p>

      <GlassCard padding="lg">
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          rows={3}
          placeholder="Что беспокоит? (например: тянущая боль в правом подреберье после обеда)"
          className="w-full rounded-2xl bg-black/[0.04] p-3 text-[15px] outline-none focus:ring-2 focus:ring-[#007AFF]/40 resize-none"
        />
        <div className="flex items-center gap-3 mt-3">
          <label className="text-[13px] text-[#8E8E93] shrink-0">Сила {severity}</label>
          <input
            type="range"
            min={1}
            max={10}
            value={severity}
            onChange={(e) => setSeverity(Number(e.target.value))}
            className="flex-1 accent-[#AF52DE]"
          />
        </div>
        <button
          type="button"
          disabled={text.trim().length < 2 || add.isPending}
          onClick={() => add.mutate()}
          className="mt-3 w-full h-11 rounded-2xl bg-[#AF52DE] text-white font-semibold text-[15px] pressable disabled:opacity-50"
        >
          {add.isPending ? "Добавляю…" : "В копилку"}
        </button>
      </GlassCard>

      <section>
        <SectionHeader
          title="Открытые"
          action={<span className="caption">{data?.count ?? 0}</span>}
        />
        {isLoading && (
          <p className="text-[#8E8E93] text-[14px]">Загрузка…</p>
        )}
        <div className="space-y-2">
          {(data?.items || []).map((c) => (
            <ComplaintCard
              key={c.id}
              item={c}
              onResolve={() => resolve.mutate(c.id)}
            />
          ))}
          {data && data.items.length === 0 && (
            <GlassCard padding="lg">
              <p className="text-[14px] text-[#8E8E93] text-center">
                Пока пусто — добавьте первую жалобу
              </p>
            </GlassCard>
          )}
        </div>
      </section>
    </div>
  );
}

function ComplaintCard({
  item,
  onResolve,
}: {
  item: ComplaintItem;
  onResolve: () => void;
}) {
  return (
    <GlassCard padding="md">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="text-[12px] font-semibold text-[#8E8E93]">
            {item.date}
            {item.specialty_hint ? ` · ${item.specialty_hint}` : ""}
            {` · сила ${item.severity}/10`}
          </p>
          <p className="text-[15px] font-medium leading-snug mt-1">{item.text}</p>
          {item.navigator && item.navigator[0] && (
            <p className="text-[12px] text-[#007AFF] mt-2">
              → {item.navigator[0].specialty}
              {item.navigator[0].covered === false
                ? " · не покрывается"
                : " · страховка ок"}
            </p>
          )}
        </div>
        <button
          type="button"
          onClick={onResolve}
          className="text-[12px] font-semibold text-[#8E8E93] px-2 py-1 rounded-full bg-black/5 shrink-0"
        >
          Готово
        </button>
      </div>
    </GlassCard>
  );
}
