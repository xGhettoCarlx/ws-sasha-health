import { Outlet, useLocation, Navigate } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";
import { useAuth } from "../hooks/useAuth";
import { useAuthStore } from "../stores/authStore";
import { BottomNav } from "../components/nav/BottomNav";
import { Loader2, ShieldAlert } from "lucide-react";

function AuthSkeleton() {
  return (
    <div className="flex flex-col items-center justify-center min-h-dvh gap-4 bg-[#F2F2F7]">
      <div className="w-14 h-14 rounded-[18px] bg-white shadow-[var(--shadow-card)] flex items-center justify-center">
        <Loader2 className="w-7 h-7 animate-spin text-[#007AFF]" />
      </div>
      <p className="text-[15px] text-[#8E8E93] font-medium">Загрузка…</p>
    </div>
  );
}

function PendingApprovalScreen() {
  const userId = useAuthStore((s) => s.userId);

  return (
    <div className="flex flex-col items-center justify-center min-h-dvh gap-5 px-8 text-center bg-[#F2F2F7]">
      <div className="w-16 h-16 rounded-full glass-thick flex items-center justify-center">
        <ShieldAlert className="w-8 h-8 text-[#FF9500]" />
      </div>
      <h2 className="text-[22px] font-semibold tracking-tight">Заявка на рассмотрении</h2>
      <p className="text-[15px] text-[#8E8E93] max-w-xs leading-relaxed">
        Администратор проверит ваш ID и откроет доступ.
        {userId > 0 && (
          <>
            <br />
            <span className="font-mono text-[13px] text-[#1C1C1E]">ID {userId}</span>
          </>
        )}
      </p>
    </div>
  );
}

const pageTransition = {
  initial: { opacity: 0, y: 12 },
  animate: { opacity: 1, y: 0 },
  exit: { opacity: 0, y: -8 },
  transition: { duration: 0.28, ease: [0.22, 1, 0.36, 1] as const },
};

export function AppShell() {
  const { isReady } = useAuth();
  const isApproved = useAuthStore((s) => s.isApproved);
  const isPending = useAuthStore((s) => s.isPending);
  const isAuthenticated = useAuthStore((s) => s.authMethod !== "none");
  const location = useLocation();

  if (!isReady) return <AuthSkeleton />;
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  if (isPending && !isApproved) return <PendingApprovalScreen />;

  return (
    <div className="flex flex-col min-h-dvh max-w-[480px] mx-auto relative">
      <div
        className="pointer-events-none fixed inset-0 max-w-[480px] mx-auto -z-10"
        style={{
          background:
            "radial-gradient(100% 60% at 0% 0%, rgba(0,122,255,0.07), transparent 55%), radial-gradient(80% 50% at 100% 10%, rgba(255,45,85,0.05), transparent 50%), #F2F2F7",
        }}
      />

      <main className="flex-1 overflow-y-auto scrollbar-hidden">
        <AnimatePresence mode="wait">
          <motion.div
            key={location.pathname}
            initial={pageTransition.initial}
            animate={pageTransition.animate}
            exit={pageTransition.exit}
            transition={pageTransition.transition}
          >
            <Outlet />
          </motion.div>
        </AnimatePresence>
      </main>

      <BottomNav />
    </div>
  );
}
