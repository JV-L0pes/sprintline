import { NavLink } from "react-router-dom";
import { useI18n } from "@/shared/i18n";

export function ProjectNav({ slug, projectKey }: { slug: string; projectKey: string }) {
  const { t } = useI18n();
  const base = `/w/${slug}/p/${projectKey}`;
  const tabs = [
    { to: `${base}/board`, label: t("board.title") },
    { to: `${base}/backlog`, label: t("backlog.title") },
    { to: `${base}/metrics`, label: t("metrics.title") },
  ];
  return (
    <nav
      className="flex items-center gap-6 border-b border-rule pb-3"
      aria-label={t("project.label")}
    >
      {tabs.map((tab) => (
        <NavLink
          key={tab.to}
          to={tab.to}
          className={({ isActive }) => `nav-link${isActive ? " active" : ""}`}
        >
          {tab.label}
        </NavLink>
      ))}
    </nav>
  );
}
