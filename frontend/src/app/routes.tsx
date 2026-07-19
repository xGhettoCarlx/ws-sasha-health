import { lazy, Suspense, type ReactNode } from "react";
import { Route, Routes, Navigate } from "react-router-dom";
import { AppShell } from "./AppShell";
import { PageSkeleton } from "../components/ui/PageSkeleton";

const LoginPage = lazy(() => import("../features/login/components/LoginPage"));
const DashboardPage = lazy(() =>
  import("../features/dashboard/components/DashboardPage").then((m) => ({
    default: m.DashboardPage,
  })),
);
const RecordsPage = lazy(() => import("../features/records/components/RecordsPage"));
const MedicationsPage = lazy(
  () => import("../features/medications/components/MedicationsPage"),
);
const HistoryPage = lazy(() => import("../features/history/components/HistoryPage"));
const ProfilePage = lazy(() => import("../features/profile/components/ProfilePage"));
const StrategyPage = lazy(() => import("../features/strategy/components/StrategyPage"));
const CheckupsPage = lazy(
  () => import("../features/checkups/components/CheckupsPage"),
);
const ComplaintsPage = lazy(
  () => import("../features/complaints/components/ComplaintsPage"),
);
const NavigatorPage = lazy(
  () => import("../features/navigator/components/NavigatorPage"),
);
const PipelinePage = lazy(
  () => import("../features/pipeline/components/PipelinePage"),
);
const TimelinePage = lazy(
  () => import("../features/timeline/components/TimelinePage"),
);
const InsurancePage = lazy(
  () => import("../features/insurance/components/InsurancePage"),
);

function SuspensePage({ children }: { children: ReactNode }) {
  return <Suspense fallback={<PageSkeleton />}>{children}</Suspense>;
}

export const routes: ReactNode = (
  <Routes>
    <Route
      path="login"
      element={
        <SuspensePage>
          <LoginPage />
        </SuspensePage>
      }
    />

    <Route element={<AppShell />}>
      <Route index element={<Navigate to="/dashboard" replace />} />
      <Route
        path="dashboard"
        element={
          <SuspensePage>
            <DashboardPage />
          </SuspensePage>
        }
      />
      <Route
        path="pipeline"
        element={
          <SuspensePage>
            <PipelinePage />
          </SuspensePage>
        }
      />
      <Route
        path="timeline"
        element={
          <SuspensePage>
            <TimelinePage />
          </SuspensePage>
        }
      />
      <Route
        path="insurance"
        element={
          <SuspensePage>
            <InsurancePage />
          </SuspensePage>
        }
      />
      {/* Deep links kept (not in tab bar). trojan/previsit removed → Timeline prompt */}
      <Route
        path="checkups"
        element={
          <SuspensePage>
            <CheckupsPage />
          </SuspensePage>
        }
      />
      <Route
        path="complaints"
        element={
          <SuspensePage>
            <ComplaintsPage />
          </SuspensePage>
        }
      />
      <Route
        path="navigator"
        element={
          <SuspensePage>
            <NavigatorPage />
          </SuspensePage>
        }
      />
      <Route path="trojan" element={<Navigate to="/insurance" replace />} />
      <Route path="previsit" element={<Navigate to="/timeline" replace />} />
      <Route
        path="records"
        element={
          <SuspensePage>
            <RecordsPage />
          </SuspensePage>
        }
      />
      <Route
        path="medications"
        element={
          <SuspensePage>
            <MedicationsPage />
          </SuspensePage>
        }
      />
      <Route
        path="history"
        element={
          <SuspensePage>
            <HistoryPage />
          </SuspensePage>
        }
      />
      <Route
        path="profile"
        element={
          <SuspensePage>
            <ProfilePage />
          </SuspensePage>
        }
      />
      <Route
        path="strategy"
        element={
          <SuspensePage>
            <StrategyPage />
          </SuspensePage>
        }
      />
    </Route>
  </Routes>
);
