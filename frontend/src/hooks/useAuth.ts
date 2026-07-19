import { useCallback, useEffect, useState } from "react";
import { useAuthStore } from "../stores/authStore";
import { apiPost } from "../lib/api";
import { DEMO_MODE } from "../lib/mock-data";

interface AuthState {
  isReady: boolean;
  isTelegram: boolean;
  isPWA: boolean;
  userId: number;
  initData: string;
  isDemo: boolean;
}

function getTelegramWebApp(): any {
  if (typeof window === "undefined") return null;
  return (window as any).Telegram?.WebApp ?? null;
}

function detectPWA(): boolean {
  if (typeof window === "undefined") return false;
  return window.matchMedia("(display-mode: standalone)").matches;
}

/**
 * Auth detection with DEMO_MODE fallback for Apple UI prototype.
 * When API/Telegram is unavailable, auto-approves a demo user so all screens render.
 */
export function useAuth(): AuthState {
  const [isReady, setIsReady] = useState(false);
  const [isTelegram, setIsTelegram] = useState(false);
  const [isPWA, setIsPWA] = useState(false);
  const [userId, setUserId] = useState(0);
  const [initData, setInitData] = useState("");
  const [isDemo, setIsDemo] = useState(false);

  const { setAuth, setPending, authMethod } = useAuthStore();

  const enterDemo = useCallback(() => {
    setIsDemo(true);
    setUserId(900001);
    setAuth(900001, "web", "");
    sessionStorage.setItem(
      "web_auth",
      JSON.stringify({ user_id: 900001, first_name: "Demo", demo: true }),
    );
  }, [setAuth]);

  const authenticate = useCallback(async () => {
    const tg = getTelegramWebApp();
    const pwa = detectPWA();
    setIsPWA(pwa);

    if (tg?.initData) {
      setIsTelegram(true);
      const rawInitData = tg.initData || "";
      const unsafeUser = tg.initDataUnsafe?.user;
      setInitData(rawInitData);
      if (unsafeUser?.id) setUserId(unsafeUser.id);
      sessionStorage.setItem("tg_init_data", rawInitData);

      try {
        const result = await apiPost<{ status: string; user_id: number }>(
          "/api/auth/pwa",
          { init_data: rawInitData },
        );
        if (result.status === "approved") {
          setAuth(result.user_id, "telegram", rawInitData);
        } else if (result.status === "pending_approval") {
          setPending(result.user_id, "telegram", rawInitData);
        }
      } catch {
        if (unsafeUser?.id) setAuth(unsafeUser.id, "telegram", rawInitData);
        else if (DEMO_MODE) enterDemo();
      }
      setIsReady(true);
      return;
    }

    // Stored web/demo auth
    const webAuthRaw = sessionStorage.getItem("web_auth");
    if (webAuthRaw) {
      try {
        const webAuth = JSON.parse(webAuthRaw);
        if (webAuth?.user_id) {
          setUserId(webAuth.user_id);
          setIsDemo(!!webAuth.demo);
          setAuth(webAuth.user_id, "web", "");
          setIsReady(true);
          return;
        }
      } catch {
        sessionStorage.removeItem("web_auth");
      }
    }

    // PWA stored initData
    if (pwa) {
      const stored = sessionStorage.getItem("tg_init_data");
      if (stored) {
        setInitData(stored);
        try {
          const result = await apiPost<{ status: string; user_id: number }>(
            "/api/auth/pwa",
            { init_data: stored },
          );
          if (result.status === "approved") {
            setAuth(result.user_id, "pwa", stored);
          } else if (result.status === "pending_approval") {
            setPending(result.user_id, "pwa", stored);
          }
        } catch {
          if (DEMO_MODE) enterDemo();
        }
        setIsReady(true);
        return;
      }
    }

    // Browser / local shell without Telegram: personal app uses owner web auth
    // so production `/sh/` serves agent markdown (was tree-shaken when DEV-only).
    // VITE_LOCAL_AUTH=false disables this for multi-tenant deploys.
    const localAuthOff = import.meta.env.VITE_LOCAL_AUTH === "false";
    if (!localAuthOff) {
      const localId = 80101636;
      setUserId(localId);
      setAuth(localId, "web", "");
      sessionStorage.setItem(
        "web_auth",
        JSON.stringify({ user_id: localId, first_name: "Sasha", local: true }),
      );
      setIsReady(true);
      return;
    }

    // Optional mock-only prototype
    if (DEMO_MODE) {
      enterDemo();
    }
    setIsReady(true);
  }, [setAuth, setPending, enterDemo]);

  useEffect(() => {
    if (authMethod === "none") {
      authenticate();
    } else {
      setIsReady(true);
    }
  }, [authenticate, authMethod]);

  return { isReady, isTelegram, isPWA, userId, initData, isDemo };
}
