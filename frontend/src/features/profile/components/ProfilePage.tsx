import { useQuery } from "@tanstack/react-query";
import {
  LogOut,
  Shield,
  Sparkles,
  Stethoscope,
} from "lucide-react";
import {
  GlassCard,
  ListGroup,
  ListRow,
  PageHeader,
  SectionHeader,
  StatusPill,
} from "../../../components/apple";
import { fetchInsurance, fetchProfile } from "../../../lib/services";
import { useAuthStore } from "../../../stores/authStore";
import { useNavigate } from "react-router-dom";

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

function parseAnthropo(content?: string | null): {
  height?: string;
  weight?: string;
  bmi?: string;
} {
  if (!content) return {};
  const h = content.match(/(\d{2,3})\s*см/i);
  const w = content.match(/(\d{2,3}(?:[.,]\d+)?)\s*кг/i);
  const b = content.match(/ИМТ\s*(\d+(?:[.,]\d+)?)/i);
  return {
    height: h?.[1],
    weight: w?.[1]?.replace(",", "."),
    bmi: b?.[1]?.replace(",", "."),
  };
}

export default function ProfilePage() {
  const clearAuth = useAuthStore((s) => s.clearAuth);
  const navigate = useNavigate();

  const profileQ = useQuery({
    queryKey: ["profile"],
    queryFn: fetchProfile,
    staleTime: 30_000,
  });
  const insQ = useQuery({
    queryKey: ["insurance"],
    queryFn: fetchInsurance,
    staleTime: 60_000,
  });

  function logout() {
    sessionStorage.removeItem("web_auth");
    clearAuth();
    navigate("/login", { replace: true });
  }

  const p = profileQ.data;
  const age = ageFromDob(p?.birth_date);
  const anthropo = parseAnthropo(p?.content);
  const initials = (p?.full_name || "СЗ")
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((x) => x[0])
    .join("")
    .toUpperCase();
  const policy = insQ.data?.policies?.[0];
  const diagnoses = p?.diagnoses ?? [];
  const allergies = p?.allergies ?? [];

  return (
    <div className="page-shell section-gap">
      <PageHeader title="Профиль" subtitle="Пациент" />

      {profileQ.isLoading && (
        <GlassCard padding="lg">
          <p className="text-[#8E8E93]">Загрузка карточки…</p>
        </GlassCard>
      )}
      {profileQ.isError && (
        <GlassCard padding="lg">
          <p className="text-[#FF3B30]">Не удалось загрузить /api/profile/</p>
        </GlassCard>
      )}

      {p && (
        <GlassCard padding="lg" className="fade-up">
          <div className="flex items-center gap-4">
            <div
              className="w-[72px] h-[72px] rounded-full flex items-center justify-center text-white text-[24px] font-semibold shrink-0"
              style={{
                background: "linear-gradient(145deg,#007AFF,#5AC8FA)",
                boxShadow: "0 8px 24px rgba(0,122,255,0.3)",
              }}
            >
              {initials}
            </div>
            <div className="min-w-0">
              <p className="text-[20px] font-semibold tracking-tight leading-tight truncate">
                {p.full_name}
              </p>
              <p className="text-[14px] text-[#8E8E93] mt-1">
                {age != null ? `${age} лет · ` : ""}
                {p.birth_date}
              </p>
              <div className="flex flex-wrap gap-1.5 mt-2">
                <StatusPill tone="info">{p.trust_tier}</StatusPill>
                {anthropo.bmi && (
                  <StatusPill tone="neutral">ИМТ {anthropo.bmi}</StatusPill>
                )}
              </div>
            </div>
          </div>

          <div className="grid grid-cols-3 gap-2 mt-5">
            <StatChip label="Рост" value={anthropo.height || "—"} unit="см" />
            <StatChip label="Вес" value={anthropo.weight || "—"} unit="кг" />
            <StatChip label="ИМТ" value={anthropo.bmi || "—"} unit="" />
          </div>
        </GlassCard>
      )}

      <section>
        <SectionHeader
          title="Диагнозы"
          action={<span className="caption">{diagnoses.length}</span>}
        />
        <div className="space-y-2.5">
          {diagnoses.map((d, i) => (
            <GlassCard key={`${d.name}-${i}`} padding="md">
              <div className="flex gap-3">
                <span className="text-[20px] leading-none mt-0.5">
                  {d.status || "•"}
                </span>
                <div className="min-w-0">
                  <p className="text-[15px] font-semibold leading-snug">{d.name}</p>
                  <p className="text-[12px] text-[#8E8E93] mt-1 leading-snug">
                    {d.source || d.date}
                  </p>
                </div>
              </div>
            </GlassCard>
          ))}
          {p && diagnoses.length === 0 && (
            <GlassCard padding="lg">
              <p className="text-[14px] text-[#8E8E93] text-center">Нет диагнозов в карточке</p>
            </GlassCard>
          )}
        </div>
      </section>

      <section>
        <SectionHeader title="Аллергии" />
        <div className="flex flex-wrap gap-2">
          {allergies.map((a) => (
            <span
              key={a}
              className="px-3 py-1.5 rounded-full bg-[#FF2D55]/10 text-[#FF2D55] text-[13px] font-medium"
            >
              {a}
            </span>
          ))}
          {p && allergies.length === 0 && (
            <p className="text-[14px] text-[#8E8E93]">Не указаны</p>
          )}
        </div>
      </section>

      {policy && (
        <section>
          <SectionHeader title="Страховка" />
          <GlassCard padding="md" className="flex items-center gap-3">
            <div className="w-11 h-11 rounded-2xl bg-[#34C759]/15 flex items-center justify-center">
              <Shield className="w-5 h-5 text-[#34C759]" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-[15px] font-semibold truncate">{policy.policy}</p>
              <p className="text-[13px] text-[#8E8E93]">
                остаток {Number(policy.remaining ?? 0).toLocaleString("ru-RU")} BYN
                {policy.expiry ? ` · до ${policy.expiry}` : ""}
              </p>
            </div>
          </GlassCard>
        </section>
      )}

      <section>
        <SectionHeader title="Разделы" />
        <ListGroup>
          <ListRow
            icon={<Sparkles className="w-4 h-4" />}
            title="Стратегия"
            onClick={() => navigate("/strategy")}
          />
          <ListRow
            icon={<Stethoscope className="w-4 h-4" />}
            title="Чекапы"
            onClick={() => navigate("/checkups")}
          />
        </ListGroup>
      </section>

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

function StatChip({
  label,
  value,
  unit,
}: {
  label: string;
  value: string;
  unit: string;
}) {
  return (
    <div className="rounded-2xl bg-black/[0.04] px-2 py-2.5 text-center">
      <p className="text-[11px] font-semibold text-[#8E8E93] uppercase">{label}</p>
      <p className="text-[17px] font-semibold tabular-nums mt-0.5">
        {value}
        {unit ? (
          <span className="text-[11px] font-medium text-[#8E8E93] ml-0.5">{unit}</span>
        ) : null}
      </p>
    </div>
  );
}
