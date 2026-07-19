import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ChevronRight,
  ClipboardList,
  Coins,
  Shield,
  Sparkles,
  Stethoscope,
} from "lucide-react";
import {
  GlassCard,
  PageHeader,
  SectionHeader,
  StatusPill,
} from "../../../components/apple";
import { fetchOverview, postVital } from "../../../lib/navigator-api";

export function DashboardPage() {
  const qc = useQueryClient();
  const { data, isLoading, isError } = useQuery({
    queryKey: ["overview"],
    queryFn: fetchOverview,
    staleTime: 30_000,
  });

  const [sys, setSys] = useState("");
  const [dia, setDia] = useState("");
  const [weight, setWeight] = useState("");
  const [when, setWhen] = useState<"morning" | "evening" | "other">("morning");
  const [msg, setMsg] = useState<string | null>(null);

  const saveVital = useMutation({
    mutationFn: postVital,
    onSuccess: () => {
      setMsg("Сохранено");
      setSys("");
      setDia("");
      setWeight("");
      qc.invalidateQueries({ queryKey: ["overview"] });
      qc.invalidateQueries({ queryKey: ["vitals"] });
      setTimeout(() => setMsg(null), 2000);
    },
    onError: (e: Error) => setMsg(e.message || "Ошибка сохранения"),
  });

  const greeting = useMemo(() => {
    const h = new Date().getHours();
    if (h < 12) return "Доброе утро";
    if (h < 18) return "Добрый день";
    return "Добрый вечер";
  }, []);

  const onSave = () => {
    const payload: { bp?: string; weight_kg?: number; when?: string } = { when };
    if (sys && dia) payload.bp = `${sys}/${dia}`;
    if (weight) payload.weight_kg = Number(weight.replace(",", "."));
    if (!payload.bp && payload.weight_kg == null) {
      setMsg("Введите давление и/или вес");
      return;
    }
    saveVital.mutate(payload);
  };

  if (isLoading) {
    return (
      <div className="page-shell section-gap">
        <PageHeader subtitle={greeting} title="…" />
        <GlassCard padding="lg">
          <p className="text-[15px] text-[#8E8E93]">Загрузка реальных данных…</p>
        </GlassCard>
      </div>
    );
  }

  if (isError || !data) {
    return (
      <div className="page-shell section-gap">
        <PageHeader subtitle={greeting} title="Медик" />
        <GlassCard padding="lg">
          <p className="text-[15px] text-[#FF3B30] font-medium">
            Не удалось загрузить данные API
          </p>
          <p className="text-[13px] text-[#8E8E93] mt-2">
            Запустите FastAPI (`uvicorn app.main:app`) и откройте через `/sh/`.
          </p>
        </GlassCard>
      </div>
    );
  }

  return (
    <div className="page-shell section-gap">
      <PageHeader
        subtitle={greeting}
        title={data.patient.short_name || "Саша"}
      />

      <p className="text-[13px] text-[#8E8E93] -mt-2 leading-relaxed">
        {data.patient.summary_line || "Мед-навигатор · реальные файлы агента"}
      </p>

      {/* BP + Weight only */}
      <section>
        <SectionHeader title="Контроль" action={<span className="caption">АД · вес</span>} />
        <div className="grid grid-cols-2 gap-3">
          <MetricTile
            label="Давление"
            value={data.vitals.last_bp?.bp || "—"}
            unit="мм рт.ст."
            accent="#FF2D55"
            meta={data.vitals.last_bp?.date ? `замер ${data.vitals.last_bp.date}` : "нет записей"}
          />
          <MetricTile
            label="Вес"
            value={
              data.vitals.last_weight?.weight_kg != null
                ? String(data.vitals.last_weight.weight_kg)
                : "—"
            }
            unit="кг"
            accent="#34C759"
            meta={
              data.vitals.last_weight?.date
                ? `замер ${data.vitals.last_weight.date}`
                : data.vitals.last_weight?.source || "из карточки"
            }
          />
        </div>
      </section>

      {/* Input form */}
      <GlassCard padding="lg">
        <p className="text-[15px] font-semibold mb-3">Новый замер</p>
        <div className="flex gap-2 mb-3">
          {(["morning", "evening", "other"] as const).map((w) => (
            <button
              key={w}
              type="button"
              onClick={() => setWhen(w)}
              className={`flex-1 h-9 rounded-full text-[13px] font-medium pressable ${
                when === w
                  ? "bg-[#007AFF] text-white"
                  : "bg-black/5 text-[#1C1C1E]"
              }`}
            >
              {w === "morning" ? "Утро" : w === "evening" ? "Вечер" : "Другое"}
            </button>
          ))}
        </div>
        <div className="grid grid-cols-3 gap-2 mb-3">
          <input
            inputMode="numeric"
            placeholder="Сис"
            value={sys}
            onChange={(e) => setSys(e.target.value.replace(/\D/g, "").slice(0, 3))}
            className="h-11 rounded-2xl bg-black/[0.04] px-3 text-[16px] text-center outline-none focus:ring-2 focus:ring-[#007AFF]/40"
          />
          <input
            inputMode="numeric"
            placeholder="Диа"
            value={dia}
            onChange={(e) => setDia(e.target.value.replace(/\D/g, "").slice(0, 3))}
            className="h-11 rounded-2xl bg-black/[0.04] px-3 text-[16px] text-center outline-none focus:ring-2 focus:ring-[#007AFF]/40"
          />
          <input
            inputMode="decimal"
            placeholder="Вес"
            value={weight}
            onChange={(e) => setWeight(e.target.value)}
            className="h-11 rounded-2xl bg-black/[0.04] px-3 text-[16px] text-center outline-none focus:ring-2 focus:ring-[#007AFF]/40"
          />
        </div>
        <button
          type="button"
          onClick={onSave}
          disabled={saveVital.isPending}
          className="w-full h-11 rounded-2xl bg-[#007AFF] text-white font-semibold text-[15px] pressable disabled:opacity-50"
        >
          {saveVital.isPending ? "Сохраняю…" : "Сохранить"}
        </button>
        {msg && (
          <p className="text-[13px] text-center mt-2 text-[#8E8E93]">{msg}</p>
        )}
      </GlassCard>

      {/* Hub cards */}
      <section className="space-y-3">
        <HubRow
          to="/checkups"
          icon={<ClipboardList className="w-4 h-4" />}
          iconBg="#FF9500"
          title="Чекапы"
          detail={
            data.checkups.overdue
              ? `${data.checkups.overdue} пора сделать`
              : `${data.checkups.total} в трекере`
          }
          badge={data.checkups.overdue ? "срочно" : undefined}
        />
        <HubRow
          to="/complaints"
          icon={<Coins className="w-4 h-4" />}
          iconBg="#AF52DE"
          title="Копилка жалоб"
          detail={`${data.complaints_open} открытых`}
        />
        <HubRow
          to="/navigator"
          icon={<Stethoscope className="w-4 h-4" />}
          iconBg="#007AFF"
          title="Навигатор"
          detail="Симптом → врач → страховка"
        />
        <HubRow
          to="/previsit"
          icon={<Sparkles className="w-4 h-4" />}
          iconBg="#5AC8FA"
          title="Pre-Visit"
          detail="Промпт для Gemini"
        />
      </section>

      {/* Insurance strip */}
      {data.insurance && (
        <section>
          <SectionHeader title="Страховка" />
          <GlassCard padding="md" className="flex items-center gap-3">
            <div className="w-11 h-11 rounded-2xl bg-[#34C759]/15 flex items-center justify-center">
              <Shield className="w-5 h-5 text-[#34C759]" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-[15px] font-semibold truncate">
                {(data.insurance as { policy?: string }).policy || "ДМС"}
              </p>
              <p className="text-[13px] text-[#8E8E93]">
                остаток{" "}
                {Number(
                  (data.insurance as { remaining?: number }).remaining ?? 0,
                ).toLocaleString("ru-RU")}{" "}
                BYN
                {(data.insurance as { expiry?: string }).expiry
                  ? ` · до ${(data.insurance as { expiry?: string }).expiry}`
                  : ""}
              </p>
            </div>
            <Link to="/navigator">
              <ChevronRight className="w-5 h-5 text-[#C7C7CC]" />
            </Link>
          </GlassCard>
        </section>
      )}

      {/* Active diagnoses preview */}
      {data.patient.diagnoses?.length > 0 && (
        <section>
          <SectionHeader
            title="Активные"
            action={
              <Link to="/records" className="caption text-[#007AFF]">
                карта
              </Link>
            }
          />
          <GlassCard padding="none">
            {data.patient.diagnoses.slice(0, 4).map((d, i) => (
              <div key={i}>
                {i > 0 && <div className="hairline ml-4" />}
                <div className="px-4 py-3 flex items-start gap-3">
                  <span className="text-[16px] leading-none mt-0.5">
                    {(d as { status?: string }).status || "•"}
                  </span>
                  <div className="min-w-0">
                    <p className="text-[15px] font-medium leading-snug">
                      {(d as { name?: string }).name}
                    </p>
                    <p className="text-[12px] text-[#8E8E93] mt-0.5">
                      {(d as { date?: string }).date}
                    </p>
                  </div>
                </div>
              </div>
            ))}
          </GlassCard>
        </section>
      )}

      <p className="text-[11px] text-[#AEAEB2] text-center px-4 pb-2 leading-relaxed">
        {data.disclaimer}
      </p>
    </div>
  );
}

