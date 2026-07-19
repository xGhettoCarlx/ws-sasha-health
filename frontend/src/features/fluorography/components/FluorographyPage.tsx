import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Scan, AlertTriangle, Calendar, CheckCircle } from "lucide-react";
import { PageSkeleton } from "../../../components/ui/PageSkeleton";
import { ErrorState } from "../../../components/ErrorState";
import { EmptyState } from "../../../components/EmptyState";
import { Card, CardContent } from "../../../components/ui/card";
import TelegramBackButton from "../../../components/TelegramBackButton";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "../../../components/ui/dialog";
import { fetchFluorography } from "../../../lib/services";
import type { FluorographySchema, FluorographyRecord } from "../../../lib/types";

const OVERDUE_MONTHS = 10;

type PageState = "loading" | "error" | "empty" | "data";

function monthsSince(dateStr: string): number {
  const date = new Date(dateStr);
  const now = new Date();
  return (
    (now.getFullYear() - date.getFullYear()) * 12 +
    (now.getMonth() - date.getMonth())
  );
}

function getDateColor(months: number): string {
  if (months > OVERDUE_MONTHS) return "var(--tg-theme-destructive-color, #ef4444)";
  if (months >= 8) return "#f59e0b";
  return "#22c55e";
}

function formatDate(dateStr: string): string {
  const date = new Date(dateStr);
  return date.toLocaleDateString("ru-RU", {
    day: "numeric",
    month: "long",
    year: "numeric",
  });
}


// ─── Modal Component ─────────────────────────────────────────────────────────

interface FluorographyModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function FluorographyModal({ open, onOpenChange }: FluorographyModalProps) {
  const [state, setState] = useState<PageState>("loading");
  const [data, setData] = useState<FluorographySchema | null>(null);
  const [errorMessage, setErrorMessage] = useState<string>("");

