import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Copy, Save, Swords } from "lucide-react";
import {
  GlassCard,
  PageHeader,
  SectionHeader,
  StatusPill,
} from "../../../components/apple";
import {
  composeTrojan,
  fetchTrojan,
  saveTrojan,
} from "../../../lib/services";
import { cn } from "../../../lib/utils";

export default function TrojanHorsePage() {
  const qc = useQueryClient();
  const { data, isLoading, isError } = useQuery({
    queryKey: ["trojan"],
    queryFn: fetchTrojan,
  });

  const [specialty, setSpecialty] = useState("Кардиология");
  const [complaintIds, setComplaintIds] = useState<string[]>([]);
  const [boosterIds, setBoosterIds] = useState<string[]>([]);
  const [notes, setNotes] = useState("");
  const [script, setScript] = useState<string | null>(null);
  const [copyMsg, setCopyMsg] = useState<string | null>(null);

  useEffect(() => {
    if (!data) return;
    setSpecialty(data.specialty);
    setComplaintIds(data.selected_complaint_ids || []);
    setBoosterIds(data.selected_booster_ids || []);
    setNotes(data.notes || "");
  }, [data]);

  const boosters = useMemo(() => {
    if (!data) return [];
    return (
      data.boosters_by_specialty?.[specialty] ||
      data.boosters ||
      []
    );
  }, [data, specialty]);

  const saveMut = useMutation({
    mutationFn: () =>
      saveTrojan({
        specialty,
        complaint_ids: complaintIds,
        booster_ids: boosterIds,
        notes,
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["trojan"] }),
  });

  const composeMut = useMutation({
    mutationFn: () =>
      composeTrojan({
        specialty,
        complaint_ids: complaintIds,
        booster_ids: boosterIds,
      }),
    onSuccess: (res) => setScript(res.script),
  });

  const toggle = (list: string[], id: string, set: (v: string[]) => void) => {
    set(list.includes(id) ? list.filter((x) => x !== id) : [...list, id]);
  };

  const onCopy = async () => {
    if (!script) return;
    try {
      await navigator.clipboard.writeText(script);
      setCopyMsg("Скопировано");
      setTimeout(() => setCopyMsg(null), 1500);
    } catch {
      setCopyMsg("Не удалось скопировать");
    }
  };

  return (
    <div className="page-shell section-gap">
      <PageHeader subtitle="Аппрув чекапа" title="Троянский конь" />
      <p className="text-[13px] text-[#8E8E93] -mt-2 leading-relaxed">
        Реальные жалобы + точечные усиления → направления без «просто посмотреть»
      </p>

      {isLoading && (
        <GlassCard padding="lg">
          <p className="text-[#8E8E93]">Загрузка…</p>
        </GlassCard>
      )}
      {isError && (
        <GlassCard padding="lg">
          <p className="text-[#FF3B30]">Не удалось загрузить /api/trojan</p>
        </GlassCard>
      )}

      {data && (
        <>
          <GlassCard padding="md">
            <div className="flex items-center gap-2 mb-3">
              <div className="w-10 h-10 rounded-2xl bg-[#AF52DE]/15 flex items-center justify-center">
                <Swords className="w-5 h-5 text-[#AF52DE]" />
              </div>
              <div>
                <p className="text-[15px] font-semibold">Направление</p>
                <p className="text-[12px] text-[#8E8E93]">Специальность для микса</p>
              </div>
            </div>
            <div className="flex flex-wrap gap-2">
              {data.specialties.map((s) => (
                <button
                  key={s}
                  type="button"
                  onClick={() => {
                    setSpecialty(s);
                    setBoosterIds([]);
                    setScript(null);
                  }}
                  className={cn(
                    "h-9 px-3 rounded-full text-[13px] font-medium pressable",
                    specialty === s
                      ? "bg-[#AF52DE] text-white"
                      : "bg-black/5 text-[#1C1C1E]",
                  )}
                >
                  {s}
                </button>
              ))}
            </div>
          </GlassCard>

          <section>
            <SectionHeader
              title="Реальные жалобы"
              action={
                <span className="caption">{complaintIds.length} выбрано</span>
              }
            />
            <div className="space-y-2">
              {data.complaints.length === 0 && (
                <GlassCard padding="md">
                  <p className="text-[13px] text-[#8E8E93]">
                    Копилка пуста — добавьте жалобы в разделе «Жалобы»
                  </p>
                </GlassCard>
              )}
              {data.complaints.map((c) => {
                const on = c.id ? complaintIds.includes(c.id) : false;
                return (
                  <button
                    key={c.id}
                    type="button"
                    onClick={() => c.id && toggle(complaintIds, c.id, setComplaintIds)}
                    className={cn(
                      "w-full text-left rounded-[20px] px-4 py-3 pressable border",
                      on
                        ? "bg-[#007AFF]/10 border-[#007AFF]/30"
                        : "bg-white border-transparent shadow-[var(--shadow-card)]",
                    )}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <p className="text-[14px] font-medium leading-snug">
                        {c.text}
                      </p>
                      {on && <StatusPill tone="info">в миксе</StatusPill>}
                    </div>
                    <p className="text-[12px] text-[#8E8E93] mt-1">
                      {c.specialty_hint || "—"}
                      {c.severity != null ? ` · сила ${c.severity}` : ""}
                    </p>
                  </button>
                );
              })}
            </div>
          </section>

          <section>
            <SectionHeader
              title="Усиления"
              action={
                <span className="caption">{boosterIds.length} выбрано</span>
              }
            />
            <p className="text-[12px] text-[#8E8E93] mb-2 px-0.5">
              Не выдумка диагноза — формулировки, которые обычно открывают чекап
            </p>
            <div className="space-y-2">
              {boosters.map((b) => {
                const on = boosterIds.includes(b.id);
                return (
                  <button
                    key={b.id}
                    type="button"
                    onClick={() => toggle(boosterIds, b.id, setBoosterIds)}
                    className={cn(
                      "w-full text-left rounded-[20px] px-4 py-3 pressable border",
                      on
                        ? "bg-[#FF9500]/12 border-[#FF9500]/35"
                        : "bg-white border-transparent shadow-[var(--shadow-card)]",
                    )}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <p className="text-[14px] font-medium leading-snug">
                        {b.text}
                      </p>
                      {on && <StatusPill tone="warn">усиление</StatusPill>}
                    </div>
                    <p className="text-[12px] text-[#8E8E93] mt-1">
                      {b.rationale}
                    </p>
                  </button>
                );
              })}
            </div>
          </section>

          <GlassCard padding="md">
            <p className="text-[13px] font-semibold mb-2">Заметки</p>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={3}
              placeholder="Контекст для Pre-Visit / терапевта…"
              className="w-full rounded-2xl bg-black/[0.04] px-3 py-2.5 text-[14px] outline-none focus:ring-2 focus:ring-[#AF52DE]/40 resize-none"
            />
          </GlassCard>

          <div className="grid grid-cols-2 gap-2">
            <button
              type="button"
              disabled={saveMut.isPending}
              onClick={() => saveMut.mutate()}
              className="h-11 rounded-2xl bg-[#1C1C1E] text-white font-semibold text-[14px] pressable disabled:opacity-50 inline-flex items-center justify-center gap-1.5"
            >
              <Save className="w-4 h-4" />
              {saveMut.isPending ? "…" : "Сохранить"}
            </button>
            <button
              type="button"
              disabled={composeMut.isPending}
              onClick={() => composeMut.mutate()}
              className="h-11 rounded-2xl bg-[#AF52DE] text-white font-semibold text-[14px] pressable disabled:opacity-50 inline-flex items-center justify-center gap-1.5"
            >
              <Swords className="w-4 h-4" />
              {composeMut.isPending ? "…" : "Собрать скрипт"}
            </button>
          </div>

          {saveMut.isSuccess && (
            <p className="text-[12px] text-center text-[#34C759]">Сохранено</p>
          )}

          {script && (
            <GlassCard padding="md">
              <div className="flex items-center justify-between mb-2">
                <p className="text-[15px] font-semibold">Скрипт визита</p>
                <button
                  type="button"
                  onClick={onCopy}
                  className="text-[13px] text-[#007AFF] font-medium inline-flex items-center gap-1 pressable"
                >
                  <Copy className="w-3.5 h-3.5" />
                  {copyMsg || "Копировать"}
                </button>
              </div>
              <pre className="text-[12px] leading-relaxed whitespace-pre-wrap font-sans text-[#1C1C1E]/90">
                {script}
              </pre>
            </GlassCard>
          )}
        </>
      )}
    </div>
  );
}