function MetricTile({
  label,
  value,
  unit,
  accent,
  meta,
}: {
  label: string;
  value: string;
  unit: string;
  accent: string;
  meta: string;
}) {
  return (
    <GlassCard padding="md">
      <div className="flex items-center gap-2 mb-2">
        <span
          className="w-2 h-2 rounded-full"
          style={{ background: accent }}
        />
        <p className="text-[12px] font-semibold text-[#8E8E93] uppercase tracking-wide">
          {label}
        </p>
      </div>
      <p className="text-[28px] font-semibold tracking-tight leading-none text-[#1C1C1E]">
        {value}
      </p>
      <p className="text-[12px] text-[#8E8E93] mt-1">{unit}</p>
      <p className="text-[11px] text-[#AEAEB2] mt-2">{meta}</p>
    </GlassCard>
  );
}

function HubRow({
  to,
  icon,
  iconBg,
  title,
  detail,
  badge,
}: {
  to: string;
  icon: React.ReactNode;
  iconBg: string;
  title: string;
  detail: string;
  badge?: string;
}) {
  return (
    <Link to={to}>
      <GlassCard padding="md" pressable className="flex items-center gap-3">
        <div
          className="w-10 h-10 rounded-[12px] flex items-center justify-center text-white shrink-0"
          style={{ background: iconBg }}
        >
          {icon}
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-[16px] font-semibold">{title}</p>
          <p className="text-[13px] text-[#8E8E93] truncate">{detail}</p>
        </div>
        {badge && <StatusPill tone="warn">{badge}</StatusPill>}
        <ChevronRight className="w-5 h-5 text-[#C7C7CC]" />
      </GlassCard>
    </Link>
  );
}

