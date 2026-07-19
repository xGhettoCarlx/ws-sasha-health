import { useState, useEffect, useCallback } from "react";
import { motion } from "framer-motion";
import { Inbox, X, Check } from "lucide-react";
import { PageSkeleton } from "../../../components/ui/PageSkeleton";
import { ErrorState } from "../../../components/ErrorState";
import { EmptyState } from "../../../components/EmptyState";
import { apiFetch, apiPost } from "../../../lib/api";

// ─── Types ────────────────────────────────────────────────────────────

interface InboxItem {
  id: string;
  filename: string;
  original_path: string | null;
  ocr_status: string;
  extracted_data: Record<string, unknown>;
  created_at: string;
  processed: boolean;
  source_tier: string;
}

interface ItemFormState {
  verified_data: Record<string, string>;
  category: string;
  date: string;
  type_name: string;
}

type PageState = "loading" | "error" | "data";

// ─── Constants ────────────────────────────────────────────────────────

const CATEGORY_OPTIONS = [
  { value: "", label: "Выберите..." },
  { value: "analyses", label: "Анализы" },
  { value: "visits", label: "Визиты" },
  { value: "fluorography", label: "Флюорография" },
  { value: "medications", label: "Лекарства" },
  { value: "allergies", label: "Аллергии" },
  { value: "diagnoses", label: "Диагнозы" },
  { value: "history", label: "История" },
  { value: "other", label: "Другое" },
];

function getTodayDate(): string {
  return new Date().toISOString().slice(0, 10);
}

function createFormState(extracted_data: Record<string, unknown>): ItemFormState {
  const verified: Record<string, string> = {};
  if (extracted_data && typeof extracted_data === "object") {
    for (const [key, value] of Object.entries(extracted_data)) {
      verified[key] = value != null ? String(value) : "";
    }
  }
  return {
    verified_data: verified,
    category: "analyses",
    date: getTodayDate(),
    type_name: "",
  };
}

const stagger = {
  animate: { transition: { staggerChildren: 0.08 } },
};

const fadeUp = {
  initial: { opacity: 0, y: 16 },
  animate: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.35, ease: [0.25, 0.4, 0.25, 1] as const },
  },
};

// ─── Component ────────────────────────────────────────────────────────

