/**
 * DMS Insurance workspace — policy + coverage tiles/accordions + Trojan Horse.
 * Data: /api/insurance/ ← data/страховка.md
 */
import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  CheckCircle2,
  ChevronDown,
  Mail,
  Phone,
  Shield,
  XCircle,
} from "lucide-react";
import {
  GlassCard,
  PageHeader,
  SectionHeader,
  StatusPill,
} from "../../../components/apple";
import { fetchInsurance } from "../../../lib/services";
import type { InsurancePolicy, InsuranceSchema } from "../../../lib/types";
import { TrojanHorsePanel } from "../../trojan/components/TrojanHorsePanel";
import { cn } from "../../../lib/utils";

/** Belgosstrakh АВгос+ком — structured from страховка.md body */
const COVERED_GROUPS: { title: string; items: string[]; glyph: string }[] = [
  {
    title: "Консультации",
    glyph: "🩺",
    items: [
      "Все специалисты (кроме диетолога, сомнолога, трихолога, косметолога, психиатра, нарколога, мануального терапевта, стоматолога-ортопеда/ортодонта/имплантолога)",
      "Высоковостребованные (>70 BYN) — франшиза 40%",
      "Гинеколог — до 5 раз; уролог — до 5 раз",
    ],
  },
  {
    title: "Диагностика",
    glyph: "🔬",
    items: [
      "Лаборатории: Хеликс, Инвитро, Синлаб-ЕМЛ, гос.",
      "УЗИ — без ограничений",
      "КТ — 1 раз за период",
      "МРТ — 1 раз за период",
      "ФГДС/ФКС — 2 раза в совокупности",
    ],
  },
  {
    title: "Лечение",
    glyph: "💊",
    items: [
      "Малые операции (в гос.)",
      "Уколы / блокады — до 10",
      "Массаж — 10 сеансов, физиотерапия",
      "Экстренная стоматология — 1 раз",
    ],
  },
];

const NOT_COVERED: { title: string; detail: string }[] = [
  {
    title: "Лекарства",
    detail: "Лекарства, БАДы, витамины — вне полиса",
  },
  {
    title: "Стоматология",
    detail: "Плановая, протезирование, имплантация — нет",
  },
  {
    title: "Хронические / тяжёлые",
    detail: "Онкология, ВИЧ, гепатиты B/C, туберкулёз, диабет 1 типа, психиатрия",
  },
  {
    title: "Беременность",
    detail: "Беременность и роды не покрываются",
  },
  {
    title: "Процедуры",
    detail: "Капельницы, мануальная терапия, остеопатия",
  },
];

function money(n: number | undefined | null): string {
  return Number(n ?? 0).toLocaleString("ru-RU", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  });
}

function policyFromSchema(data: InsuranceSchema | undefined): InsurancePolicy | null {
  if (!data) return null;
  const p = data.policies?.[0];
  if (!p) return null;
  return p;
}

