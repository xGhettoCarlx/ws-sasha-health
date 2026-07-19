/**
 * Trojan Horse panel — base pack for pre-visit PDF prompt (Insurance workspace).
 * Auto-saves selection; no separate «Сохранить» / «Скрипт» buttons (Part 2 Phase 4).
 */
import { useEffect, useMemo, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Check, Swords } from "lucide-react";
import {
  GlassCard,
  SectionHeader,
  StatusPill,
} from "../../../components/apple";
import { fetchTrojan, saveTrojan } from "../../../lib/services";
import { cn } from "../../../lib/utils";

export function TrojanHorsePanel({ compact = false }: { compact?: boolean }) {
  const qc = useQueryClient();
  const { data, isLoading, isError } = useQuery({
    queryKey: ["trojan"],
    queryFn: fetchTrojan,
  });

  const [specialty, setSpecialty] = useState("Кардиология");
  const [complaintIds, setComplaintIds] = useState<string[]>([]);
  const [boosterIds, setBoosterIds] = useState<string[]>([]);
  const [notes, setNotes] = useState("");
  const [saveMsg, setSaveMsg] = useState<string | null>(null);
  const hydrated = useRef(false);
  const skipNextSave = useRef(true);

  useEffect(() => {
    if (!data) return;
    setSpecialty(data.specialty || "Кардиология");
    setComplaintIds(data.selected_complaint_ids || []);
    setBoosterIds(data.selected_booster_ids || []);
    setNotes(data.notes || "");
    hydrated.current = true;
    skipNextSave.current = true;
  }, [data]);

  const boosters = useMemo(() => {
    if (!data) return [];
    return data.boosters_by_specialty?.[specialty] || data.boosters || [];
  }, [data, specialty]);

  const relatedComplaints = useMemo(() => {
    if (!data?.complaints) return [];
    const key = specialty.toLowerCase().slice(0, 5);
    const scored = data.complaints.map((c) => {
      const hint = (c.specialty_hint || "").toLowerCase();
      const tags = (c.tags || []).join(" ").toLowerCase();
      const text = (c.text || "").toLowerCase();
      const hit =
        hint.includes(key.slice(0, 4)) ||
        tags.includes(key.slice(0, 4)) ||
        (specialty.startsWith("Кардио") &&
          (text.includes("пульс") ||
            text.includes("давлен") ||
            text.includes("сердц"))) ||
        (specialty.startsWith("Гастро") &&
          (text.includes("подребер") ||
            text.includes("живот") ||
            text.includes("желч"))) ||
        (specialty.startsWith("ЛОР") &&
          (text.includes("нос") ||
            text.includes("храп") ||
            text.includes("заложен")));
      return { c, hit };
    });
    return [
      ...scored.filter((x) => x.hit).map((x) => x.c),
      ...scored.filter((x) => !x.hit).map((x) => x.c),
    ];
  }, [data, specialty]);

  const saveMut = useMutation({
    mutationFn: () =>
      saveTrojan({
        specialty,
        complaint_ids: complaintIds,
        booster_ids: boosterIds,
        notes,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["trojan"] });
      setSaveMsg("База обновлена");
      setTimeout(() => setSaveMsg(null), 1600);
    },
  });

  // Auto-save selection (debounced) — no explicit Save/Script buttons
  useEffect(() => {
    if (!hydrated.current) return;
    if (skipNextSave.current) {
      skipNextSave.current = false;
      return;
    }
    const t = window.setTimeout(() => {
      saveMut.mutate();
    }, 450);
    return () => window.clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps -- deliberate autosave on selection
  }, [specialty, complaintIds, boosterIds, notes]);

  const toggle = (list: string[], id: string, set: (v: string[]) => void) => {
    set(list.includes(id) ? list.filter((x) => x !== id) : [...list, id]);
  };

  const mixCount = complaintIds.length + boosterIds.length;

  if (isLoading) {
    return (
      <GlassCard padding="md">
        <p className="text-[#8E8E93]">Загрузка Троянского коня…</p>
      </GlassCard>
    );
  }
  if (isError || !data) {
    return (
      <GlassCard padding="md">
        <p className="text-[#FF3B30]">Не удалось загрузить /api/trojan</p>
      </GlassCard>
    );
  }

  return (
    <div className={cn("space-y-3", compact && "space-y-2")}>
      <GlassCard padding="md">
        <div className="flex items-center gap-2 mb-2">
          <div className="w-10 h-10 rounded-2xl bg-[#AF52DE]/15 flex items-center justify-center">
            <Swords className="w-5 h-5 text-[#AF52DE]" />
          </div>
          <div className="min-w-0 flex-1">
            <p className="text-[15px] font-semibold">База для PDF-промпта</p>
            <p className="text-[12px] text-[#8E8E93] leading-snug">
              Выбери направление и формулировки — они уйдут в «Нужен промпт» на
              Конвейере (бот + печать).
            </p>
          </div>
          {saveMsg && (
            <span className="text-[11px] font-medium text-[#34C759] shrink-0 inline-flex items-center gap-0.5">
              <Check className="w-3.5 h-3.5" />
              {saveMsg}
            </span>
          )}
        </div>

        <p className="text-[11px] font-semibold text-[#8E8E93] uppercase tracking-wide mb-2">
          Направление
        </p>
        <div className="grid grid-cols-2 gap-2">
          {data.specialties.map((s) => {
            const on = specialty === s;
            return (
              <button
                key={s}
                type="button"
                onClick={() => {
                  setSpecialty(s);
                  setBoosterIds([]);
                }}
                className={cn(
                  "min-h-[44px] px-3 py-2 rounded-2xl text-[13px] font-semibold text-left pressable border transition-colors",
                  on
                    ? "bg-[#AF52DE] text-white border-[#AF52DE]"
                    : "bg-black/[0.04] text-[#1C1C1E] border-transparent",
                )}
              >
                {s}
              </button>
            );
          })}
        </div>

        <div className="mt-3 flex flex-wrap gap-1.5">
          <StatusPill tone="info">{mixCount} в базе</StatusPill>
          <StatusPill tone="neutral">{complaintIds.length} жалоб</StatusPill>
          <StatusPill tone="warn">{boosterIds.length} усилений</StatusPill>
        </div>
      </GlassCard>

      <section>
        <SectionHeader
          title="Жалобы из копилки"
          action={
            <span className="caption">{complaintIds.length} выбрано</span>
          }
        />
        <div className="grid grid-cols-1 gap-2">
          {relatedComplaints.length === 0 && (
            <GlassCard padding="md">
              <p className="text-[13px] text-[#8E8E93]">
                Копилка жалоб пуста — агент добавит перед визитом
              </p>
            </GlassCard>
          )}
          {relatedComplaints.map((c) => {
            const on = c.id ? complaintIds.includes(c.id) : false;
            return (
              <button
                key={c.id}
                type="button"
                onClick={() => c.id && toggle(complaintIds, c.id, setComplaintIds)}
                className={cn(
                  "w-full text-left rounded-2xl px-3.5 py-3 pressable border min-h-[56px]",
                  on
                    ? "bg-[#007AFF]/12 border-[#007AFF]/35"
                    : "bg-white border-black/[0.06] shadow-[var(--shadow-card)]",
                )}
              >
                <div className="flex items-start justify-between gap-2">
                  <p className="text-[14px] font-medium leading-snug">{c.text}</p>
                  {on && <StatusPill tone="info">в базе</StatusPill>}
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
          title="Формулировки (усиления)"
          action={<span className="caption">{boosterIds.length}</span>}
        />
        <p className="text-[12px] text-[#8E8E93] mb-2 px-0.5">
          Клинически уместные фразы для {specialty} — основа листа врачу
        </p>
        <div className="grid grid-cols-1 gap-2">
          {boosters.map((b) => {
            const on = boosterIds.includes(b.id);
            return (
              <button
                key={b.id}
                type="button"
                onClick={() => toggle(boosterIds, b.id, setBoosterIds)}
                className={cn(
                  "w-full text-left rounded-2xl px-3.5 py-3 pressable border min-h-[56px]",
                  on
                    ? "bg-[#FF9500]/14 border-[#FF9500]/40"
                    : "bg-white border-black/[0.06] shadow-[var(--shadow-card)]",
                )}
              >
                <div className="flex items-start justify-between gap-2">
                  <p className="text-[14px] font-medium leading-snug">{b.text}</p>
                  {on && <StatusPill tone="warn">в базе</StatusPill>}
                </div>
                <p className="text-[12px] text-[#8E8E93] mt-1">{b.rationale}</p>
              </button>
            );
          })}
        </div>
      </section>

      <GlassCard padding="md">
        <p className="text-[13px] font-semibold mb-2">Заметки к промпту</p>
        <textarea
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          rows={2}
          placeholder="Контекст для страховки / Pre-Visit…"
          className="w-full rounded-2xl bg-black/[0.04] px-3 py-2.5 text-[14px] outline-none focus:ring-2 focus:ring-[#AF52DE]/40 resize-none"
        />
        <p className="text-[11px] text-[#AEAEB2] mt-2 leading-snug">
          Сохранение автоматическое. PDF-лист — кнопка «Нужен промпт» на
          Конвейере у нужного визита.
        </p>
      </GlassCard>
    </div>
  );
}

export default TrojanHorsePanel;
