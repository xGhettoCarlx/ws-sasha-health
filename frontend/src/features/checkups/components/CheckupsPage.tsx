import { useQuery } from "@tanstack/react-query";
import { GlassCard, PageHeader, SectionHeader, StatusPill } from "../../../components/apple";
import { fetchCheckups, type CheckupItem } from "../../../lib/navigator-api";

export default function CheckupsPage() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["checkups"],
    queryFn: fetchCheckups,
  });

  return (
    <div className="page-shell section-gap">
      <PageHeader subtitle="Скрининг" title="Чекапы" />
      <p className="text-[13px] text-[#8E8E93] -mt-2">
        Ежегодные и полугодовые процедуры из чекапы.md агента
      </p>

      {isLoading && (
        <GlassCard padding="lg">
          <p className="text-[#8E8E93]">Загрузка…</p>
        </GlassCard>
      )}
      {isError && (
        <GlassCard padding="lg">
          <p className="text-[#FF3B30]">Не удалось загрузить чекапы</p>
        </GlassCard>
      )}

      {data && (
        <>
          <div className="grid grid-cols-3 gap-2">
            <Stat label="Ок" value={data.summary.ok} tone="ok" />
            <Stat label="План" value={data.summary.plan} tone="plan" />
            <Stat label="Пора" value={data.summary.overdue} tone="overdue" />
          </div>

          <section>
            <SectionHeader title="Список" action={<span className="caption">{data.count}</span>} />
            <div className="space-y-2">
              {data.items.map((item) => (
                <CheckupRow key={item.id} item={item} />
              ))}
            </div>
          </section>
        </>
      )}
    </div>
  );
}

function Stat({
  label,
  value,
  tone,
}: {
  label: string;
  value: number;
  tone: "ok" | "plan" | "overdue";
}) {
  const color =
    tone === "ok" ? "#34C759" : tone === "plan" ? "#FF9500" : "#FF3B30";
  return (
    <GlassCard padding="md" className="text-center">
      <p className="text-[22px] font-semibold" style={{ color }}>
        {value}
      </p>
      <p className="text-[12px] text-[#8E8E93] font-medium">{label}</p>
    </GlassCard>
  );
}

function CheckupRow({ item }: { item: CheckupItem }) {
  const tone =
    item.status === "ok" ? "ok" : item.status === "plan" ? "warn" : "danger";
  return (
    <GlassCard padding="md">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-[15px] font-semibold leading-snug">{item.name}</p>
          <p className="text-[13px] text-[#8E8E93] mt-1">
            интервал {item.interval}
            {item.last_date ? ` · последний ${item.last_date}` : " · нет данных"}
          </p>
          {item.due_in_days != null && (
            <p className="text-[12px] text-[#AEAEB2] mt-0.5">
              {item.due_in_days >= 0
                ? `ещё ~${item.due_in_days} дн.`
                : `просрочено на ${Math.abs(item.due_in_days)} дн.`}
            </p>
          )}
        </div>
        <StatusPill tone={tone as "ok" | "warn" | "danger"}>
          {item.status_label}
        </StatusPill>
      </div>
    </GlassCard>
  );
}
