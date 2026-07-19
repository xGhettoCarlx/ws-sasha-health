import { type FC } from "react";
import { useNavigate } from "react-router-dom";
import { Heart, Sparkles } from "lucide-react";
import { useAuthStore } from "../../../stores/authStore";
import { GlassCard } from "../../../components/apple";

/** Owner Telegram id — always allowed by FastAPI admin bypass. */
const OWNER_USER_ID = 80101636;

export const LoginPage: FC = () => {
  const navigate = useNavigate();
  const setAuth = useAuthStore((s) => s.setAuth);

  function enterApp() {
    sessionStorage.setItem(
      "web_auth",
      JSON.stringify({
        user_id: OWNER_USER_ID,
        first_name: "Александр",
        local: true,
      }),
    );
    setAuth(OWNER_USER_ID, "web", "");
    navigate("/dashboard", { replace: true });
  }

  return (
    <div className="min-h-dvh flex flex-col items-center justify-center px-6 py-12 relative overflow-hidden">
      <div
        className="absolute inset-0 -z-10"
        style={{
          background:
            "radial-gradient(80% 50% at 50% 0%, rgba(0,122,255,0.14), transparent 60%), radial-gradient(60% 40% at 80% 80%, rgba(255,45,85,0.1), transparent 50%), #F2F2F7",
        }}
      />

      <div className="w-full max-w-[360px] fade-up">
        <div className="flex flex-col items-center text-center mb-10">
          <div
            className="w-[88px] h-[88px] rounded-[28px] flex items-center justify-center mb-6 shadow-[var(--shadow-float)]"
            style={{
              background: "linear-gradient(145deg, #FF2D55 0%, #FF6B8A 50%, #FF9500 100%)",
            }}
          >
            <Heart className="w-11 h-11 text-white" fill="white" strokeWidth={1.5} />
          </div>
          <h1 className="large-title mb-2">Sasha Health</h1>
          <p className="text-[17px] text-[#8E8E93] leading-relaxed max-w-[280px]">
            Медицинский дневник — данные из чата с агентом и файлов data/.
          </p>
        </div>

        <GlassCard variant="glass" padding="lg" className="space-y-4">
          <button
            type="button"
            onClick={enterApp}
            className="w-full h-[52px] rounded-[14px] bg-[#007AFF] text-white text-[17px] font-semibold pressable shadow-[0_8px_24px_rgba(0,122,255,0.35)] focus-ring"
          >
            Открыть
          </button>

          <p className="text-center text-[13px] text-[#8E8E93] flex items-center justify-center gap-1.5">
            <Sparkles className="w-3.5 h-3.5 text-[#FF9500]" />
            Реальные файлы агента · чекапы · жалобы · Pre-Visit
          </p>
        </GlassCard>

        <p className="mt-8 text-center footnote">
          В Telegram Mini App вход через initData.
          <br />
          В браузере — локальный доступ владельца.
        </p>
      </div>
    </div>
  );
};

export default LoginPage;
