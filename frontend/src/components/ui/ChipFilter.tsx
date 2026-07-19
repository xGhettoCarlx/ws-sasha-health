import { cn } from "@/lib/utils";

interface ChipFilterProps {
  items: { key: string; label: string }[];
  selected: string | null;
  onSelect: (key: string) => void;
  className?: string;
}

function ChipFilter({ items, selected, onSelect, className }: ChipFilterProps) {
  return (
    <div className={cn("flex flex-wrap gap-2", className)}>
      {items.map((item) => {
        const isActive = item.key === selected;
        return (
          <button
            key={item.key}
            type="button"
            onClick={() => onSelect(item.key)}
            className={cn(
              "px-4 py-1.5 rounded-full text-sm font-medium transition-colors cursor-pointer border",
              "focus:outline-none focus-visible:ring-2 focus-visible:ring-sh-accent focus-visible:ring-offset-1",
              isActive
                ? "bg-[#60A5FA] text-white border-[#3B82F6]"
                : "bg-transparent text-sh-secondary border-sh-border hover:border-sh-secondary hover:text-sh-primary",
            )}
          >
            {item.label}
          </button>
        );
      })}
    </div>
  );
}

export { ChipFilter };
export type { ChipFilterProps };
