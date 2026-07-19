/**
 * Профиль — дашборд здоровья по категориям врачей (Phase 2 UX rework).
 * Клик по категории → будущие записи, диагнозы, обследования.
 * Заменяет «Моя медкарта».
 */
import { useMemo, useState, type ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  CalendarClock,
  ChevronLeft,
  FileHeart,
  FlaskConical,
  LogOut,
  Stethoscope,
} from "lucide-react";
import {
  GlassCard,
  PageHeader,
  SectionHeader,
  StatusPill,
} from "../../../components/apple";
import { fetchProfile, fetchTimeline } from "../../../lib/services";
import type {
  DiagnosisItem,
  TimelineResponse,
  VisitItem,
} from "../../../lib/types";
import { useAuthStore } from "../../../stores/authStore";
import { useNavigate } from "react-router-dom";
import { cn } from "../../../lib/utils";
import {
  buildCategoryBuckets,
  TRIAGE_COLORS,
  type CategoryBucket,
  type TriageLevel,
} from "../healthCategories";

function ageFromDob(dob?: string | null): number | null {
  if (!dob) return null;
  const d = new Date(dob);
  if (Number.isNaN(d.getTime())) return null;
  const now = new Date();
  let age = now.getFullYear() - d.getFullYear();
  const m = now.getMonth() - d.getMonth();
  if (m < 0 || (m === 0 && now.getDate() < d.getDate())) age -= 1;
  return age;
}

function collectVisits(timeline: TimelineResponse | null | undefined): VisitItem[] {
  if (!timeline) return [];
  const out: VisitItem[] = [...(timeline.future || [])];
  for (const year of timeline.past?.groups || []) {
    for (const month of year.months || []) {
      out.push(...(month.items || []));
    }
  }
  out.push(...(timeline.past?.undated || []));
  return out;
}

export default function ProfilePage() {
  const clearAuth = useAuthStore((s) => s.clearAuth);
  const navigate = useNavigate();
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const profileQ = useQuery({
    queryKey: ["profile"],
    queryFn: fetchProfile,
    staleTime: 30_000,
  });
  const timelineQ = useQuery({
    queryKey: ["timeline"],
    queryFn: fetchTimeline,
    staleTime: 20_000,
  });

  const buckets = useMemo(() => {
    const diagnoses = (profileQ.data?.diagnoses || []) as DiagnosisItem[];
    const visits = collectVisits(timelineQ.data ?? null);
    return buildCategoryBuckets({ diagnoses, visits });
  }, [profileQ.data, timelineQ.data]);

  const selected = useMemo(
    () => buckets.find((b) => b.def.id === selectedId) ?? null,
    [buckets, selectedId],
  );

  const summary = useMemo(() => {
    const red = buckets.filter((b) => b.triage === "red").length;
    const yellow = buckets.filter((b) => b.triage === "yellow").length;
    const active = buckets.filter(
      (b) =>
        b.diagnoses.length > 0 ||
        b.futureVisits.length > 0 ||
        b.pastVisits.length > 0,
    ).length;
    return { red, yellow, active };
  }, [buckets]);

  function logout() {
    sessionStorage.removeItem("web_auth");
    clearAuth();
    navigate("/login", { replace: true });
  }

  const p = profileQ.data;
  const age = ageFromDob(p?.birth_date);
  const initials = (p?.full_name || "СЗ")
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((x) => x[0])
    .join("")
    .toUpperCase();

  if (selected) {
    return (
      <CategoryDetail
        bucket={selected}
        onBack={() => setSelectedId(null)}
      />
    );
  }

  return (
    <div className="page-shell section-gap">
      <PageHeader title="Профиль" subtitle="Дашборд здоровья" />

      {(profileQ.isLoading || timelineQ.isLoading) && (
        <GlassCard padding="lg">
          <p className="text-[#8E8E93]">Загрузка карты…</p>
        </GlassCard>
      )}

      {(profileQ.isError || timelineQ.isError) && (
        <GlassCard padding="lg">
          <p className="text-[#FF3B30] text-[14px]">
            Не удалось загрузить данные профиля или расписания
          </p>
        </GlassCard>
      )}

      {p && (
        <GlassCard padding="lg" className="fade-up">
          <div className="flex items-center gap-3.5">
            <div
              className="w-14 h-14 rounded-full flex items-center justify-center text-white text-[18px] font-semibold shrink-0"
              style={{
                background: "linear-gradient(145deg,#007AFF,#5AC8FA)",
                boxShadow: "0 6px 18px rgba(0,122,255,0.28)",
              }}
            >
              {initials}
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-[17px] font-semibold tracking-tight leading-tight truncate">
                {p.full_name}
              </p>
              <p className="text-[13px] text-[#8E8E93] mt-0.5">
                {age != null ? `${age} лет · ` : ""}
                {p.birth_date}
              </p>
              <div className="flex flex-wrap gap-1.5 mt-2">
                {summary.red > 0 && (
                  <StatusPill tone="danger">{summary.red} срочно</StatusPill>
                )}
                {summary.yellow > 0 && (
                  <StatusPill tone="warn">{summary.yellow} контроль</StatusPill>
                )}
                <StatusPill tone="neutral">{summary.active} направл.</StatusPill>
              </div>
            </div>
          </div>
        </GlassCard>
      )}

      <section>
        <SectionHeader
          title="По направлениям"
          action={
            <span className="caption">
              🟢 спокойно · 🟡 контроль · 🔴 срочно
            </span>
          }
        />
        <div className="grid grid-cols-3 gap-2.5">
          {buckets.map((b) => (
            <CategoryCircle
              key={b.def.id}
              bucket={b}
              onClick={() => setSelectedId(b.def.id)}
            />
          ))}
        </div>
      </section>

      {p && (p.allergies?.length ?? 0) > 0 && (
        <section>
          <SectionHeader title="Аллергии" />
          <div className="flex flex-wrap gap-2">
            {p.allergies.map((a) => (
              <span
                key={a}
                className="px-3 py-1.5 rounded-full bg-[#FF2D55]/10 text-[#FF2D55] text-[13px] font-medium"
              >
                {a}
              </span>
            ))}
          </div>
        </section>
      )}

      <button
        type="button"
        onClick={logout}
        className="w-full h-11 rounded-2xl bg-black/5 text-[#FF3B30] font-semibold text-[15px] pressable flex items-center justify-center gap-2"
      >
        <LogOut className="w-4 h-4" />
        Выйти
      </button>
    </div>
  );
}

