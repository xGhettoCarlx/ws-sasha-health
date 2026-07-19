import { AlertCircle } from "lucide-react";
import { GlassCard } from "./apple";

export function ErrorState({
  message = "Что-то пошло не так",
  onRetry,
}: {
  message?: string;
  onRetry?: () => void;
}) {
  return (
    <div className="page-shell flex items-center justify-center min-h-[60dvh]">
      <GlassCard padding="lg" className="w-full text-center py-10">
        <div className="w-14 h-14 rounded-full bg-[#FFEBEA] flex items-center justify-center mx-auto mb-4">
          <AlertCircle className="w-7 h-7 text-[#FF3B30]" />
        </div>
        <p className="text-[17px] font-semibold">Ошибка загрузки</p>
        <p className="text-[14px] text-[#8E8E93] mt-2 leading-relaxed">{message}</p>
        {onRetry && (
          <button
            type="button"
            onClick={onRetry}
            className="mt-6 h-11 px-6 rounded-[12px] bg-[#007AFF] text-white text-[16px] font-semibold pressable"
          >
            Повторить
          </button>
        )}
      </GlassCard>
    </div>
  );
}