  const loadData = async () => {
    setState("loading");
    setErrorMessage("");
    try {
      const result = await fetchFluorography();
      if (!result.history || result.history.length === 0) {
        setState("empty");
        return;
      }
      const sorted = [...result.history].sort(
        (a, b) => new Date(b.date).getTime() - new Date(a.date).getTime(),
      );
      setData({ ...result, history: sorted });
      setState("data");
    } catch (err) {
      setErrorMessage(
        err instanceof Error ? err.message : "Не удалось загрузить данные флюорографии",
      );
      setState("error");
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const history = data?.history ?? [];
  const lastExam = history[0];
  const monthsSinceLast = lastExam ? monthsSince(lastExam.date) : 0;
  const isOverdue = monthsSinceLast > OVERDUE_MONTHS;
  const nextDue = data?.next_due;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="text-[#1F2937]">Флюорография</DialogTitle>
        </DialogHeader>

        {state === "loading" && <div className="py-8"><PageSkeleton variant="default" /></div>}

        {state === "error" && (
          <ErrorState
            message={errorMessage || "Не удалось загрузить данные флюорографии"}
            onRetry={() => loadData()}
          />
        )}

        {state === "empty" && (
          <EmptyState
            icon={<Scan className="h-8 w-8" />}
            title="Нет обследований"
            description="У вас пока нет записей о флюорографии"
          />
        )}

        {state === "data" && (
          <div className="space-y-4">
            {isOverdue && (
              <motion.div
                className="flex items-start gap-3 rounded-xl p-4"
                style={{ background: "#ef4444", color: "#ffffff" }}
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ duration: 0.3 }}
              >
                <AlertTriangle className="h-5 w-5 shrink-0 mt-0.5" />
                <div>
                  <p className="text-sm font-semibold leading-snug">
                    Прошло более {OVERDUE_MONTHS} месяцев с последней флюорографии.
                  </p>
                  <p className="text-xs mt-1 opacity-90 leading-snug">
                    Рекомендуется пройти обследование.
                  </p>
                </div>
              </motion.div>
            )}

            {nextDue && (
              <motion.div
                className="flex items-center gap-2 rounded-lg p-3 text-sm bg-[#F3F4F6]"
                initial={{ opacity: 0, y: -8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.25 }}
              >
                <Calendar className="h-4 w-4 shrink-0 text-[#007AFF]" />
                <span className="text-[#1F2937]">
                  Следующее обследование:{" "}
                  <span className="font-medium">{formatDate(nextDue)}</span>
                </span>
              </motion.div>
            )}

            {lastExam && (
            <div className="flex items-center gap-3 rounded-xl p-4 bg-[#F3F4F6]">
              <div
                className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full"
                style={{ background: getDateColor(monthsSinceLast) }}
              >
                <CheckCircle className="h-5 w-5 text-white" />
              </div>
              <div>
                <p className="text-xs text-[#6B7280]">Последнее обследование</p>
                <p className="text-sm font-semibold" style={{ color: getDateColor(monthsSinceLast) }}>
                  {formatDate(lastExam.date)}
                </p>
              </div>
              <span
                className="ml-auto shrink-0 rounded-full px-2.5 py-0.5 text-xs font-medium"
                style={{
                  background: isOverdue ? "#ef4444" : monthsSinceLast >= 8 ? "#fef3c7" : "#dcfce7",
                  color: isOverdue ? "#ffffff" : monthsSinceLast >= 8 ? "#92400e" : "#166534",
                }}
              >
                {isOverdue ? "Просрочено" : monthsSinceLast >= 8 ? "Скоро" : "Актуально"}
              </span>
            </div>
            )}

            <div>
              <h2 className="text-sm font-semibold mb-3 text-[#6B7280]">История обследований</h2>
              <div className="space-y-3">
                {history.map((record: FluorographyRecord, index: number) => (
                  <motion.div
                    key={`${record.date}-${record.number}-${index}`}
                    initial={{ opacity: 0, y: 16 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.3, delay: index * 0.06 }}
                  >
                    <Card size="sm">
                      <CardContent>
                        <div className="flex items-start justify-between gap-3">
                          <div className="min-w-0 flex-1">
                            <p className="text-sm font-medium truncate text-[#1F2937]">
                              {formatDate(record.date)}
                            </p>
                            <p className="text-xs mt-0.5 text-[#6B7280]">
                              {record.institution}
                            </p>
                            {record.number && (
                              <p className="text-xs mt-0.5 text-[#6B7280]">
                                № {record.number}
                              </p>
                            )}
                          </div>
                          <span className="shrink-0 rounded-full px-2.5 py-0.5 text-xs font-medium bg-[#007AFF] text-white">
                            {record.result}
                          </span>
                        </div>
                      </CardContent>
                    </Card>
                  </motion.div>
                ))}
              </div>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}

export default function FluorographyPage() {
  const [state, setState] = useState<PageState>("loading");
  const [data, setData] = useState<FluorographySchema | null>(null);
  const [errorMessage, setErrorMessage] = useState<string>("");

  const loadData = async () => {
    setState("loading");
    setErrorMessage("");
    try {
      const result = await fetchFluorography();
      if (!result.history || result.history.length === 0) {
        setState("empty");
        return;
      }
      // Sort history by date descending (most recent first)
      const sorted = [...result.history].sort(
        (a, b) => new Date(b.date).getTime() - new Date(a.date).getTime(),
      );
      setData({ ...result, history: sorted });
      setState("data");
    } catch (err) {
      setErrorMessage(
        err instanceof Error ? err.message : "Не удалось загрузить данные флюорографии",
      );
      setState("error");
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  // ─── Loading ──────────────────────────────────────────────────────────────
  if (state === "loading") return <PageSkeleton variant="default" />;

  // ─── Error ────────────────────────────────────────────────────────────────
  if (state === "error") {
    return (
      <ErrorState
        message={errorMessage || "Не удалось загрузить данные флюорографии"}
        onRetry={() => loadData()}
      />
    );
  }

  // ─── Empty ────────────────────────────────────────────────────────────────
  if (state === "empty") {
    return (
      <EmptyState
        icon={<Scan className="h-8 w-8" />}
        title="Нет обследований"
        description="У вас пока нет записей о флюорографии"
      />
    );
  }

  // ─── Data ─────────────────────────────────────────────────────────────────
  const history = data!.history;
  const lastExam = history[0]!;
  const monthsSinceLast = monthsSince(lastExam.date);
  const isOverdue = monthsSinceLast > OVERDUE_MONTHS;
  const nextDue = data!.next_due;

  return (
    <motion.div
      className="p-4 space-y-4"
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: 0.1 }}
    >
      {/* ─── Header ──────────────────────────────────────────────────────── */}
      <div className="flex items-center gap-2">
        <TelegramBackButton to="/profile" />
        <h1 className="text-xl font-semibold" style={{ color: "var(--tg-theme-text-color)" }}>
          Флюорография
        </h1>
      </div>

      {/* ─── Overdue Warning ─────────────────────────────────────────────── */}
      <AnimatePresence>
        {isOverdue && (
          <motion.div
            className="flex items-start gap-3 rounded-xl p-4"
            style={{
              background: "var(--tg-theme-destructive-color, #ef4444)",
              color: "#ffffff",
            }}
            initial={{ opacity: 0, scale: 0.95, height: 0 }}
            animate={{ opacity: 1, scale: 1, height: "auto" }}
            exit={{ opacity: 0, scale: 0.95, height: 0 }}
            transition={{ duration: 0.3 }}
          >
            <AlertTriangle className="h-5 w-5 shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-semibold leading-snug">
                Прошло более {OVERDUE_MONTHS} месяцев с последней флюорографии.
              </p>
              <p className="text-xs mt-1 opacity-90 leading-snug">
                Рекомендуется пройти обследование.
              </p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ─── Next Due ────────────────────────────────────────────────────── */}
      <AnimatePresence>
        {nextDue && (
          <motion.div
            className="flex items-center gap-2 rounded-lg p-3 text-sm"
            style={{
              background: "var(--tg-theme-secondary-bg-color, #f0f0f0)",
              color: "var(--tg-theme-text-color)",
            }}
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.25, delay: 0.15 }}
          >
            <Calendar className="h-4 w-4 shrink-0" style={{ color: "var(--tg-theme-button-color, #2481cc)" }} />
            <span>
              Следующее обследование:{" "}
              <span className="font-medium">{formatDate(nextDue)}</span>
            </span>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ─── Last Exam Status ────────────────────────────────────────────── */}
      <motion.div
        className="flex items-center gap-3 rounded-xl p-4"
        style={{
          background: "var(--tg-theme-secondary-bg-color, #f0f0f0)",
        }}
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3, delay: 0.2 }}
      >
        <div
          className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full"
          style={{ background: getDateColor(monthsSinceLast) }}
        >
          <CheckCircle className="h-5 w-5 text-white" />
        </div>
        <div>
          <p
            className="text-xs"
            style={{ color: "var(--tg-theme-hint-color)" }}
          >
            Последнее обследование
          </p>
          <p
            className="text-sm font-semibold"
            style={{
              color: getDateColor(monthsSinceLast),
            }}
          >
            {formatDate(lastExam.date)}
          </p>
        </div>
        <span
          className="ml-auto shrink-0 rounded-full px-2.5 py-0.5 text-xs font-medium"
          style={{
            background: isOverdue
              ? "var(--tg-theme-destructive-color, #ef4444)"
              : monthsSinceLast >= 8
                ? "#fef3c7"
                : "#dcfce7",
            color: isOverdue
              ? "#ffffff"
              : monthsSinceLast >= 8
                ? "#92400e"
                : "#166534",
          }}
        >
          {isOverdue
            ? "Просрочено"
            : monthsSinceLast >= 8
              ? "Скоро"
              : "Актуально"}
        </span>
      </motion.div>

      {/* ─── History List ────────────────────────────────────────────────── */}
      <div>
        <h2
          className="text-sm font-semibold mb-3"
          style={{ color: "var(--tg-theme-hint-color)" }}
        >
          История обследований
        </h2>
        <div className="space-y-3">
          {history.map((record: FluorographyRecord, index: number) => (
            <motion.div
              key={`${record.date}-${record.number}-${index}`}
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3, delay: 0.25 + index * 0.06 }}
            >
              <Card size="sm">
                <CardContent>
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0 flex-1">
                      <p
                        className="text-sm font-medium truncate"
                        style={{ color: "var(--tg-theme-text-color)" }}
                      >
                        {formatDate(record.date)}
                      </p>
                      <p
                        className="text-xs mt-0.5"
                        style={{ color: "var(--tg-theme-hint-color)" }}
                      >
                        {record.institution}
                      </p>
                      {record.number && (
                        <p
                          className="text-xs mt-0.5"
                          style={{ color: "var(--tg-theme-hint-color)" }}
                        >
                          № {record.number}
                        </p>
                      )}
                    </div>
                    <span
                      className="shrink-0 rounded-full px-2.5 py-0.5 text-xs font-medium"
                      style={{
                        background: "var(--tg-theme-button-color, #2481cc)",
                        color: "var(--tg-theme-button-text-color, #ffffff)",
                      }}
                    >
                      {record.result}
                    </span>
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          ))}
        </div>
      </div>
    </motion.div>
  );
}
