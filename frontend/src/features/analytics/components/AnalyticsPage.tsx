import { useState, useEffect, useCallback } from "react";
import { motion } from "framer-motion";
import { TrendingUp, Shield, Sun, Heart } from "lucide-react";
import { PageSkeleton } from "../../../components/ui/PageSkeleton";
import { ErrorState } from "../../../components/ErrorState";
import { EmptyState } from "../../../components/EmptyState";
import { Card } from "../../../components/ui/card";
import { Accordion, AccordionItem, AccordionTrigger, AccordionContent } from "../../../components/ui/accordion";
import { fetchStrategy, fetchCategories, fetchAnalytics } from "../../../lib/services";
import type { StrategySchema, StrategyStep, AnalyticsResponse, AnalyticsParameter } from "../../../lib/types";

type PageState = "loading" | "error" | "empty" | "data";

const SECTION_ICONS: Record<string, React.FC<{ className?: string }>> = {
  "ДО СТРАХОВКИ": Shield,
  "ЕЖЕДНЕВНО": Sun,
  "ПО СТРАХОВКЕ": Heart,
};

function priorityBorder(priority: number): string {
  if (priority <= 2) return "border-l-sh-status-critical";
  if (priority === 3) return "border-l-sh-status-warning";
  return "border-l-[#60A5FA]";
}

