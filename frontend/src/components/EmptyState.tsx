import type { ReactNode } from "react";
import { Inbox } from "lucide-react";
import { GlassCard } from "./apple";

export function EmptyState({
  title = "Пока пусто",
  description = "Данные появятся после первой записи",
  icon,
  action,
}: {
  title?: string;
  description?: string;
  icon?: ReactNode;
  action?: ReactNode;
}) {
  return (
    <GlassCard padding="lg" className="flex flex-col items-center text-center py-12">
      <div className="w-14 h-14 rounded-full bg-[#F2F2F7] flex items-center justify-center mb-4 text-[#8E8E93]">
        {icon ?? <Inbox className="w-7 h-7" strokeWidth={1.5} />}
      </div>
      <p className="text-[17px] font-semibold">{title}</p>
      <p className="text-[14px] text-[#8E8E93] mt-1.5 max-w-[240px] leading-relaxed">
        {description}
      </p>
      {action && <div className="mt-5">{action}</div>}
    </GlassCard>
  );
}
