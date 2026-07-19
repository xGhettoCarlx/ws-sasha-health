import { cn } from "../../lib/utils";

export function PageSkeleton({
  variant: _variant,
  className,
}: {
  variant?: string;
  className?: string;
}) {
  return (
    <div className={cn("page-shell space-y-5 animate-pulse", className)}>
      <div className="h-10 w-40 rounded-xl bg-white/80" />
      <div className="h-36 rounded-[20px] bg-white shadow-sm" />
      <div className="grid grid-cols-2 gap-3">
        <div className="h-32 rounded-[20px] bg-white" />
        <div className="h-32 rounded-[20px] bg-white" />
        <div className="h-32 rounded-[20px] bg-white" />
        <div className="h-32 rounded-[20px] bg-white" />
      </div>
      <div className="h-48 rounded-[20px] bg-white" />
    </div>
  );
}
