import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { AlertTriangle, ChevronRight } from "lucide-react";
import { PageSkeleton } from "../../../components/ui/PageSkeleton";
import { ErrorState } from "../../../components/ErrorState";
import { EmptyState } from "../../../components/EmptyState";
import TelegramBackButton from "../../../components/TelegramBackButton";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "../../../components/ui/dialog";
import { fetchProfile } from "../../../lib/services";

type PageState = "loading" | "error" | "empty" | "data";


// ─── Modal Component ─────────────────────────────────────────────────────────

interface AllergiesModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function AllergiesModal({ open, onOpenChange }: AllergiesModalProps) {
  const [state, setState] = useState<PageState>("loading");
  const [data, setData] = useState<string[]>([]);
  const [errorMessage, setErrorMessage] = useState<string>("");

  const loadData = async () => {
    setState("loading");
    setErrorMessage("");
    try {
      const profile = await fetchProfile();
      const allergies = profile.allergies ?? [];
      if (allergies.length === 0) {
        setState("empty");
        return;
      }
      setData(allergies);
      setState("data");
    } catch (err) {
      setErrorMessage(
        err instanceof Error
          ? err.message
          : "Не удалось загрузить список аллергий",
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
            <AlertTriangle className="h-5 w-5 text-[#EC4899]" />
            Аллергии
          </DialogTitle>
        </DialogHeader>

        {state === "loading" && <div className="py-8"><PageSkeleton variant="list" /></div>}

        {state === "error" && (
          <ErrorState
            message={errorMessage || "Не удалось загрузить список аллергий"}
            onRetry={() => loadData()}
          />
        )}

        {state === "empty" && (
          <EmptyState
            icon={<AlertTriangle className="h-8 w-8" />}
            title="Аллергий нет"
            description="У вас пока нет добавленных аллергий"
          />
        )}

        {state === "data" && (
          <div className="bg-white rounded-2xl overflow-hidden shadow-[0_2px_8px_rgba(0,0,0,0.04)]">
            {data.map((item, i) => (
              <div
                key={item ?? i}
                className="px-4 py-3.5 border-b border-[#F3F4F6] last:border-b-0"
              >
                <div className="flex items-center justify-between">
                  <p className="text-[#1F2937] text-sm">{item}</p>
                  <ChevronRight className="h-4 w-4 text-[#6B7280] shrink-0" />
                </div>
              </div>
            ))}
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}

export default function AllergiesPage() {
  const [state, setState] = useState<PageState>("loading");
  const [data, setData] = useState<string[]>([]);
  const [errorMessage, setErrorMessage] = useState<string>("");

  const loadData = async () => {
    setState("loading");
    setErrorMessage("");
    try {
      const profile = await fetchProfile();
      const allergies = profile.allergies ?? [];
      if (allergies.length === 0) {
        setState("empty");
        return;
      }
      setData(allergies);
      setState("data");
    } catch (err) {
      setErrorMessage(
        err instanceof Error
          ? err.message
          : "Не удалось загрузить список аллергий",
      );
      setState("error");
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  if (state === "loading") return <PageSkeleton variant="list" />;

  if (state === "error") {
    return (
      <ErrorState
        message={errorMessage || "Не удалось загрузить список аллергий"}
        onRetry={() => loadData()}
      />
    );
  }

  if (state === "empty") {
    return (
      <EmptyState
        icon={<AlertTriangle className="h-8 w-8" />}
        title="Аллергий нет"
        description="У вас пока нет добавленных аллергий"
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
        <AlertTriangle
          className="h-5 w-5"
          style={{ color: "var(--tg-theme-button-color, #2481cc)" }}
        />
        <h1
          className="text-xl font-semibold"
          style={{ color: "var(--tg-theme-text-color)" }}
        >
          Аллергии
        </h1>
      </div>

      <div className="bg-sh-surface rounded-2xl overflow-hidden">
        {data.map((item, i) => (
          <motion.div
            key={item ?? i}
            className="px-4 py-3.5 border-b border-sh-border last:border-b-0"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.04, duration: 0.2 }}
          >
            <div className="flex items-center justify-between">
              <p className="text-sh-primary text-sm">{item}</p>
              <ChevronRight className="h-4 w-4 text-sh-secondary shrink-0" />
            </div>
          </motion.div>
        ))}
      </div>
    </motion.div>
  );
}
