import { type ReactNode, useEffect } from "react";
import { BrowserRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  init,
  miniApp,
  themeParams,
  useSignal,
  bindMiniAppCssVars,
  bindThemeParamsCssVars,
} from "@telegram-apps/sdk-react";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000,
      gcTime: 30 * 60 * 1000,
      // Backend may be restarting under launchd KeepAlive — retry briefly
      retry: 2,
      retryDelay: (attempt) => Math.min(1000 * 2 ** attempt, 4000),
      refetchOnWindowFocus: true,
    },
  },
});

function isTelegram(): boolean {
  if (typeof window === "undefined") return false;
  return !!(window as any).Telegram?.WebApp;
}

function ThemeInitializer({ children }: { children: ReactNode }) {
  // Always call hook unconditionally (Rules of Hooks) — signal returns default before init()
  const isDark = useSignal(miniApp.isDark);

  useEffect(() => {
    const root = document.documentElement;
    if (isDark) {
      root.classList.add("dark");
    } else {
      root.classList.remove("dark");
    }
  }, [isDark]);

  return <>{children}</>;
}

function VersionGate({ children }: { children: ReactNode }) {
  useEffect(() => {
    const VERSION_KEY = "sh-app-version";
    const VERSION_URL = "/sh/version.json";

    async function checkVersion() {
      try {
        const res = await fetch(`${VERSION_URL}?t=${Date.now()}`, { cache: "no-store" });
        if (!res.ok) return;
        const data = await res.json();
        const remoteVersion = data.version;
        if (!remoteVersion) return;

        const localVersion = localStorage.getItem(VERSION_KEY);
        if (localVersion && localVersion !== remoteVersion) {
          console.log(`[VersionGate] Version mismatch: ${localVersion} → ${remoteVersion}, reloading.`);
          localStorage.setItem(VERSION_KEY, remoteVersion);
          window.location.reload();
          return;
        }
        localStorage.setItem(VERSION_KEY, remoteVersion);
      } catch (err) {
        console.warn("[VersionGate] Version check failed:", err);
      }
    }

    checkVersion();
  }, []);

  return <>{children}</>;
}

function TelegramSDKInit({ children }: { children: ReactNode }) {
  useEffect(() => {
    if (!isTelegram()) return;

    try {
      init({ acceptCustomStyles: true });
      themeParams.mount();
      bindThemeParamsCssVars();
      miniApp.mount();
      bindMiniAppCssVars();
    } catch (err) {
      console.warn("[Providers] Telegram SDK init failed — running in non-Telegram mode:", err);
    }
  }, []);

  return <>{children}</>;
}

interface ProvidersProps {
  children: ReactNode;
}

export function Providers({ children }: ProvidersProps) {
  return (
    <VersionGate>
      <QueryClientProvider client={queryClient}>
        <TelegramSDKInit>
          <ThemeInitializer>
            <BrowserRouter basename="/sh">{children}</BrowserRouter>
          </ThemeInitializer>
        </TelegramSDKInit>
      </QueryClientProvider>
    </VersionGate>
  );
}