function CategoryCircle({
  bucket,
  onClick,
}: {
  bucket: CategoryBucket;
  onClick: () => void;
}) {
  const colors = TRIAGE_COLORS[bucket.triage];
  const count =
    bucket.diagnoses.length +
    bucket.futureVisits.length +
    bucket.pastVisits.length;

  return (
    <button
      type="button"
      onClick={onClick}
      className="pressable flex flex-col items-center gap-2 py-2.5 px-1 rounded-2xl"
    >
      <div
        className="relative w-[68px] h-[68px] rounded-full flex items-center justify-center"
        style={{
          background: colors.bg,
          boxShadow: `0 0 0 2.5px ${colors.ring}`,
        }}
      >
        <span className="text-[26px] leading-none" aria-hidden>
          {bucket.def.glyph}
        </span>
        {count > 0 && (
          <span
            className="absolute -top-0.5 -right-0.5 min-w-[18px] h-[18px] px-1 rounded-full text-[10px] font-bold text-white flex items-center justify-center"
            style={{ background: colors.ring }}
          >
            {count}
          </span>
        )}
      </div>
      <div className="text-center min-w-0 w-full">
        <p className="text-[12px] font-semibold text-[#1C1C1E] truncate leading-tight">
          {bucket.def.label}
        </p>
        <p
          className="text-[10px] font-medium mt-0.5 truncate"
          style={{ color: colors.text }}
        >
          {colors.label}
        </p>
      </div>
    </button>
  );
}

