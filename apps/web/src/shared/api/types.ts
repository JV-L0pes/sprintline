export type Role = "OWNER" | "ADMIN" | "MEMBER" | "VIEWER";
export type RegistrationMode = "open" | "invite_only" | "closed";

export interface Meta {
  app_name: string;
  registration_mode: RegistrationMode;
}
export type WorkItemType = "EPIC" | "STORY" | "TASK" | "BUG" | "SUBTASK";
export type StatusCategory = "TODO" | "IN_PROGRESS" | "DONE";
export type SprintState = "PLANNED" | "ACTIVE" | "COMPLETED";
export type Priority = "LOWEST" | "LOW" | "MEDIUM" | "HIGH" | "HIGHEST";
export type ProjectMode = "POINTS" | "COUNT";
export type WipEnforcement = "SOFT" | "HARD";

export interface User {
  id: string;
  email: string;
  name: string;
  locale: string;
}

export interface SessionResponse {
  access_token: string;
  access_expires_at: string;
  user: User;
}

export interface Workspace {
  id: string;
  name: string;
  slug: string;
  timezone: string;
  role: Role;
}

export interface Member {
  user_id: string;
  name: string;
  email: string;
  role: Role;
  joined_at: string;
}

export interface Project {
  id: string;
  name: string;
  key: string;
  mode: ProjectMode;
  wip_enforcement: WipEnforcement;
  created_at: string;
}

export interface BoardColumn {
  id: string;
  name: string;
  position: number;
  category: StatusCategory;
  wip_limit: number | null;
  item_count: number;
}

export interface WorkItem {
  id: string;
  project_id: string;
  key: string;
  type: WorkItemType;
  title: string;
  description: string;
  parent_id: string | null;
  status_column_id: string;
  status_category: StatusCategory;
  story_points: number | null;
  priority: Priority;
  assignee_id: string | null;
  sprint_id: string | null;
  position: number;
  due_date: string | null;
  created_at: string;
  updated_at: string | null;
  done_at: string | null;
  first_in_progress_at: string | null;
  version: number;
}

export interface Board {
  id: string;
  project_id: string;
  name: string;
  columns: BoardColumn[];
  items: WorkItem[];
}

export interface Sprint {
  id: string;
  board_id: string;
  name: string;
  goal: string | null;
  state: SprintState;
  start_date: string;
  end_date: string;
  completed_at: string | null;
  total_items: number;
  done_items: number;
  total_points: number;
  done_points: number;
}

export interface BurndownDay {
  date: string;
  index: number;
  ideal: number;
  remaining: number;
  completed: number;
  scope: number;
}

export interface ScopeChange {
  date: string;
  delta: number;
  kind: "added" | "removed";
}

export interface Burndown {
  sprint_id: string;
  sprint_name: string;
  unit: "points" | "items";
  start_date: string;
  end_date: string;
  days: BurndownDay[];
  scope_changes: ScopeChange[];
  totals: {
    initial_scope: number;
    final_scope: number;
    completed: number;
    unestimated_items: number;
  };
}

export interface Cfd {
  sprint_id: string;
  start_date: string;
  end_date: string;
  days: { date: string; counts: Record<StatusCategory, number> }[];
}

export interface VelocityPoint {
  sprint_id: string;
  name: string;
  start_date: string;
  end_date: string;
  committed: number;
  completed: number;
  added: number;
  removed: number;
}

export interface Velocity {
  unit: "points" | "items";
  average: number;
  sprints: VelocityPoint[];
}

export interface FlowTimes {
  count: number;
  unit: "days";
  cycle_p50: number | null;
  cycle_p85: number | null;
  cycle_p95: number | null;
  lead_p50: number | null;
  lead_p85: number | null;
  lead_p95: number | null;
}

export type IntegrationProvider = "JIRA" | "TRELLO";

export interface Integration {
  id: string;
  provider: IntegrationProvider;
  site_url: string;
  status: string;
  story_points_field: string | null;
  created_at: string;
}

export interface ImportJob {
  id: string;
  job_type: string;
  state: "PENDING" | "RUNNING" | "DONE" | "FAILED";
  project_key: string;
  start_at: number;
  imported_count: number;
  last_error: string | null;
  created_at: string;
}

export interface TrelloBoard {
  id: string;
  name: string;
  url: string;
  closed: boolean;
}

export interface FieldDiscovery {
  story_points_field: string | null;
  fields: { field_id: string; name: string; schema_type: string | null }[];
}
