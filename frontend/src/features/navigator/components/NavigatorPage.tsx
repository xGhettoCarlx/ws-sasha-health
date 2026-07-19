import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { GlassCard, PageHeader, SectionHeader, StatusPill } from "../../../components/apple";
import { fetchNavigator, type NavRoute } from "../../../lib/navigator-api";

export default function NavigatorPage() {
  const [q, setQ] = useState("");
  const [submitted, setSubmitted] = useState<string | undefined>(undefined);

  const { data, isFetching } = useQuery({
    queryKey: ["navigator", submitted ?? ""],
    queryFn: () => fetchNavigator(submitted),
  });

  return (
    <div className="page-shell section-gap">
      <PageHeader subtitle="Маршрут" title="Навигатор" />
      <p className="text-[13px] text-[#8E8E93] -mt-2">
        Симптомы / анализы → какой врач → покрытие страховкой
      </p>

      <GlassCard padding="lg">
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Опишите симптом или оставьте пустым (копилка)"
          className="w-full h-11 rounded-2xl bg-black/[0.04] px-3 text-[15px] outline-none focus:ring-2 focus:ring-[#007AFF]/40"
        />
        <button
          type="button"
          onClick={() => setSubmitted(q.trim() || undefined)}
          className="mt-3 w-full h-11 rounded-2xl bg-[#007AFF] text-white font-semibold pressable"
        >
          {isFetching ? "Считаю…" : "Подобрать маршрут"}
        </button>
      </GlassCard>

      {data && (
        <>
          <section>
            <SectionHeader
              title="Куда идти"
              action={
                <span className="caption">
                  жалоб: {data.open_complaints}
                </span>
              }
            />
            <div className="space-y-2">
              {data.routes.map((r) => (
                <RouteCard key={r.specialty + r.score} route={r} />
              ))}
              {data.routes.length === 0 && (
                <GlassCard padding="lg">
                  <p className="text-[14px] text-[#8E8E93] text-center">
                    Добавьте жалобы в копилку или введите симптом
                  </p>
                </GlassCard>
              )}
            </div>
          </section>

          <section>
            <SectionHeader title="Не покрывается ДМС" />
            <GlassCard padding="md">
              <div className="flex flex-wrap gap-1.5">
                {data.insurance.not_covered.map((x) => (
                  <span
                    key={x}
                    className="text-[12px] px-2.5 py-1 rounded-full bg-black/5 text-[#8E8E93]"
                  >
                    {x}
                  </span>
                ))}
              </div>
            </GlassCard>
          </section>

          {data.insurance.policies?.[0] != null && (
            <section>
              <SectionHeader title="Полис" />
              <GlassCard padding="md">
                <p className="text-[15px] font-semibold">
                  {(data.insurance.policies[0] as { policy?: string }).policy}
                </p>
                <p className="text-[13px] text-[#8E8E93] mt-1">
                  остаток{" "}
                  {Number(
                    (data.insurance.policies[0] as { remaining?: number })
                      .remaining ?? 0,
                  ).toLocaleString("ru-RU")}{" "}
                  BYN · до{" "}
                  {(data.insurance.policies[0] as { expiry?: string }).expiry}
                </p>
              </GlassCard>
            </section>
          )}
        </>
      )}
    </div>
  );
}

function RouteCard({ route }: { route: NavRoute }) {
  const covered =
    route.covered === true || route.covered === "limited";
  return (
    <GlassCard padding="md">
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="text-[16px] font-semibold">{route.specialty}</p>
          <p className="text-[13px] text-[#8E8E93] mt-1 leading-snug">
            {route.note}
          </p>
          {route.prep?.length > 0 && (
            <ul className="mt-2 space-y-0.5">
              {route.prep.map((p) => (
                <li key={p} className="text-[12px] text-[#1C1C1E]">
                  · {p}
                </li>
              ))}
            </ul>
          )}
        </div>
        <StatusPill tone={covered ? "ok" : "danger"}>
          {route.covered === "limited"
            ? "лимит"
            : covered
              ? "покрыто"
              : "нет"}
        </StatusPill>
      </div>
    </GlassCard>
  );
}
