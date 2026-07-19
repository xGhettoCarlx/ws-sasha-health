import {
  Activity,
  ChevronRight,
  Heart,
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
import {
  mockAllergies,
  mockDiagnoses,
  mockFluorography,
  mockInsurance,
  mockPatient,
} from "../../../lib/mock-data";
import { useAuthStore } from "../../../stores/authStore";
import { useNavigate } from "react-router-dom";

export default function ProfilePage() {
  const clearAuth = useAuthStore((s) => s.clearAuth);
  const navigate = useNavigate();

  function logout() {
    sessionStorage.removeItem("web_auth");
    clearAuth();
    navigate("/login", { replace: true });
  }

  return (
    <div className="page-shell section-gap">
      <PageHeader title="Профиль" subtitle="Пациент" />

      {/* Identity card */}
      <GlassCard padding="lg" className="fade-up">
        <div className="flex items-center gap-4">
          <div
            className="w-[72px] h-[72px] rounded-full flex items-center justify-center text-white text-[24px] font-semibold shrink-0"
            style={{
              background: "linear-gradient(145deg,#007AFF,#5AC8FA)",
              boxShadow: "0 8px 24px rgba(0,122,255,0.3)",
            }}
          >
            {mockPatient.avatar_initials}
          </div>
          <div className="min-w-0">
            <p className="text-[20px] font-semibold tracking-tight leading-tight truncate">
              {mockPatient.full_name}
            </p>
            <p className="text-[14px] text-[#8E8E93] mt-1">
              {mockPatient.age} лет · {mockPatient.birth_date}
            </p>
            <div className="flex flex-wrap gap-1.5 mt-2">
              <StatusPill tone="info">{mockPatient.blood_type}</StatusPill>
              <StatusPill tone="neutral">ИМТ {mockPatient.bmi}</StatusPill>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-3 gap-2 mt-5">
          <StatChip label="Рост" value={`${mockPatient.height_cm}`} unit="см" />
          <StatChip label="Вес" value={`${mockPatient.weight_kg}`} unit="кг" />
          <StatChip label="ИМТ" value={`${mockPatient.bmi}`} unit="" />
        </div>
      </GlassCard>

      {/* Diagnoses */}
      <section>
        <SectionHeader
          title="Диагнозы"
          action={<span className="caption">{mockDiagnoses.length}</span>}
        />
        <div className="space-y-2.5">
          {mockDiagnoses.map((d) => (
            <GlassCard key={d.id} padding="md" pressable>
              <div className="flex gap-3">
                <span className="text-[20px] leading-none mt-0.5">{d.statusEmoji}</span>
                <div className="min-w-0">
                  <p className="text-[15px] font-semibold leading-snug">{d.name}</p>
                  <p className="text-[12px] text-[#8E8E93] mt-1 leading-snug">{d.source}</p>
                </div>
              </div>
            </GlassCard>
          ))}
        </div>
      </section>

      {/* Allergies */}
      <section>
        <SectionHeader title="Аллергии" />
        <div className="flex flex-wrap gap-2">
          {mockAllergies.map((a) => (
            <span
              key={a}
              className="px-3.5 py-2 rounded-full bg-[#FFEBEA] text-[#D70015] text-[13px] font-semibold"
            >
              {a}
            </span>
          ))}
        </div>
      </section>

      {/* Insurance + fluoro */}
      <section>
        <SectionHeader title="Документы" />
        <ListGroup>
          <ListRow
            icon={<Shield className="w-4 h-4" />}
            iconBg="#34C759"
            title="Страховка ДМС"
            subtitle={mockInsurance.policy}
            detail={`${Math.round((mockInsurance.remaining / mockInsurance.sum_insured) * 100)}%`}
            onClick={() => {}}
          />
          <ListRow
            icon={<Stethoscope className="w-4 h-4" />}
            iconBg="#5AC8FA"
            title="Флюорография"
            subtitle={`${mockFluorography.last_date} · ${mockFluorography.result}`}
            detail="OK"
            onClick={() => {}}
          />
          <ListRow
            icon={<Activity className="w-4 h-4" />}
            iconBg="#FF2D55"
            title="HealthKit / метрики"
            subtitle="Синхронизация (скоро)"
            showChevron
            onClick={() => {}}
          />
        </ListGroup>
      </section>

      {/* Insurance card visual */}
      <GlassCard
        padding="lg"
        className="text-white overflow-hidden relative"
        style={{
          background: "linear-gradient(135deg, #1C1C1E 0%, #3A3A3C 50%, #007AFF 160%)",
        }}
      >
        <div className="absolute -right-6 -top-6 w-32 h-32 rounded-full bg-white/10" />
        <div className="absolute right-8 bottom-4 w-20 h-20 rounded-full bg-[#007AFF]/30 blur-xl" />
        <div className="relative">
          <div className="flex items-center justify-between mb-6">
            <p className="text-[13px] font-semibold text-white/70 uppercase tracking-wider">
              {mockInsurance.insurer}
            </p>
            <Heart className="w-5 h-5 text-[#FF2D55]" fill="#FF2D55" />
          </div>
          <p className="text-[15px] font-medium text-white/90 mb-1">{mockInsurance.policy}</p>
          <p className="metric-value text-[28px] mt-3">
            {new Intl.NumberFormat("ru-RU", {
              style: "currency",
              currency: "BYN",
              maximumFractionDigits: 0,
            }).format(mockInsurance.remaining)}
          </p>
          <p className="text-[13px] text-white/60 mt-1">
            остаток · до {mockInsurance.expiry}
          </p>
          <div className="mt-4 h-1.5 rounded-full bg-white/15 overflow-hidden">
            <div
              className="h-full rounded-full bg-gradient-to-r from-[#34C759] to-[#5AC8FA]"
              style={{
                width: `${(mockInsurance.remaining / mockInsurance.sum_insured) * 100}%`,
              }}
            />
          </div>
        </div>
      </GlassCard>

      <ListGroup>
        <ListRow
          icon={<Sparkles className="w-4 h-4" />}
          iconBg="#AF52DE"
          title="О приложении"
          subtitle="Sasha Health · Apple HIG prototype"
          showChevron={false}
        />
        <button
          type="button"
          onClick={logout}
          className="w-full flex items-center gap-3 px-4 py-3.5 pressable text-left"
        >
          <span className="w-8 h-8 rounded-[9px] bg-[#FF3B30] flex items-center justify-center text-white">
            <LogOut className="w-4 h-4" />
          </span>
          <span className="flex-1 text-[16px] text-[#FF3B30] font-medium">Выйти из демо</span>
          <ChevronRight className="w-4 h-4 text-[#C7C7CC]" />
        </button>
      </ListGroup>
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
    <div className="rounded-[14px] bg-[#F2F2F7] px-3 py-2.5 text-center">
      <p className="text-[11px] font-semibold text-[#8E8E93] uppercase tracking-wide">
        {label}
      </p>
      <p className="metric-value text-[18px] mt-0.5">
        {value}
        {unit && <span className="text-[11px] font-medium text-[#8E8E93] ml-0.5">{unit}</span>}
      </p>
    </div>
  );
}
