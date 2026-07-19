import { NavLink, useLocation } from "react-router-dom";
import { House, GitBranch, CalendarRange, Shield } from "lucide-react";
import { cn } from "../../lib/utils";

interface Tab {
  to: string;
  label: string;
  icon: React.FC<React.ComponentProps<"svg">>;
}

/** Purged: Жалобы, Маршрут, Троян, Pre-Visit — DoD HEALTH-APP-UX-PURGE */
const tabs: Tab[] = [
  { to: "/dashboard", label: "Обзор", icon: House },
  { to: "/pipeline", label: "Конвейер", icon: GitBranch },
  { to: "/timeline", label: "Лента", icon: CalendarRange },
  { to: "/insurance", label: "Страховка", icon: Shield },
];

export function BottomNav() {
  const { pathname } = useLocation();

  return (
    <nav
      className="fixed bottom-0 left-0 right-0 z-50"
      style={{ paddingBottom: "var(--safe-area-inset-bottom, 0px)" }}
    >
      <div className="max-w-[480px] mx-auto px-3 pb-2">
        <div className="glass-nav rounded-[24px] h-[64px] flex items-center justify-around px-1">
          {tabs.map((tab) => {
            const active =
              pathname === tab.to ||
              (tab.to !== "/dashboard" && pathname.startsWith(tab.to));
            const Icon = tab.icon;

            return (
              <NavLink
                key={tab.to}
                to={tab.to}
                className={cn(
                  "relative flex flex-col items-center justify-center gap-0.5 flex-1 h-full rounded-2xl pressable",
                  active ? "text-[#007AFF]" : "text-[#8E8E93]",
                )}
              >
                {active && (
                  <span className="absolute inset-x-2 top-1.5 bottom-1.5 rounded-2xl bg-[#007AFF]/[0.08]" />
                )}
                <Icon
                  className="w-[22px] h-[22px] relative"
                  strokeWidth={active ? 2.4 : 1.8}
                />
                <span
                  className={cn(
                    "text-[10px] relative leading-none",
                    active ? "font-semibold" : "font-medium",
                  )}
                >
                  {tab.label}
                </span>
              </NavLink>
            );
          })}
        </div>
      </div>
    </nav>
  );
}