function CategoryDetail({
  bucket,
  onBack,
}: {
  bucket: CategoryBucket;
  onBack: () => void;
}) {
  const colors = TRIAGE_COLORS[bucket.triage];

  return (
    <div className="page-shell section-gap">
      <button
        type="button"
        onClick={onBack}
        className="inline-flex items-center gap-0.5 text-[14px] text-[#007AFF] font-medium pressable -mb-1"
      >
        <ChevronLeft className="w-4 h-4" />
        Профиль
      </button>

      <PageHeader
        title={bucket.def.specialty}
        subtitle="Направление"
        trailing={
          <span
            className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[12px] font-semibold"
            style={{ background: colors.bg, color: colors.text }}
          >
            <span
              className="w-2 h-2 rounded-full"
              style={{ background: colors.ring }}
            />
            {colors.label}
          </span>
        }
      />

      <section>
        <SectionHeader
          title="Будущие записи"
          action={
            <span className="caption">{bucket.futureVisits.length}</span>
          }
        />
        {bucket.futureVisits.length === 0 ? (
          <EmptyBlock
            icon={<CalendarClock className="w-5 h-5 text-[#C7C7CC]" />}
            text="Нет запланированных визитов"
          />
        ) : (
          <div className="space-y-2">
            {bucket.futureVisits.map((v, i) => (
              <GlassCard key={v.id || `${v.title}-${i}`} padding="md">
                <div className="flex gap-3">
                  <div className="w-10 h-10 rounded-2xl bg-[#007AFF]/12 flex items-center justify-center shrink-0">
                    <CalendarClock className="w-5 h-5 text-[#007AFF]" />
                  </div>
                  <div className="min-w-0">
                    <p className="text-[15px] font-semibold leading-snug">
                      {v.title}
                    </p>
                    <p className="text-[13px] text-[#8E8E93] mt-0.5">
                      {[v.date, v.time].filter(Boolean).join(" · ") || "дата уточняется"}
                      {v.institution ? ` · ${v.institution}` : ""}
                    </p>
                    {v.doctor && (
                      <p className="text-[12px] text-[#AEAEB2] mt-0.5 truncate">
                        {v.doctor}
                      </p>
                    )}
                  </div>
                </div>
              </GlassCard>
            ))}
          </div>
        )}
      </section>

      <section>
        <SectionHeader
          title="Диагнозы"
          action={<span className="caption">{bucket.diagnoses.length}</span>}
        />
        {bucket.diagnoses.length === 0 ? (
          <EmptyBlock
            icon={<Stethoscope className="w-5 h-5 text-[#C7C7CC]" />}
            text="Нет диагнозов в этом направлении"
          />
        ) : (
          <div className="space-y-2">
            {bucket.diagnoses.map((d, i) => (
              <GlassCard key={`${d.name}-${i}`} padding="md">
                <div className="flex items-start gap-3">
                  <TriageDot level={d.triage} />
                  <div className="min-w-0 flex-1">
                    <p className="text-[15px] font-semibold leading-snug">
                      {d.name}
                    </p>
                    <p className="text-[12px] text-[#8E8E93] mt-0.5">
                      {d.date || "—"}
                      {d.status ? ` · ${d.status}` : ""}
                    </p>
                    {d.source && (
                      <p className="text-[12px] text-[#AEAEB2] mt-1 leading-snug">
                        {d.source}
                      </p>
                    )}
                  </div>
                </div>
              </GlassCard>
            ))}
          </div>
        )}
      </section>

      <section>
        <SectionHeader
          title="Анализы и обследования"
          action={
            <span className="caption">
              {bucket.studies.length + bucket.pastVisits.length}
            </span>
          }
        />
        {bucket.studies.length === 0 && bucket.pastVisits.length === 0 ? (
          <EmptyBlock
            icon={<FlaskConical className="w-5 h-5 text-[#C7C7CC]" />}
            text="Пока нет связанных исследований"
          />
        ) : (
          <div className="space-y-2">
            {bucket.studies.map((s, i) => (
              <GlassCard key={`study-${i}`} padding="md">
                <div className="flex gap-3">
                  <div className="w-10 h-10 rounded-2xl bg-[#34C759]/12 flex items-center justify-center shrink-0">
                    <FileHeart className="w-5 h-5 text-[#34C759]" />
                  </div>
                  <p className="text-[14px] leading-snug text-[#1C1C1E] pt-2">
                    {s}
                  </p>
                </div>
              </GlassCard>
            ))}
            {bucket.pastVisits.map((v, i) => (
              <GlassCard key={v.id || `past-${i}`} padding="md">
                <div className="flex gap-3">
                  <div className="w-10 h-10 rounded-2xl bg-black/[0.05] flex items-center justify-center shrink-0">
                    <FlaskConical className="w-5 h-5 text-[#8E8E93]" />
                  </div>
                  <div className="min-w-0">
                    <p className="text-[15px] font-semibold leading-snug">
                      {v.title}
                    </p>
                    <p className="text-[12px] text-[#8E8E93] mt-0.5">
                      {v.date || "—"}
                      {v.status ? ` · ${v.status}` : ""}
                    </p>
                  </div>
                </div>
              </GlassCard>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

function TriageDot({ level }: { level: TriageLevel }) {
  const c = TRIAGE_COLORS[level];
  return (
    <span
      className="w-2.5 h-2.5 rounded-full mt-1.5 shrink-0"
      style={{ background: c.ring }}
      title={c.label}
    />
  );
}

function EmptyBlock({ icon, text }: { icon: ReactNode; text: string }) {
  return (
    <GlassCard padding="lg" className="text-center">
      <div className="flex justify-center mb-2">{icon}</div>
      <p className={cn("text-[14px] text-[#8E8E93]")}>{text}</p>
    </GlassCard>
  );
}