export default function InsurancePage() {
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["insurance"],
    queryFn: fetchInsurance,
    staleTime: 60_000,
  });

  const [openCovered, setOpenCovered] = useState(false);
  const [openExcluded, setOpenExcluded] = useState(false);
  const [openTrojan, setOpenTrojan] = useState(true);
  /** Accordion: which covered group tile is expanded */
  const [openCoveredGroup, setOpenCoveredGroup] = useState<string | null>(null);
  /** Accordion: which excluded tile is expanded */
  const [openExcludedItem, setOpenExcludedItem] = useState<string | null>(null);

  const policy = policyFromSchema(data);
  const sum = policy?.sum_insured ?? 0;
  const remaining = policy?.remaining ?? 0;
  const spent = policy?.spent ?? Math.max(0, sum - remaining);
  const usedPct = sum > 0 ? Math.min(100, Math.round((spent / sum) * 100)) : 0;
  const expiry = policy?.expiry || "—";
  const active =
    expiry !== "—" && !Number.isNaN(Date.parse(expiry))
      ? new Date(expiry) > new Date()
      : true;

  const meta = useMemo(() => {
    const src = data?.source || "";
    const contract = src.match(/№\s*([^\s]+)/)?.[1] || "";
    return {
      contract,
      source: src,
      program:
        (policy as InsurancePolicy & { program?: string })?.program ||
        "АВгос+ком",
      insurer:
        (policy as InsurancePolicy & { insurer?: string })?.insurer ||
        "Белгосстрах",
      holder:
        (policy as InsurancePolicy & { policyholder?: string })?.policyholder ||
        "",
      premium: (policy as InsurancePolicy & { premium?: number })?.premium,
    };
  }, [data, policy]);

  if (isLoading) {
    return (
      <div className="page-shell section-gap">
        <PageHeader subtitle="ДМС" title="Страховка" />
        <GlassCard padding="lg">
          <p className="text-[#8E8E93]">Загрузка полиса…</p>
        </GlassCard>
      </div>
    );
  }

  if (isError || !data) {
    return (
      <div className="page-shell section-gap">
        <PageHeader subtitle="ДМС" title="Страховка" />
        <GlassCard padding="lg">
          <p className="text-[#FF3B30]">Не удалось загрузить /api/insurance/</p>
          <button
            type="button"
            onClick={() => refetch()}
            className="mt-3 text-[14px] text-[#007AFF] font-medium"
          >
            Повторить
          </button>
        </GlassCard>
      </div>
    );
  }

  return (
    <div className="page-shell section-gap">
      <PageHeader subtitle="Белгосстрах · ДМС" title="Страховка" />
      <p className="text-[13px] text-[#8E8E93] -mt-2 leading-relaxed">
        Полис, покрытие плиткой и Троянский конь — база для PDF-промпта
      </p>

      {/* Hero policy card */}
      <GlassCard padding="lg" className="relative overflow-hidden">
        <div
          className="absolute inset-0 opacity-90 pointer-events-none"
          style={{
            background:
              "radial-gradient(120% 80% at 0% 0%, rgba(52,199,89,0.18), transparent 55%), radial-gradient(80% 60% at 100% 100%, rgba(0,122,255,0.08), transparent 50%)",
          }}
        />
        <div className="relative">
          <div className="flex items-start justify-between gap-2 mb-3">
            <div className="flex items-center gap-2">
              <div className="w-11 h-11 rounded-2xl bg-[#34C759]/20 flex items-center justify-center">
                <Shield className="w-5 h-5 text-[#34C759]" />
              </div>
              <div>
                <p className="text-[17px] font-semibold">
                  {policy?.policy || "ДМС"}
                </p>
                <p className="text-[12px] text-[#8E8E93]">
                  {meta.insurer} · {meta.program}
                </p>
              </div>
            </div>
            <StatusPill tone={active ? "ok" : "danger"}>
              {active ? "активен" : "истёк"}
            </StatusPill>
          </div>

          <div className="grid grid-cols-2 gap-3 mb-3">
            <div>
              <p className="text-[11px] font-semibold text-[#8E8E93] uppercase">
                Лимит
              </p>
              <p className="text-[20px] font-semibold tabular-nums">
                {money(sum)}{" "}
                <span className="text-[13px] font-medium text-[#8E8E93]">BYN</span>
              </p>
            </div>
            <div>
              <p className="text-[11px] font-semibold text-[#8E8E93] uppercase">
                Остаток
              </p>
              <p className="text-[20px] font-semibold tabular-nums text-[#34C759]">
                {money(remaining)}{" "}
                <span className="text-[13px] font-medium text-[#8E8E93]">BYN</span>
              </p>
            </div>
          </div>

          <div className="h-2 rounded-full bg-black/5 overflow-hidden mb-2">
            <div
              className="h-full rounded-full bg-[#34C759]"
              style={{ width: `${100 - usedPct}%` }}
            />
          </div>
          <p className="text-[12px] text-[#8E8E93]">
            Израсходовано {money(spent)} BYN ({usedPct}%) · срок до{" "}
            <span className="font-medium text-[#1C1C1E]">{expiry}</span>
          </p>

          {(meta.contract || meta.holder || meta.premium != null) && (
            <div className="mt-3 pt-3 border-t border-black/5 space-y-1">
              {meta.contract && (
                <p className="text-[12px] text-[#8E8E93]">
                  Договор № <span className="text-[#1C1C1E]">{meta.contract}</span>
                </p>
              )}
              {meta.holder && (
                <p className="text-[12px] text-[#8E8E93]">
                  Страхователь:{" "}
                  <span className="text-[#1C1C1E]">{meta.holder}</span>
                </p>
              )}
              {meta.premium != null && (
                <p className="text-[12px] text-[#8E8E93]">
                  Взнос:{" "}
                  <span className="text-[#1C1C1E]">{money(meta.premium)} BYN</span>
                </p>
              )}
            </div>
          )}
        </div>
      </GlassCard>

      {/* Trojan Horse */}
      <section>
        <button
          type="button"
          onClick={() => setOpenTrojan((v) => !v)}
          className="w-full flex items-center justify-between px-0.5 mb-2 pressable"
        >
          <SectionHeader title="Троянский конь" />
          <ChevronDown
            className={cn(
              "w-5 h-5 text-[#8E8E93] transition-transform",
              openTrojan && "rotate-180",
            )}
          />
        </button>
        <p className="text-[12px] text-[#8E8E93] mb-2 px-0.5">
          База формулировок для PDF-промпта врачу (без отдельных кнопок Сохранить/Скрипт)
        </p>
        {openTrojan && <TrojanHorsePanel />}
      </section>

      {/* Covered — tile grid + accordion detail */}
      <section>
        <button
          type="button"
          onClick={() => setOpenCovered((v) => !v)}
          className="w-full flex items-center justify-between px-0.5 mb-2 pressable"
        >
          <SectionHeader title="Что покрывается ДМС" />
          <ChevronDown
            className={cn(
              "w-5 h-5 text-[#8E8E93] transition-transform",
              openCovered && "rotate-180",
            )}
          />
        </button>
        {openCovered && (
          <div className="grid grid-cols-1 gap-2">
            {COVERED_GROUPS.map((g) => {
              const open = openCoveredGroup === g.title;
              return (
                <div key={g.title}>
                  <button
                    type="button"
                    onClick={() =>
                      setOpenCoveredGroup((cur) =>
                        cur === g.title ? null : g.title,
                      )
                    }
                    className={cn(
                      "w-full text-left rounded-2xl px-3.5 py-3 pressable border flex items-center gap-3",
                      open
                        ? "bg-[#34C759]/12 border-[#34C759]/35"
                        : "bg-white border-transparent shadow-[var(--shadow-card)]",
                    )}
                  >
                    <span className="text-[22px] leading-none">{g.glyph}</span>
                    <div className="flex-1 min-w-0">
                      <p className="text-[15px] font-semibold flex items-center gap-1.5">
                        <CheckCircle2 className="w-4 h-4 text-[#34C759]" />
                        {g.title}
                      </p>
                      <p className="text-[12px] text-[#8E8E93] mt-0.5">
                        {g.items.length} пункта · нажми для деталей
                      </p>
                    </div>
                    <ChevronDown
                      className={cn(
                        "w-4 h-4 text-[#C7C7CC] shrink-0 transition-transform",
                        open && "rotate-180",
                      )}
                    />
                  </button>
                  {open && (
                    <div className="mt-1.5 ml-2 pl-3 border-l-2 border-[#34C759]/30 space-y-1.5 py-1">
                      {g.items.map((item) => (
                        <p
                          key={item}
                          className="text-[13px] text-[#1C1C1E]/90 leading-snug"
                        >
                          {item}
                        </p>
                      ))}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </section>

      {/* Not covered — rectangular tiles + accordion */}
      <section>
        <button
          type="button"
          onClick={() => setOpenExcluded((v) => !v)}
          className="w-full flex items-center justify-between px-0.5 mb-2 pressable"
        >
          <SectionHeader title="Что не покрывается" />
          <ChevronDown
            className={cn(
              "w-5 h-5 text-[#8E8E93] transition-transform",
              openExcluded && "rotate-180",
            )}
          />
        </button>
        {openExcluded && (
          <div className="grid grid-cols-2 gap-2">
            {NOT_COVERED.map((item) => {
              const open = openExcludedItem === item.title;
              return (
                <button
                  key={item.title}
                  type="button"
                  onClick={() =>
                    setOpenExcludedItem((cur) =>
                      cur === item.title ? null : item.title,
                    )
                  }
                  className={cn(
                    "text-left rounded-2xl px-3 py-3 pressable border min-h-[72px]",
                    open
                      ? "bg-[#FF3B30]/10 border-[#FF3B30]/30 col-span-2"
                      : "bg-white border-transparent shadow-[var(--shadow-card)]",
                  )}
                >
                  <p className="text-[13px] font-semibold flex items-center gap-1.5">
                    <XCircle className="w-3.5 h-3.5 text-[#FF3B30] shrink-0" />
                    {item.title}
                  </p>
                  {open && (
                    <p className="text-[12px] text-[#8E8E93] mt-1.5 leading-snug">
                      {item.detail}
                    </p>
                  )}
                </button>
              );
            })}
          </div>
        )}
      </section>

      {/* Contacts */}
      <section>
        <SectionHeader title="Контакты БГС" />
        <div className="grid grid-cols-1 gap-2">
          <a href="tel:+375222713071" className="block">
            <GlassCard padding="md" pressable className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-2xl bg-[#007AFF]/12 flex items-center justify-center">
                <Phone className="w-5 h-5 text-[#007AFF]" />
              </div>
              <div>
                <p className="text-[15px] font-medium">+375 222 71 30 71</p>
                <p className="text-[12px] text-[#8E8E93]">Телефон</p>
              </div>
            </GlassCard>
          </a>
          <a href="mailto:dms.mogilev@bgs.by" className="block">
            <GlassCard padding="md" pressable className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-2xl bg-[#007AFF]/12 flex items-center justify-center">
                <Mail className="w-5 h-5 text-[#007AFF]" />
              </div>
              <div>
                <p className="text-[15px] font-medium">dms.mogilev@bgs.by</p>
                <p className="text-[12px] text-[#8E8E93]">Email · Могилёв</p>
              </div>
            </GlassCard>
          </a>
        </div>
      </section>
    </div>
  );
}
