/**
 * DMS Insurance workspace — policy limits + covered/excluded + Trojan Horse.
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
const COVERED_GROUPS: { title: string; items: string[] }[] = [
  {
    title: "Консультации",
    items: [
      "Все специалисты (кроме диетолога, сомнолога, трихолога, косметолога, психиатра, нарколога, мануального терапевта, стоматолога-ортопеда/ортодонта/имплантолога)",
      "Высоковостребованные (>70 BYN) — франшиза 40%",
      "Гинеколог — до 5 раз; уролог — до 5 раз",
    ],
  },
  {
    title: "Диагностика",
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
    items: [
      "Малые операции (в гос.)",
      "Уколы / блокады — до 10",
      "Массаж — 10 сеансов, физиотерапия",
      "Экстренная стоматология — 1 раз",
    ],
  },
];

const NOT_COVERED: string[] = [
  "Лекарства, БАДы, витамины",
  "Плановая стоматология, протезирование, имплантация",
  "Онкология, ВИЧ, гепатиты B/C, туберкулёз, диабет 1 типа, психиатрия",
  "Беременность, роды",
  "Капельницы, мануальная терапия, остеопатия",
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

  /** Compact: coverage lists collapsed by default; Trojan open near top */
  const [openCovered, setOpenCovered] = useState(false);
  const [openExcluded, setOpenExcluded] = useState(false);
  const [openTrojan, setOpenTrojan] = useState(true);

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
        Полис, покрытие и Троянский конь для аппрува чекапов
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
              {meta.source && (
                <p className="text-[11px] text-[#AEAEB2] leading-snug">{meta.source}</p>
              )}
            </div>
          )}
        </div>
      </GlassCard>

      {/* Trojan Horse — top, right under policy limits */}
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
          Выбери направление — реальные жалобы + формулировки для аппрува чекапа
        </p>
        {openTrojan && <TrojanHorsePanel />}
      </section>

      {/* Covered — collapsed by default */}
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
          <div className="space-y-2">
            {COVERED_GROUPS.map((g) => (
              <GlassCard key={g.title} padding="md">
                <p className="text-[14px] font-semibold mb-2 flex items-center gap-1.5">
                  <CheckCircle2 className="w-4 h-4 text-[#34C759]" />
                  {g.title}
                </p>
                <ul className="space-y-1.5">
                  {g.items.map((item) => (
                    <li
                      key={item}
                      className="text-[13px] text-[#1C1C1E]/90 leading-snug pl-1 flex gap-2"
                    >
                      <span className="text-[#34C759] shrink-0">•</span>
                      <span>{item}</span>
                    </li>
                  ))}
                </ul>
              </GlassCard>
            ))}
          </div>
        )}
      </section>

      {/* Not covered — collapsed by default */}
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
          <GlassCard padding="md">
            <ul className="space-y-2">
              {NOT_COVERED.map((item) => (
                <li
                  key={item}
                  className="text-[13px] leading-snug flex gap-2 items-start"
                >
                  <XCircle className="w-4 h-4 text-[#FF3B30] shrink-0 mt-0.5" />
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          </GlassCard>
        )}
      </section>

      {/* Contacts */}
      <section>
        <SectionHeader title="Контакты БГС" />
        <div className="space-y-2">
          <a href="tel:+375222713071" className="block">
            <GlassCard padding="md" pressable className="flex items-center gap-3">
              <Phone className="w-5 h-5 text-[#007AFF]" />
              <div>
                <p className="text-[15px] font-medium">+375 222 71 30 71</p>
                <p className="text-[12px] text-[#8E8E93]">Телефон</p>
              </div>
            </GlassCard>
          </a>
          <a href="mailto:dms.mogilev@bgs.by" className="block">
            <GlassCard padding="md" pressable className="flex items-center gap-3">
              <Mail className="w-5 h-5 text-[#007AFF]" />
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
