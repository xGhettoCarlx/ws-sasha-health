import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import {
  Shield, CheckCircle, XCircle, Activity,
  Stethoscope, Syringe, Scan, FlaskConical, Phone,
} from "lucide-react";
import { PageSkeleton } from "../../../components/ui/PageSkeleton";
import { ErrorState } from "../../../components/ErrorState";
import TelegramBackButton from "../../../components/TelegramBackButton";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "../../../components/ui/dialog";
import { fetchInsurance } from "../../../lib/services";
import type { InsuranceSchema } from "../../../lib/types";

type PageState = "loading" | "error" | "data";

// Hardcoded contract limits from страховка.md
interface LimitItem {
  icon: typeof Shield;
  label: string;
  used: number;
  total: number;
}

const STRICT_LIMITS: LimitItem[] = [
  { icon: Scan, label: "МРТ / КТ", used: 0, total: 1 },
  { icon: Stethoscope, label: "Эндоскопия (ФГДС/ФКС)", used: 0, total: 2 },
  { icon: Syringe, label: "Уколы / блокады", used: 0, total: 10 },
  { icon: Activity, label: "Экстр. стоматология", used: 0, total: 1 },
];

const UNLIMITED_ITEMS = [
  { icon: Stethoscope, label: "Консультации всех специалистов" },
  { icon: FlaskConical, label: "Лаборатории (Хеликс, Инвитро, Синлаб)" },
  { icon: Activity, label: "УЗИ — без ограничений" },
];

const EXCLUDED_ITEMS = [
  "Лекарства, БАДы, витамины",
  "Плановая стоматология, протезирование",
];

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString("ru-RU", {
    day: "numeric",
    month: "long",
    year: "numeric",
  });
}


// ─── Modal Component ─────────────────────────────────────────────────────────

interface InsuranceModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function InsuranceModal({ open, onOpenChange }: InsuranceModalProps) {
  const [state, setState] = useState<PageState>("loading");
  const [data, setData] = useState<InsuranceSchema | null>(null);
  const [errorMessage, setErrorMessage] = useState<string>("");

