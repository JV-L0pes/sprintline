import { LogOut } from "lucide-react";
import { useEffect } from "react";
import { NavLink, Outlet, useNavigate, useParams } from "react-router-dom";
import { useProjects } from "@/entities/project/api";
import { useSession } from "@/entities/session";
import { useWorkspaces } from "@/entities/workspace/api";
import { LanguageSwitch } from "@/features/shell/ui/language-switch";
import { ThemeToggle } from "@/features/shell/ui/theme-toggle";
import { useI18n } from "@/shared/i18n";
import { useReveal } from "@/shared/lib/use-reveal";
import { Skeleton } from "@/shared/ui/misc";

export function AppShell() {
  const { t } = useI18n();
  const navigate = useNavigate();
  const { user, logout } = useSession();
  const { slug } = useParams<{ slug: string }>();
  const workspaces = useWorkspaces();
  const workspace = workspaces.data?.find((item) => item.slug === slug);
  const projects = useProjects(workspace?.id);
  useReveal([projects.data]);

  useEffect(() => {
    window.scrollTo(0, 0);
  }, [slug]);

  return (
    <>
      <header className="bar stuck">
        <div className="shell bar-in">
          <button
            type="button"
            className="mark"
            aria-label={t("common.appName")}
            onClick={() => {
              void navigate("/");
            }}
          >
            S
          </button>
          <div className="min-w-0 flex-1">
            <p className="mono truncate text-ash">{workspace ? t("workspace.label") : ""}</p>
            <p className="truncate text-sm font-bold tracking-tight">
              {workspace?.name ?? t("common.loading")}
            </p>
          </div>
          <nav className="hidden items-center gap-6 md:flex" aria-label="Workspace">
            {workspace ? (
              <>
                <NavLink
                  to={`/w/${workspace.slug}`}
                  end
                  className={({ isActive }) => `nav-link${isActive ? " active" : ""}`}
                >
                  {t("project.label")}s
                </NavLink>
                <NavLink
                  to={`/w/${workspace.slug}/settings`}
                  className={({ isActive }) => `nav-link${isActive ? " active" : ""}`}
                >
                  {t("workspace.settings")}
                </NavLink>
              </>
            ) : null}
          </nav>
          <div className="flex min-w-0 items-center gap-3">
            <span className="mono hidden text-ash lg:block">{user?.name}</span>
            <LanguageSwitch />
            <ThemeToggle />
            <button
              type="button"
              className="sq"
              aria-label={t("auth.logout")}
              onClick={() => {
                void logout().then(() => navigate("/login"));
              }}
            >
              <LogOut size={15} strokeWidth={2} aria-hidden />
            </button>
          </div>
        </div>
      </header>
      <main className="shell app-grid">
        <aside className="rail" aria-label={t("project.label")}>
          <div>
            <p className="rail-title">{t("project.label")}s</p>
            {projects.isLoading ? (
              <div className="grid gap-2">
                <Skeleton />
                <Skeleton />
              </div>
            ) : (
              <nav className="grid">
                {(projects.data ?? []).map((project) => (
                  <NavLink
                    key={project.id}
                    to={`/w/${slug ?? ""}/p/${project.key}/board`}
                    className={({ isActive }) => `rail-item${isActive ? " active" : ""}`}
                  >
                    <span className="truncate">{project.name}</span>
                    <span className="key">{project.key}</span>
                  </NavLink>
                ))}
                {projects.data?.length === 0 ? (
                  <p className="py-3 text-sm text-ash">{t("project.empty")}</p>
                ) : null}
              </nav>
            )}
          </div>
          {workspace ? (
            <div>
              <p className="rail-title">{t("workspace.label")}</p>
              <nav className="grid">
                <NavLink to="/" className="rail-item">
                  <span>{t("workspace.create")}</span>
                </NavLink>
                <NavLink to={`/w/${workspace.slug}/settings`} className="rail-item">
                  <span>{t("workspace.members")}</span>
                </NavLink>
              </nav>
            </div>
          ) : null}
        </aside>
        <div className="min-w-0">
          <Outlet context={{ workspace }} />
        </div>
      </main>
    </>
  );
}
