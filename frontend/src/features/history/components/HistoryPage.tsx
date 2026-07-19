import { PageHeader, SectionHeader, GlassCard, StatusPill } from "../../../components/apple";
import { mockLabs } from "../../../lib/mock-data";
import { BarChart } from "../../../components/apple";

/** History / analytics view with mock lab trend charts */
export default function HistoryPage() {
  const altTrend = [
    { label: "янв", value: 38, color: "#34C759" },
    { label: "мар", value: 41, color: "#34C759" },
    { label: "май", value: 48, color: "#FF9500" },
    { label: "июн", value: 52, color: "#FF9500" },
    { label: "июл", value: 45, color: "#FFCC00" },
  ];

  return (
    <div className="page-shell section-gap">
      <PageHeader title="Аналитика" subtitle="Тренды" />

      <GlassCard padding="lg">
        <div className="flex items-start justify-between mb-4">
          <div>
            <p className="text-[13px] font-semibold text-[#8E8E93]">АЛТ</p>
            <p className="metric-value text-[34px] mt-1">
              52 <span className="text-[15px] font-medium text-[#8E8E93]">Ед/л</span>
            </p>
          </div>
          <StatusPill tone="warn">выше нормы</StatusPill>
        </div>
        <BarChart values={altTrend} height={130} />
        <p className="caption mt-4 leading-relaxed">
          Референс до 41 Ед/л. Динамика связана с нагрузкой на печень — см. стратегию снижения веса.
        </p>
      </GlassCard>

      <section>
        <SectionHeader title="Все исследования" />
        <div className="space-y-3">
          {mockLabs.map((lab) => (
            <GlassCard key={lab.id} padding="md" pressable>
              <div className="flex justify-between items-start gap-2">
                <div>
                  <p className="text-[16px] font-semibold">{lab.name}</p>
                  <p className="text-[13px] text-[#8E8E93] mt-0.5">{lab.date}</p>
                </div>
                <StatusPill
                  tone={lab.status === "normal" ? "ok" : lab.status === "attention" ? "warn" : "danger"}
                >
                  {lab.category}
                </StatusPill>
              </div>
              <p className="text-[14px] text-[#8E8E93] mt-2">{lab.summary}</p>
            </GlassCard>
          ))}
        </div>
      </section>
    </div>
  );
}