  const loadData = async () => {
    setState("loading");
    setErrorMessage("");
    try {
      const result = await fetchInsurance();
      setData(result);
      setState("data");
    } catch (err) {
      setErrorMessage(
        err instanceof Error ? err.message : "Не удалось загрузить данные страховки",
      );
      setState("error");
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const policy = data?.policies?.[0];
  const totalSum = policy?.sum_insured ?? 37651.83;
  const expiry = policy?.expiry ?? "2027-01-24";
  const isActive = new Date(expiry) > new Date();

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-[#1F2937]">
            <Shield className="h-5 w-5" />
            Страховка
          </DialogTitle>
        </DialogHeader>

        {state === "loading" && <div className="py-8"><PageSkeleton variant="detail" /></div>}

        {state === "error" && (
          <ErrorState
            message={errorMessage || "Не удалось загрузить данные страховки"}
            onRetry={() => loadData()}
          />
        )}

        {state === "data" && (
          <div className="space-y-5">
            {/* Hero Card */}
            <div
              className="rounded-2xl p-5 relative overflow-hidden"
              style={{
                background: "linear-gradient(135deg, #1a3a2a 0%, #0d2818 50%, #1a3a2a 100%)",
                border: "1px solid rgba(34, 197, 94, 0.2)",
              }}
            >
              <div className="absolute -top-6 -right-6 w-24 h-24 rounded-full opacity-10"
                style={{ background: "radial-gradient(circle, #22c55e, transparent)" }} />
              <div className="absolute -bottom-8 -left-8 w-32 h-32 rounded-full opacity-5"
                style={{ background: "radial-gradient(circle, #22c55e, transparent)" }} />
              <div className="flex items-start justify-between mb-4 relative z-10 gap-3">
                <div>
                  <p className="text-sm font-semibold tracking-wider text-[#94A3B8]">Белгосстрах</p>
                  <p className="text-[20px] font-bold text-white mt-0.5">АВгос+ком</p>
                </div>
                {isActive ? (
                  <div className="shrink-0 whitespace-nowrap rounded-full px-2.5 py-1 text-xs font-semibold"
                    style={{ backgroundColor: "rgba(34, 197, 94, 0.2)", color: "#4ADE80" }}>
                    Активна до {formatDate(expiry)}
                  </div>
                ) : (
                  <div className="shrink-0 rounded-full px-2.5 py-1 text-xs font-semibold"
                    style={{ backgroundColor: "rgba(239, 68, 68, 0.2)", color: "#f87171" }}>
                    Истекла
                  </div>
                )}
              </div>
              <div className="relative z-10">
                <p className="text-xs text-white/50 mb-1">Общий лимит</p>
                <p className="font-bold tracking-tight text-2xl text-white/90">
                  {totalSum.toLocaleString("ru-RU")} BYN
                </p>
              </div>
              <div className="flex items-center justify-between mt-4 pt-4 border-t border-white/10 relative z-10">
                <div>
                  <p className="text-[10px] text-white/40">Страхователь</p>
                  <p className="text-xs text-white/70">ООО «Фабрика Роста»</p>
                </div>
                <div>
                  <p className="text-[10px] text-white/40">Договор</p>
                  <p className="text-xs text-white/70">БРМ 0011726</p>
                </div>
              </div>
            </div>

            {/* Strict Limits */}
            <div>
              <h2 className="text-sm font-semibold uppercase tracking-wide mb-3 text-[#6B7280]">Строгие лимиты</h2>
              <div className="space-y-2.5">
                {STRICT_LIMITS.map((item) => {
                  const Icon = item.icon;
                  const isExhausted = item.used >= item.total;
                  const pct = (item.used / item.total) * 100;
                  return (
                    <div key={item.label} className="bg-[#F3F4F6] rounded-xl py-3.5 px-4"
                      style={{ opacity: isExhausted ? 0.5 : 1 }}>
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-2.5">
                          <Icon className="h-4 w-4" style={{ color: isExhausted ? "#EF4444" : "#007AFF" }} />
                          <span className="text-sm font-medium text-[#1F2937]">{item.label}</span>
                        </div>
                        <span className="text-xs font-semibold"
                          style={{ color: isExhausted ? "#EF4444" : "#1F2937" }}>
                          {isExhausted ? "Исчерпано" : `${item.used} из ${item.total}`}
                        </span>
                      </div>
                      <div className="w-full h-1.5 rounded-full overflow-hidden bg-[#E5E7EB]">
                        <div className="h-full rounded-full transition-all duration-700"
                          style={{ width: `${Math.min(pct, 100)}%`,
                            background: isExhausted ? "#EF4444" : "#60A5FA" }} />
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Unlimited */}
            <div>
              <h2 className="text-sm font-semibold uppercase tracking-wide mb-3 text-[#6B7280]">Без ограничений</h2>
              <div className="space-y-1.5">
                {UNLIMITED_ITEMS.map((item) => {
                  const Icon = item.icon;
                  return (
                    <div key={item.label} className="flex items-center gap-2.5 py-2">
                      <CheckCircle className="h-4 w-4 shrink-0 text-[#22C55E]" />
                      <Icon className="h-3.5 w-3.5 text-[#6B7280]" />
                      <span className="text-sm text-[#1F2937]">{item.label}</span>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Exclusions */}
            <div>
              <h2 className="text-sm font-semibold uppercase tracking-wide mb-3 text-[#6B7280]">Не покрывается</h2>
              <div className="space-y-1.5">
                {EXCLUDED_ITEMS.map((item) => (
                  <div key={item} className="flex items-center gap-2.5 py-2">
                    <XCircle className="h-4 w-4 shrink-0 text-[#D1D5DB]" />
                    <span className="text-sm text-[#9CA3AF]">{item}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Contacts */}
            <div className="space-y-3">
              <h2 className="text-sm font-semibold uppercase tracking-wide mb-1 text-[#6B7280]">Контакты страховой</h2>
              <a href="tel:+375222713071"
                className="flex items-center gap-3 rounded-xl p-4 transition-opacity hover:opacity-80 bg-[#F3F4F6]">
                <span className="text-lg">📞</span>
                <div className="flex items-center gap-2">
                  <Phone className="h-4 w-4 text-[#6B7280]" />
                  <span className="text-sm text-[#1F2937]">+375 222 71 30 71</span>
                </div>
              </a>
              <a href="mailto:dms.mogilev@bgs.by"
                className="flex items-center gap-3 rounded-xl p-4 transition-opacity hover:opacity-80 bg-[#F3F4F6]">
                <span className="text-lg">✉️</span>
                <div className="flex items-center gap-2">
                  <span className="text-sm text-[#1F2937]">dms.mogilev@bgs.by</span>
                </div>
              </a>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}

export default function InsurancePage() {
  const [state, setState] = useState<PageState>("loading");
  const [data, setData] = useState<InsuranceSchema | null>(null);
  const [errorMessage, setErrorMessage] = useState<string>("");

  const loadData = async () => {
    setState("loading");
    setErrorMessage("");
    try {
      const result = await fetchInsurance();
      setData(result);
      setState("data");
    } catch (err) {
      setErrorMessage(
        err instanceof Error ? err.message : "Не удалось загрузить данные страховки",
      );
      setState("error");
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  if (state === "loading") return <PageSkeleton variant="detail" />;

  if (state === "error") {
    return (
      <ErrorState
        message={errorMessage || "Не удалось загрузить данные страховки"}
        onRetry={() => loadData()}
      />
    );
  }

  const policy = data?.policies?.[0];
  const totalSum = policy?.sum_insured ?? 37651.83;
  const expiry = policy?.expiry ?? "2027-01-24";
  const isActive = new Date(expiry) > new Date();

  return (
    <motion.div
      className="p-4 space-y-5 pb-8"
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
    >
      {/* Header */}
      <div className="flex items-center gap-2">
        <TelegramBackButton to="/profile" />
        <Shield
          className="h-5 w-5"
          style={{ color: "var(--tg-theme-button-color)" }}
        />
        <h1
          className="text-xl font-semibold"
          style={{ color: "var(--tg-theme-text-color)" }}
        >
          Страховка
        </h1>
      </div>

      {/* ─── Hero Card (bank-card style) ─── */}
      <motion.div
        className="rounded-2xl p-5 relative overflow-hidden"
        style={{
          background: "linear-gradient(135deg, #1a3a2a 0%, #0d2818 50%, #1a3a2a 100%)",
          border: "1px solid rgba(34, 197, 94, 0.2)",
        }}
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ delay: 0.1, duration: 0.4, ease: [0.25, 0.4, 0.25, 1] as const }}
      >
        {/* Decorative circles */}
        <div
          className="absolute -top-6 -right-6 w-24 h-24 rounded-full opacity-10"
          style={{ background: "radial-gradient(circle, #22c55e, transparent)" }}
        />
        <div
          className="absolute -bottom-8 -left-8 w-32 h-32 rounded-full opacity-5"
          style={{ background: "radial-gradient(circle, #22c55e, transparent)" }}
        />

        {/* Top row: company + badge */}
        <div className="flex items-start justify-between mb-4 relative z-10 gap-3">
          <div>
            <p className="text-sm font-semibold tracking-wider text-[#94A3B8]" style={{ textTransform: "none" }}>Белгосстрах</p>
            <p className="text-[20px] font-bold text-white mt-0.5">АВгос+ком</p>
          </div>
          {isActive ? (
            <div
              className="shrink-0 whitespace-nowrap"
              style={{
                backgroundColor: "rgba(34, 197, 94, 0.2)",
                color: "#4ADE80",
                borderRadius: "9999px",
                padding: "4px 10px",
                fontSize: "12px",
                fontWeight: 600,
              }}
            >
              Активна до {formatDate(expiry)}
            </div>
          ) : (
            <div
              className="shrink-0"
              style={{
                backgroundColor: "rgba(239, 68, 68, 0.2)",
                color: "#f87171",
                borderRadius: "9999px",
                padding: "4px 10px",
                fontSize: "12px",
                fontWeight: 600,
              }}
            >
              Истекла
            </div>
          )}
        </div>

        {/* Total limit */}
        <div className="relative z-10">
          <p className="text-xs text-white/50 mb-1">Общий лимит</p>
          <p
            className="font-bold tracking-tight"
            style={{ fontSize: "24px", color: "rgba(255,255,255,0.9)" }}
          >
            {totalSum.toLocaleString("ru-RU")} BYN
          </p>
        </div>

        {/* Bottom row */}
        <div className="flex items-center justify-between mt-4 pt-4 border-t border-white/10 relative z-10">
          <div>
            <p className="text-[10px] text-white/40">Страхователь</p>
            <p className="text-xs text-white/70">ООО «Фабрика Роста»</p>
          </div>
          <div>
            <p className="text-[10px] text-white/40">Договор</p>
            <p className="text-xs text-white/70">БРМ 0011726</p>
          </div>
        </div>
      </motion.div>

      {/* ─── Strict Limits ─── */}
      <motion.section
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2, duration: 0.4 }}
      >
        <h2
          className="text-sm font-semibold uppercase tracking-wide mb-3"
          style={{ color: "var(--tg-theme-hint-color)" }}
        >
          Строгие лимиты
        </h2>
        <div className="space-y-2.5">
          {STRICT_LIMITS.map((item, i) => {
            const Icon = item.icon;
            const isExhausted = item.used >= item.total;
            const pct = (item.used / item.total) * 100;

            return (
              <motion.div
                key={item.label}
                className="bg-sh-surface rounded-xl py-3.5 px-4"
                initial={{ opacity: 0, x: -12 }}
                animate={{ opacity: isExhausted ? 0.5 : 1, x: 0 }}
                transition={{ delay: 0.25 + i * 0.05, duration: 0.3 }}
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2.5">
                    <Icon
                      className="h-4 w-4"
                      style={{
                        color: isExhausted ? "#EF4444" : "var(--tg-theme-button-color)",
                      }}
                    />
                    <span
                      className="text-sm font-medium"
                      style={{ color: "var(--tg-theme-text-color)" }}
                    >
                      {item.label}
                    </span>
                  </div>
                  <span
                    className="text-xs font-semibold text-white"
                    style={{
                      color: isExhausted ? "#EF4444" : "#FFFFFF",
                    }}
                  >
                    {isExhausted ? "Исчерпано" : `${item.used} из ${item.total}`}
                  </span>
                </div>
                {/* Progress bar */}
                <div
                  className="w-full h-1.5 rounded-full overflow-hidden"
                  style={{
                    background: "var(--tg-theme-secondary-bg-color, rgba(255,255,255,0.06))",
                  }}
                >
                  <div
                    className="h-full rounded-full transition-all duration-700"
                    style={{
                      width: `${Math.min(pct, 100)}%`,
                      background: isExhausted
                        ? "#EF4444"
                        : "#60A5FA",
                    }}
                  />
                </div>
              </motion.div>
            );
          })}
        </div>
      </motion.section>

      {/* ─── Unlimited ─── */}
      <motion.section
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.45, duration: 0.4 }}
      >
        <h2
          className="text-sm font-semibold uppercase tracking-wide mb-3"
          style={{ color: "var(--tg-theme-hint-color)" }}
        >
          Без ограничений
        </h2>
        <div className="space-y-1.5">
          {UNLIMITED_ITEMS.map((item, i) => {
            const Icon = item.icon;
            return (
              <motion.div
                key={item.label}
                className="flex items-center gap-2.5 py-2"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.5 + i * 0.05 }}
              >
                <CheckCircle className="h-4 w-4 shrink-0" style={{ color: "#22C55E" }} />
                <Icon
                  className="h-3.5 w-3.5"
                  style={{ color: "var(--tg-theme-hint-color)" }}
                />
                <span className="text-sm" style={{ color: "var(--tg-theme-text-color)" }}>
                  {item.label}
                </span>
              </motion.div>
            );
          })}
        </div>
      </motion.section>

      {/* ─── Exclusions ─── */}
      <motion.section
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.6, duration: 0.4 }}
      >
        <h2
          className="text-sm font-semibold uppercase tracking-wide mb-3"
          style={{ color: "var(--tg-theme-hint-color)" }}
        >
          Не покрывается
        </h2>
        <div className="space-y-1.5">
          {EXCLUDED_ITEMS.map((item, i) => (
            <motion.div
              key={item}
              className="flex items-center gap-2.5 py-2"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.65 + i * 0.05 }}
            >
              <XCircle
                className="h-4 w-4 shrink-0"
                style={{ color: "rgba(255,255,255,0.2)" }}
              />
              <span
                className="text-sm"
                style={{ color: "var(--tg-theme-hint-color)", opacity: 0.6 }}
              >
                {item}
              </span>
            </motion.div>
          ))}
        </div>
      </motion.section>

      {/* ─── Contacts ─── */}
      <motion.section
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.7 }}
        className="space-y-3"
      >
        <h2
          className="text-sm font-semibold uppercase tracking-wide mb-1"
          style={{ color: "var(--tg-theme-hint-color)" }}
        >
          Контакты страховой
        </h2>

        {/* Phone */}
        <a
          href="tel:+375222713071"
          className="flex items-center gap-3 rounded-xl p-4 transition-opacity hover:opacity-80"
          style={{ background: "rgba(255,255,255,0.05)" }}
        >
          <span className="text-lg">📞</span>
          <div className="flex items-center gap-2">
            <Phone className="h-4 w-4" style={{ color: "var(--tg-theme-hint-color)" }} />
            <span className="text-sm" style={{ color: "var(--tg-theme-text-color)" }}>+375 222 71 30 71</span>
          </div>
        </a>

        {/* Email */}
        <a
          href="mailto:dms.mogilev@bgs.by"
          className="flex items-center gap-3 rounded-xl p-4 transition-opacity hover:opacity-80"
          style={{ background: "rgba(255,255,255,0.05)" }}
        >
          <span className="text-lg">✉️</span>
          <div className="flex items-center gap-2">
            <span className="text-sm" style={{ color: "var(--tg-theme-text-color)" }}>dms.mogilev@bgs.by</span>
          </div>
        </a>
      </motion.section>
    </motion.div>
  );
}
