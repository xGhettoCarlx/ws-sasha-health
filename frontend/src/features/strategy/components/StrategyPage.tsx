import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { Flag } from "lucide-react";
import {
  GlassCard,
  PageHeader,
  SectionHeader,
  StatusPill,
} from "../../../components/apple";
import { fetchStrategy } from "../../../lib/services";

interface StrategySection {
  title: string;
  bullets: string[];
}

function parseStrategyBody(content?: string | null): StrategySection[] {
  if (!content?.trim()) return [];
  const sections: StrategySection[] = [];
  let current: StrategySection | null = null;
  for (const raw of content.split(/\r?\n/)) {
    const line = raw.trim();
    if (!line) continue;
    const h = line.match(/^##\s+(.+)/);
    if (h?.[1]) {
      current = { title: h[1].trim(), bullets: [] };
      sections.push(current);
      continue;
    }
    if (!current) {
      current = { title: "План", bullets: [] };
      sections.push(current);
    }
    const bullet = line.replace(/^[\*\-•]\s+/, "").trim();
    if (bullet) current.bullets.push(bullet);
  }
  return sections;
}

export default function StrategyPage() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["strategy"],
    queryFn: fetchStrategy,
    staleTime: 60_000,
  });

  const sections = useMemo(
    () => parseStrategyBody(data?.content),
    [data?.content],
  );

  return (
    <div className="page-shell section-gap">
      <PageHeader
        title="План"
        subtitle="Стратегия"
        trailing={
          data?.updated ? (
            <StatusPill tone="info">обн. {data.updated}</StatusPill>
          ) : undefined
        }
      />

      {isLoading && (
        <GlassCard padding="lg">
          <p className="text-[#8E8E93]">Загрузка стратегия.md…</p>
        </GlassCard>
      )}
      {isError && (
        <GlassCard padding="lg">
          <p className="text-[#FF3B30]">Не удалось загрузить стратегию</p>
        </GlassCard>
      )}

      {data && (
        <GlassCard
          padding="lg"
          style={{
            background:
              "linear-gradient(145deg, rgba(0,122,255,0.12), rgba(88,86,214,0.1))",
          }}
          className="!bg-transparent border border-white/60 shadow-[var(--shadow-card)]"
        >
          <p className="text-[13px] font-semibold text-[#007AFF] mb-1">
            Фокус {data.updated?.slice(0, 4) || "2026"}
          </p>
          <h2 className="text-[22px] font-bold tracking-tight leading-snug">
            {data.title || "Стратегия"}
          </h2>
        </GlassCard>
      )}

      {sections.map((sec) => (
        <section key={sec.title}>
          <SectionHeader title={sec.title} />
          <GlassCard padding="none">
            {sec.bullets.map((item, i) => (
              <div key={i}>
                {i > 0 && <div className="hairline ml-12" />}
                <div className="flex items-start gap-3 px-4 py-3.5">
                  <Flag
                    className="w-5 h-5 text-[#007AFF] shrink-0 mt-0.5"
                    strokeWidth={1.8}
                  />
                  <p className="text-[15px] leading-snug text-[#1C1C1E]">{item}</p>
                </div>
              </div>
            ))}
          </GlassCard>
        </section>
      ))}

      {data && sections.length === 0 && (
        <GlassCard padding="lg">
          <p className="text-[14px] text-[#8E8E93] whitespace-pre-wrap">
            {data.content || "Стратегия пуста"}
          </p>
        </GlassCard>
      )}
    </div>
  );
}