export default function InboxPage() {
  const [state, setState] = useState<PageState>("loading");
  const [errorMessage, setErrorMessage] = useState("");
  const [items, setItems] = useState<InboxItem[]>([]);
  const [formStates, setFormStates] = useState<Record<string, ItemFormState>>({});
  const [processingIds, setProcessingIds] = useState<Set<string>>(new Set());

  const loadItems = useCallback(async () => {
    setState("loading");
    setErrorMessage("");
    try {
      const data = await apiFetch<InboxItem[]>("/api/inbox/pending");
      setItems(data);
      const init: Record<string, ItemFormState> = {};
      for (const item of data) {
        init[item.id] = createFormState(item.extracted_data);
      }
      setFormStates(init);
      setState("data");
    } catch (err) {
      setErrorMessage(
        err instanceof Error ? err.message : "Не удалось загрузить входящие",
      );
      setState("error");
    }
  }, []);

  useEffect(() => {
    loadItems();
  }, [loadItems]);

  // ─── Form field helpers ──────────────────────────────────────────

  function updateField(itemId: string, field: string, value: string) {
    setFormStates((prev) => ({
      ...prev,
      [itemId]: {
        ...(prev[itemId] ?? createFormState({})),
        verified_data: {
          ...(prev[itemId]?.verified_data ?? {}),
          [field]: value,
        },
      },
    }));
  }

  function updateMeta(
    itemId: string,
    field: "category" | "date" | "type_name",
    value: string,
  ) {
    setFormStates((prev) => ({
      ...prev,
      [itemId]: {
        ...(prev[itemId] ?? createFormState({})),
        [field]: value,
      },
    }));
  }

  // ─── Actions ──────────────────────────────────────────────────────

  async function handleVerify(itemId: string) {
    const form = formStates[itemId];
    if (!form || !form.category || !form.type_name.trim()) return;

    setProcessingIds((prev) => new Set(prev).add(itemId));
    try {
      await apiPost(`/api/inbox/${itemId}/verify`, {
        verified_data: form.verified_data,
        category: form.category,
        date: form.date,
        type_name: form.type_name.trim(),
      });
      await loadItems();
    } catch {
      /* item stays in list on error */
    } finally {
      setProcessingIds((prev) => {
        const next = new Set(prev);
        next.delete(itemId);
        return next;
      });
    }
  }

  async function handleReject(itemId: string) {
    setProcessingIds((prev) => new Set(prev).add(itemId));
    try {
      await apiPost(`/api/inbox/${itemId}/reject`);
      await loadItems();
    } catch {
      /* item stays in list on error */
    } finally {
      setProcessingIds((prev) => {
        const next = new Set(prev);
        next.delete(itemId);
        return next;
      });
    }
  }

  // ─── Render states ────────────────────────────────────────────────

  if (state === "loading") {
    return (
      <>
        <div className="flex items-center gap-2 pb-4">
          <h1 className="text-xl font-semibold text-[#1C1C1E]">
            Входящие
          </h1>
        </div>
        <PageSkeleton variant="detail" />
      </>
    );
  }

  if (state === "error") {
    return (
      <>
        <div className="flex items-center gap-2 pb-4">
          <h1 className="text-xl font-semibold text-[#1C1C1E]">
            Входящие
          </h1>
        </div>
        <ErrorState
          message={errorMessage || "Не удалось загрузить входящие"}
          onRetry={() => loadItems()}
        />
      </>
    );
  }

  if (items.length === 0) {
    return (
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.3 }}
      >
        <div className="flex items-center gap-2 pb-4">
          <Inbox className="h-5 w-5 text-[#007AFF]" />
          <h1 className="text-xl font-semibold text-[#1C1C1E]">
            Входящие
          </h1>
        </div>
        <EmptyState
          title="Нет входящих сканов"
          description="Загрузите анализы или документы через бота"
        />
      </motion.div>
    );
  }

  // ─── Data rendering ───────────────────────────────────────────────

  return (
    <motion.div
      className="space-y-4"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.3 }}
    >
      {/* ─── Header ────────────────────────────────────────────────── */}
      <div className="flex items-center gap-2">
        <Inbox className="h-5 w-5 text-[#007AFF]" />
        <h1 className="text-xl font-semibold text-[#1C1C1E]">
          Входящие
        </h1>
        <span className="text-xs rounded-full px-2 py-0.5 ml-1 bg-[#007AFF]/10 text-[#007AFF]">
          {items.length}
        </span>
      </div>

      {/* ─── Item cards ────────────────────────────────────────────── */}
      <motion.div variants={stagger} initial="initial" animate="animate" className="space-y-8">
        {items.map((item) => (
          <InboxItemCard
            key={item.id}
            item={item}
            form={formStates[item.id] ?? createFormState(item.extracted_data)}
            processing={processingIds.has(item.id)}
            onFieldChange={(field, value) => updateField(item.id, field, value)}
            onMetaChange={(field, value) => updateMeta(item.id, field, value)}
            onVerify={() => handleVerify(item.id)}
            onReject={() => handleReject(item.id)}
          />
        ))}
      </motion.div>
    </motion.div>
  );
}

// ─── Item Card ────────────────────────────────────────────────────────

interface InboxItemCardProps {
  item: InboxItem;
  form: ItemFormState;
  processing: boolean;
  onFieldChange: (field: string, value: string) => void;
  onMetaChange: (field: "category" | "date" | "type_name", value: string) => void;
  onVerify: () => void;
  onReject: () => void;
}