export default function AnalyticsPage() {
  const [state, setState] = useState<PageState>("loading");
  const [strategy, setStrategy] = useState<StrategySchema | null>(null);
  const [categories, setCategories] = useState<string[]>([]);
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [analyticsItems, setAnalyticsItems] = useState<AnalyticsParameter[]>([]);
  const [errorMessage, setErrorMessage] = useState("");

  const loadData = useCallback(async () => {
    setState("loading");
    setErrorMessage("");
    try {
      const [strat, cats] = await Promise.all([
        fetchStrategy(),
        fetchCategories(),
      ]);
      setStrategy(strat);
      setCategories(cats.categories ?? []);
      const hasData = (strat.steps?.length ?? 0) > 0 || (cats.categories?.length ?? 0) > 0;
      setState(hasData ? "data" : "empty");
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : "Ошибка загрузки");
      setState("error");
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const loadAnalytics = useCallback(async (category: string) => {
    try {
      const data: AnalyticsResponse = await fetchAnalytics(category);
      setAnalyticsItems(data.items ?? []);
    } catch {
      setAnalyticsItems([]);
    }
  }, []);

  useEffect(() => {
    if (selectedCategory) {
      loadAnalytics(selectedCategory);
    } else {
      setAnalyticsItems([]);
    }
  }, [selectedCategory, loadAnalytics]);

  if (state === "loading") return <PageSkeleton variant="card" />;

  if (state === "error") {
    return <ErrorState message={errorMessage || "Ошибка загрузки"} onRetry={loadData} />;
  }

  if (state === "empty") {
    return <EmptyState title="Нет данных" description="Стратегия и аналитика пока не заполнены" />;
  }

  // Group strategy steps by section
  const sections = new Map<string, StrategyStep[]>();
  for (const step of strategy?.steps ?? []) {
    const key = step.section || "Без категории";
    const list = sections.get(key);
    if (list) list.push(step);
    else sections.set(key, [step]);
  }
  // Sort steps within each section by priority
  for (const steps of sections.values()) {
    steps.sort((a, b) => a.priority - b.priority);
  }

  // Group analytics items by test_name/date
  const analyticsGroups = new Map<string, AnalyticsParameter[]>();
  for (const item of analyticsItems) {
    const key = `${item.test_name}::${item.date}`;
    const group = analyticsGroups.get(key);
    if (group) group.push(item);
    else analyticsGroups.set(key, [item]);
  }

  function flagColorClass(flag: string | null | undefined): string {
    if (!flag || flag === "N") return "text-green-400";
    return "text-red-400";
  }

  return (
    <motion.div
      className="p-4 space-y-4 pb-8"
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: 0.1 }}
    >
      <h1 className="text-xl font-semibold text-sh-primary">Анализы</h1>

      {/* ── Strategy Section ────────────────────────────────────────── */}
      {sections.size > 0 && (
        <div className="space-y-4">
          <h2 className="text-sm font-medium text-sh-secondary uppercase tracking-wide">
            {strategy?.title ?? "Стратегия здоровья"}
          </h2>
          {Array.from(sections.entries()).map(([sectionName, steps]) => {
            const Icon = SECTION_ICONS[sectionName];
            return (
              <Card key={sectionName} className="bg-sh-surface border-0 ring-0 rounded-2xl p-4">
                <div className="flex items-center gap-2 mb-3">
                  {Icon && <Icon className="h-5 w-5 text-sh-accent" />}
                  <h3 className="text-lg font-semibold text-sh-primary">{sectionName}</h3>
                </div>
                <div className="space-y-2">
                  {steps.map((step, idx) => (
                    <div
                      key={`${sectionName}-${idx}`}
                      className={`border-l-4 ${priorityBorder(step.priority)} pl-3 py-1`}
                    >
                      <div className="flex items-center gap-2 mb-0.5">
                        <span className="inline-flex h-5 w-5 items-center justify-center rounded-full bg-sh-primary/10 border border-sh-border text-[10px] font-medium text-sh-secondary">
                          {step.priority}
                        </span>
                        <span className="text-sm font-medium text-sh-primary">
                          {step.symptom || `Шаг ${step.priority}`}
                        </span>
                      </div>
                      {step.reason && (
                        <p className="text-xs text-sh-secondary mt-0.5">{step.reason}</p>
                      )}
                      {step.what_to_say && (
                        <p className="text-xs italic text-sh-secondary mt-0.5">
                          «{step.what_to_say}»
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              </Card>
            );
          })}
        </div>
      )}

      {/* ── Analytics Drill-down ───────────────────────────────────── */}
      {categories.length > 0 && (
        <div className="space-y-3">
          <h2 className="text-sm font-medium text-sh-secondary uppercase tracking-wide">
            Аналитика обследований
          </h2>

          {!selectedCategory ? (
            <div className="space-y-2">
              {categories.map((cat) => (
                <button
                  key={cat}
                  onClick={() => setSelectedCategory(cat)}
                  className="w-full text-left bg-sh-surface rounded-xl p-4 hover:bg-sh-primary/5 transition-colors cursor-pointer"
                >
                  <span className="text-sm font-medium text-sh-primary">{cat}</span>
                </button>
              ))}
            </div>
          ) : (
            <div>
              <button
                onClick={() => setSelectedCategory(null)}
                className="text-xs text-sh-accent mb-3 cursor-pointer hover:underline"
              >
                ← Все категории
              </button>
              {analyticsItems.length === 0 ? (
                <p className="text-sm text-sh-secondary">Нет данных по категории «{selectedCategory}»</p>
              ) : (
                <Accordion multiple className="space-y-2">
                  {Array.from(analyticsGroups.entries())
                    .sort(([keyA], [keyB]) => {
                      const [, dateA = ""] = keyA.split("::", 2);
                      const [, dateB = ""] = keyB.split("::", 2);
                      return new Date(dateB).getTime() - new Date(dateA).getTime();
                    })
                    .map(([key, params]) => {
                      const [test_name, date = ""] = key.split("::", 2);
                      const [y, m, d] = date.split("-");
                      const formattedDate = `${d}.${m}.${y}`;
                      return (
                        <AccordionItem key={key} value={key}>
                          <AccordionTrigger className="bg-sh-surface rounded-lg px-4">
                            {test_name} ({formattedDate})
                          </AccordionTrigger>
                          <AccordionContent>
                            <div className="overflow-x-auto bg-sh-surface/50 rounded-b-lg">
                              <table className="w-full text-sm">
                                <thead>
                                  <tr className="border-b border-sh-border/50 text-left text-sh-secondary">
                                    <th className="pb-1.5 pt-2 px-4 font-medium text-xs">Параметр</th>
                                    <th className="pb-1.5 pt-2 px-4 font-medium text-xs">Значение</th>
                                    <th className="pb-1.5 pt-2 px-4 font-medium text-xs">Ед.</th>
                                    <th className="pb-1.5 pt-2 px-4 font-medium text-xs">Реф.</th>
                                  </tr>
                                </thead>
                                <tbody>
                                  {params.map((p, pi) => (
                                    <tr key={`${p.parameter}-${pi}`} className="border-b border-sh-border/30 last:border-0">
                                      <td className="py-3 px-4 text-sm font-medium text-sh-primary">{p.parameter}</td>
                                      <td className={`py-3 px-4 text-sm font-medium ${flagColorClass(p.flag)}`}>{p.value}</td>
                                      <td className="py-3 px-4 text-[11px] text-sh-secondary">{p.unit || "—"}</td>
                                      <td className="py-3 px-4 text-[11px] text-sh-secondary">{p.ref_range || "—"}</td>
                                    </tr>
                                  ))}
                                </tbody>
                              </table>
                            </div>
                          </AccordionContent>
                        </AccordionItem>
                      );
                    })}
                </Accordion>
              )}
            </div>
          )}
        </div>
      )}

      {/* ── Charts Placeholder ─────────────────────────────────────── */}
      <Card className="border border-dashed border-sh-border bg-transparent rounded-2xl p-6 text-center">
        <TrendingUp className="h-8 w-8 text-sh-secondary mx-auto mb-2" />
        <p className="text-sm text-sh-secondary">
          Графики и тренды показателей — скоро
        </p>
      </Card>
    </motion.div>
  );
}
