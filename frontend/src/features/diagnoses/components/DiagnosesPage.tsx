import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { Stethoscope } from "lucide-react";
import { PageSkeleton } from "../../../components/ui/PageSkeleton";
import { ErrorState } from "../../../components/ErrorState";
import { EmptyState } from "../../../components/EmptyState";
import { StatusBadge } from "../../../components/ui/StatusBadge";
import TelegramBackButton from "../../../components/TelegramBackButton";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "../../../components/ui/dialog";
import { fetchProfile } from "../../../lib/services";
import type { DiagnosisItem } from "../../../lib/types";

type PageState = "loading" | "error" | "empty" | "data";

function trustTierProps(
  tier: string | undefined | null,
): { variant: "normal" | "warning" | "critical" | "verified"; label: string } {
  switch (tier) {
    case "trusted":
      return { variant: "verified", label: "Проверено" };
    case "verified":
      return { variant: "normal", label: "Подтверждено" };
    default:
      return { variant: "warning", label: "Не проверено" };
  }
}


// ─── Modal Component ─────────────────────────────────────────────────────────

interface DiagnosesModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function DiagnosesModal({ open, onOpenChange }: DiagnosesModalProps) {
  const [state, setState] = useState<PageState>("loading");
  const [data, setData] = useState<DiagnosisItem[]>([]);
  const [errorMessage, setErrorMessage] = useState<string>("");

  const loadData = async () => {
    setState("loading");
    setErrorMessage("");
    try {
      const profile = await fetchProfile();
      const diagnoses = profile.diagnoses ?? [];
      if (diagnoses.length === 0) {
        setState("empty");
        return;
      }
      setData(diagnoses);
      setState("data");
    } catch (err) {
      setErrorMessage(
        err instanceof Error
          ? err.message
          : "Не удалось загрузить список диагнозов",
      );
      setState("error");
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-[#1F2937]">
            <Stethoscope className="h-5 w-5 text-[#007AFF]" />
            Диагнозы
          </DialogTitle>
        </DialogHeader>

        {state === "loading" && <div className="py-8"><PageSkeleton variant="card" /></div>}

        {state === "error" && (
          <ErrorState
            message={errorMessage || "Не удалось загрузить список диагнозов"}
            onRetry={() => loadData()}
          />
        )}

        {state === "empty" && (
          <EmptyState
            icon={<Stethoscope className="h-8 w-8" />}
            title="Диагнозов нет"
            description="У вас пока нет добавленных диагнозов"
          />
        )}

        {state === "data" && (
          <div>
            {data.map((item, i) => {
              const { variant, label } = trustTierProps(item.trust_tier);
              return (
                <div
                  key={item.name ?? i}
                  className="bg-white rounded-xl p-4 mb-3 shadow-[0_2px_8px_rgba(0,0,0,0.04)]"
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0 flex-1">
                      <p className="font-medium text-sm text-[#1F2937]">
                        {item.name}
                      </p>
                      {item.source && (
                        <p className="text-xs text-[#6B7280] mt-0.5">
                          {item.source}
                        </p>
                      )}
                    </div>
                    <StatusBadge
                      variant={variant}
                      label={label}
                      className="shrink-0"
                    />
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}

export default function DiagnosesPage() {
  const [state, setState] = useState<PageState>("loading");
  const [data, setData] = useState<DiagnosisItem[]>([]);
  const [errorMessage, setErrorMessage] = useState<string>("");

  const loadData = async () => {
    setState("loading");
    setErrorMessage("");
    try {
      const profile = await fetchProfile();
      const diagnoses = profile.diagnoses ?? [];
      if (diagnoses.length === 0) {
        setState("empty");
        return;
      }
      setData(diagnoses);
      setState("data");
    } catch (err) {
      setErrorMessage(
        err instanceof Error
          ? err.message
          : "Не удалось загрузить список диагнозов",
      );
      setState("error");
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  if (state === "loading") return <PageSkeleton variant="card" />;

  if (state === "error") {
    return (
      <ErrorState
        message={errorMessage || "Не удалось загрузить список диагнозов"}
        onRetry={() => loadData()}
      />
    );
  }

  if (state === "empty") {
    return (
      <EmptyState
        icon={<Stethoscope className="h-8 w-8" />}
        title="Диагнозов нет"
        description="У вас пока нет добавленных диагнозов"
      />
    );
  }

  return (
    <motion.div
      className="p-4 space-y-4 pb-8"
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: 0.1 }}
    >
      <div className="flex items-center gap-2">
        <TelegramBackButton to="/profile" />
        <Stethoscope
          className="h-5 w-5"
          style={{ color: "var(--tg-theme-button-color, #2481cc)" }}
        />
        <h1
          className="text-xl font-semibold"
          style={{ color: "var(--tg-theme-text-color)" }}
        >
          Диагнозы
        </h1>
      </div>

      <div>
        {data.map((item, i) => {
          const { variant, label } = trustTierProps(item.trust_tier);
          return (
            <motion.div
              key={item.name ?? i}
              className="bg-sh-surface rounded-xl p-4 mb-3"
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.06, duration: 0.3 }}
            >
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0 flex-1">
                  <p
                    className="font-medium text-sm"
                    style={{ color: "var(--tg-theme-text-color)" }}
                  >
                    {item.name}
                  </p>
                  {item.source && (
                    <p className="text-xs text-sh-secondary mt-0.5">
                      {item.source}
                    </p>
                  )}
                </div>
                <StatusBadge
                  variant={variant}
                  label={label}
                  className="shrink-0"
                />
              </div>
            </motion.div>
          );
        })}
      </div>
    </motion.div>
  );
}
