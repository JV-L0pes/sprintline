import { lazy, type ReactNode, Suspense } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { useSession } from "@/entities/session";
import { useI18n } from "@/shared/i18n";
import { AppShell } from "@/widgets/app-shell";

const HomePage = lazy(() =>
  import("@/pages/home").then((module) => ({ default: module.HomePage })),
);
const ProjectsPage = lazy(() =>
  import("@/pages/projects").then((module) => ({ default: module.ProjectsPage })),
);
const BoardPage = lazy(() =>
  import("@/pages/board").then((module) => ({ default: module.BoardPage })),
);
const BacklogPage = lazy(() =>
  import("@/pages/backlog").then((module) => ({ default: module.BacklogPage })),
);
const MetricsPage = lazy(() =>
  import("@/pages/metrics").then((module) => ({ default: module.MetricsPage })),
);
const SettingsPage = lazy(() =>
  import("@/pages/settings").then((module) => ({ default: module.SettingsPage })),
);
const InvitePage = lazy(() =>
  import("@/pages/invite").then((module) => ({ default: module.InvitePage })),
);
const JiraCallbackPage = lazy(() =>
  import("@/pages/jira-callback").then((module) => ({ default: module.JiraCallbackPage })),
);
const TrelloCallbackPage = lazy(() =>
  import("@/pages/trello-callback").then((module) => ({ default: module.TrelloCallbackPage })),
);
const LoginPage = lazy(() =>
  import("@/pages/login").then((module) => ({ default: module.LoginPage })),
);
const RegisterPage = lazy(() =>
  import("@/pages/register").then((module) => ({ default: module.RegisterPage })),
);

function BootScreen() {
  const { t } = useI18n();
  return (
    <div className="grid min-h-screen place-content-center">
      <p className="mono text-ash">{t("common.loading")}…</p>
    </div>
  );
}

function RequireAuth({ children }: { children: ReactNode }) {
  const { status } = useSession();
  if (status === "booting") {
    return <BootScreen />;
  }
  if (status === "anonymous") {
    return <Navigate to="/login" replace />;
  }
  return children;
}

export function App() {
  return (
    <Suspense fallback={<BootScreen />}>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/integrations/callback" element={<JiraCallbackPage />} />
        <Route path="/integrations/trello/callback" element={<TrelloCallbackPage />} />
        <Route path="/invite/:token" element={<InvitePage />} />
        <Route
          path="/"
          element={
            <RequireAuth>
              <HomePage />
            </RequireAuth>
          }
        />
        <Route
          path="/w/:slug"
          element={
            <RequireAuth>
              <AppShell />
            </RequireAuth>
          }
        >
          <Route index element={<ProjectsPage />} />
          <Route path="p/:key/board" element={<BoardPage />} />
          <Route path="p/:key/backlog" element={<BacklogPage />} />
          <Route path="p/:key/metrics" element={<MetricsPage />} />
          <Route path="settings" element={<SettingsPage />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Suspense>
  );
}
