import { useRef, useState, useCallback, useEffect } from "react";
import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

interface SegmentedControlProps {
  segments: { key: string; label: string }[];
  selected: string;
  onSelect: (key: string) => void;
  className?: string;
}

function SegmentedControl({
  segments,
  selected,
  onSelect,
  className,
}: SegmentedControlProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [indicatorStyle, setIndicatorStyle] = useState<{
    left: number;
    width: number;
  }>({ left: 0, width: 0 });

  const updateIndicator = useCallback(() => {
    const container = containerRef.current;
    if (!container) return;

    const selectedIndex = segments.findIndex((s) => s.key === selected);
    if (selectedIndex === -1) return;

    const buttons = container.querySelectorAll<HTMLButtonElement>("button");
    const button = buttons[selectedIndex];
    if (!button) return;

    const containerRect = container.getBoundingClientRect();
    const buttonRect = button.getBoundingClientRect();

    setIndicatorStyle({
      left: buttonRect.left - containerRect.left,
      width: buttonRect.width,
    });
  }, [selected, segments]);

  useEffect(() => {
    updateIndicator();
  }, [updateIndicator]);

  useEffect(() => {
    const handleResize = () => updateIndicator();
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, [updateIndicator]);

  return (
    <div
      ref={containerRef}
      className={cn(
        "relative flex rounded-lg bg-sh-surface p-0.5 h-9",
        className,
      )}
    >
      <motion.div
        className="absolute inset-y-0.5 z-0 rounded-md bg-[#60A5FA]"
        layoutId="segmented-control-indicator"
        transition={{ type: "spring", stiffness: 500, damping: 35 }}
        style={{
          left: indicatorStyle.left,
          width: indicatorStyle.width,
        }}
      />
      {segments.map((segment) => {
        const isActive = segment.key === selected;
        return (
          <button
            key={segment.key}
            type="button"
            onClick={() => onSelect(segment.key)}
            className={cn(
              "relative z-10 flex-1 px-3 py-1.5 text-sm font-medium text-center transition-colors cursor-pointer",
              "focus:outline-none focus-visible:ring-2 focus-visible:ring-sh-accent rounded-md",
              isActive ? "text-white" : "text-sh-secondary hover:text-sh-primary",
            )}
          >
            {segment.label}
          </button>
        );
      })}
    </div>
  );
}

export { SegmentedControl };
export type { SegmentedControlProps };
