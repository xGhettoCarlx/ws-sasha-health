/**
 * Telegram-navigation back button.
 *
 * Automatically shows/hides the native Telegram back button
 * and falls back to a custom styled button outside Telegram.
 *
 * Usage:
 *   <TelegramBackButton to="/profile" />
 *   <TelegramBackButton />           // defaults to navigate(-1)
 */

import { useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { backButton } from "@telegram-apps/sdk-react";
import { ArrowLeft } from "lucide-react";

interface Props {
  /** Target route. If omitted, navigates back in history. */
  to?: string;
  /** Label shown on native Telegram button (default: "Назад") */
  label?: string;
}

function isTelegram(): boolean {
  if (typeof window === "undefined") return false;
  return !!(window as any).Telegram?.WebApp;
}

export default function TelegramBackButton({ to, label = "Назад" }: Props) {
  const navigate = useNavigate();

  const handleClick = useCallback(() => {
    if (to) {
      navigate(to);
    } else {
      navigate(-1);
    }
  }, [to, navigate]);

  useEffect(() => {
    if (!isTelegram()) return;

    try {
      backButton.mount();
      backButton.show();
      backButton.onClick(handleClick);
    } catch {
      // SDK not ready yet — safe to ignore
    }

    return () => {
      try {
        backButton.offClick(handleClick);
        backButton.hide();
      } catch {
        // cleanup
      }
    };
  }, [handleClick]);

  // Outside Telegram: render a custom back button
  if (!isTelegram()) {
    return (
      <button
        onClick={handleClick}
        className="inline-flex items-center gap-1.5 rounded-lg px-3 py-2 text-sm font-medium
                   transition-colors hover:bg-foreground/5 active:scale-95"
        style={{ color: "var(--tg-theme-link-color, #2481cc)" }}
        aria-label={label}
      >
        <ArrowLeft className="h-4 w-4" />
        <span>{label}</span>
      </button>
    );
  }

  // In Telegram: native back button is shown, no custom element rendered
  return null;
}