function InboxItemCard({
  item,
  form,
  processing,
  onFieldChange,
  onMetaChange,
  onVerify,
  onReject,
}: InboxItemCardProps) {
  const hasFields = Object.keys(form.verified_data).length > 0;
  const canVerify = Boolean(form.category && form.type_name.trim() && !processing);

  return (
    <motion.div
      variants={fadeUp}
      layout
      className="rounded-2xl overflow-hidden bg-white border border-[#E5E7EB]"
    >
      {/* ─── Image ─────────────────────────────────────────────────── */}
      <div
        className="w-full flex items-center justify-center overflow-hidden"
        style={{ maxHeight: "50vh", background: "rgba(0,0,0,0.3)" }}
      >
        <img
          src={`/api/inbox/${item.id}/original`}
          alt={item.filename}
          style={{
            maxHeight: "50vh",
            objectFit: "contain",
            borderRadius: "12px",
            maxWidth: "100%",
          }}
          className="p-2"
        />
      </div>

      {/* ─── Meta badge row ────────────────────────────────────────── */}
      <div className="px-4 pt-3 flex items-center gap-2 flex-wrap">
        <span className="text-xs px-2 py-1 rounded-full bg-[#007AFF]/10 text-[#007AFF]">
          {item.filename}
        </span>
        {item.ocr_status !== "completed" && (
          <span className="text-xs px-2 py-1 rounded-full bg-[#F59E0B]/10 text-[#F59E0B]">
            {item.ocr_status === "processing" ? "OCR..." : item.ocr_status}
          </span>
        )}
      </div>

      {/* ─── Scrollable form ───────────────────────────────────────── */}
      <div className="px-4 py-3 space-y-3">
        {/* Category / Date / Type */}
        <div className="grid grid-cols-3 gap-2">
          <div className="space-y-1">
            <label className="text-[10px] uppercase tracking-wide font-semibold block text-[#8E8E93]">
              Категория
            </label>
            <select
              value={form.category}
              onChange={(e) => onMetaChange("category", e.target.value)}
              disabled={processing}
              className="w-full rounded-lg px-2 py-2 text-xs border border-[#E5E7EB] focus:outline-none focus:ring-1 focus:ring-[#007AFF]/30 bg-[#F2F2F7] text-[#1C1C1E]"
            >
              {CATEGORY_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>
          <div className="space-y-1">
            <label className="text-[10px] uppercase tracking-wide font-semibold block text-[#8E8E93]">
              Дата
            </label>
            <input
              type="date"
              value={form.date}
              onChange={(e) => onMetaChange("date", e.target.value)}
              disabled={processing}
              className="w-full rounded-lg px-2 py-2 text-xs border border-[#E5E7EB] focus:outline-none focus:ring-1 focus:ring-[#007AFF]/30 bg-[#F2F2F7] text-[#1C1C1E]"
            />
          </div>
          <div className="space-y-1">
            <label className="text-[10px] uppercase tracking-wide font-semibold block text-[#8E8E93]">
              Тип
            </label>
            <input
              type="text"
              value={form.type_name}
              onChange={(e) => onMetaChange("type_name", e.target.value)}
              disabled={processing}
              placeholder="кровь"
              className="w-full rounded-lg px-2 py-2 text-xs border border-[#E5E7EB] focus:outline-none focus:ring-1 focus:ring-[#007AFF]/30 bg-[#F2F2F7] text-[#1C1C1E]"
            />
          </div>
        </div>

        {/* Extracted data fields */}
        {hasFields ? (
          <div className="space-y-2">
            <p className="text-[10px] uppercase tracking-wide font-semibold text-[#8E8E93]">
              Извлечённые данные
            </p>
            {Object.entries(form.verified_data).map(([key, value]) => (
              <div key={key} className="space-y-1">
                <label className="text-[11px] font-medium block text-[#6B7280]">
                  {key}
                </label>
                <input
                  type="text"
                  value={value}
                  onChange={(e) => onFieldChange(key, e.target.value)}
                  disabled={processing}
                  className="w-full rounded-lg px-3 py-2.5 text-sm border border-[#E5E7EB] focus:outline-none focus:ring-1 focus:ring-[#007AFF]/30 bg-[#F2F2F7] text-[#1C1C1E]"
                />
              </div>
            ))}
          </div>
        ) : (
          <p className="text-xs py-2 text-[#8E8E93]">
            {item.ocr_status === "completed"
              ? "Нет извлечённых данных"
              : "Ожидание распознавания..."}
          </p>
        )}
      </div>

      {/* ─── Footer ────────────────────────────────────────────────── */}
      <div
        className="flex gap-2 px-4 py-3 bg-[#F2F2F7] border-t border-[#E5E7EB]"
      >
        <motion.button
          whileTap={{ scale: 0.97 }}
          onClick={onReject}
          disabled={processing}
          className="flex-1 flex items-center justify-center gap-2 rounded-xl py-2.5 text-sm font-medium transition-opacity disabled:opacity-40"
          style={{
            background: "transparent",
            border: "1.5px solid #EF4444",
            color: "#EF4444",
          }}
        >
          <X className="h-4 w-4" />
          Отклонить
        </motion.button>
        <motion.button
          whileTap={{ scale: 0.97 }}
          onClick={onVerify}
          disabled={!canVerify}
          className="flex-1 flex items-center justify-center gap-2 rounded-xl py-2.5 text-sm font-semibold transition-opacity disabled:opacity-40"
          style={{
            background: canVerify ? "#007AFF" : "rgba(0,122,255,0.2)",
            color: canVerify ? "#fff" : "rgba(0,122,255,0.4)",
          }}
        >
          {processing ? (
            <>
              <motion.span
                animate={{ rotate: 360 }}
                transition={{ repeat: Infinity, duration: 1, ease: "linear" }}
                className="h-4 w-4 border-2 border-current border-t-transparent rounded-full inline-block"
              />
              Сохранение...
            </>
          ) : (
            <>
              <Check className="h-4 w-4" />
              Сохранить
            </>
          )}
        </motion.button>
      </div>
    </motion.div>
  );
}
