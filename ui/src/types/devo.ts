export type StatusTone = 'OK' | 'WARN' | 'FAIL' | 'SKIP' | 'PENDING' | 'READY' | 'unknown';

export interface ApiHealth {
  status: string;
  app: string;
  read_only: boolean;
}

export interface CurrentContext {
  project: string | null;
  run: string | null;
  project_exists: boolean;
  run_exists: boolean;
  valid: boolean;
  detail: string;
}

export interface ProjectSummary {
  name: string;
  path: string;
  path_exists: boolean;
}

export interface ProjectsResponse {
  projects: ProjectSummary[];
  count: number;
}

export interface WorkPackageOverview {
  schema_version: string;
  project_name: string;
  run_id: string;
  goal: string | null;
  lane: string;
  status: string;
  scope_status: string;
  approval_status: string;
  validation_status: string;
  delivery_status: string;
  next_phase: string;
  next_command: string | null;
  stop_conditions_summary: string[];
}

export interface RunOverview {
  schema_version: string;
  project_name: string;
  run_id: string;
  goal: string;
  run_status: string;
  work_package_status: string;
  lane: string | null;
  approval_bundle_status: string | null;
  latest_validation_status: string;
  latest_validation_run_id: string | null;
  delivery_commit: string | null;
  delivery_summary: string | null;
  generated_visual_reports: string[];
  suggested_next_action: string;
  work_package: WorkPackageOverview | null;
}

export interface ProjectOverview {
  schema_version: string;
  project_name: string;
  project_path: string | null;
  is_current_project: boolean;
  current_run_id: string | null;
  onboarding_status: string;
  doctor_overall_status: string;
  settings_summary: Record<string, unknown>;
  git_summary: Record<string, unknown>;
  validation_registry_summary: Record<string, unknown>;
  backup_summary: Record<string, unknown>;
  recent_runs: RunOverview[];
  recent_work_packages: WorkPackageOverview[];
  suggested_next_action: string;
}

export interface ProjectActivity {
  project: string;
  recent_runs: string[];
  delivered_work_packages: WorkPackageActivitySummary[];
  latest_validation_runs: string[];
  latest_context_updates: string[];
  latest_reports: string[];
  current_git_status: string;
  suggested_next_action: string;
}

export interface WorkPackageActivitySummary {
  project: string;
  run_id: string;
  goal: string;
  lane: string;
  status: string;
  has_work_package: boolean;
  approval_bundle_status: string;
  latest_validation_status: string;
  latest_validation_run_id: string | null;
  commit_hash: string | null;
  delivery_summary: string | null;
  next_action: string;
  updated_at: string;
}

export interface DoctorCheck {
  name: string;
  status: StatusTone;
  detail: string;
}

export interface DoctorReport {
  project: string | null;
  checks: DoctorCheck[];
  overall_status: StatusTone;
  suggested_next_action: string;
}

export interface UiActionMetadata {
  id: string;
  label: string;
  category: 'read_only' | 'workspace_safe' | 'approval_required' | 'dangerous_deferred';
  description: string;
  allowed_in_ui_v1: boolean;
  allowed_in_ui_v2_candidate: boolean;
  mutates_workspace: boolean;
  mutates_target_project: boolean;
  requires_approval: boolean;
  risk_level: 'none' | 'low' | 'medium' | 'high' | 'critical';
  status: 'available' | 'read_only' | 'planned' | 'deferred' | 'blocked';
  reason: string;
  required_cli_command: string | null;
}

export interface UiActionsResponse {
  ui_mode: string;
  count: number;
  actions: UiActionMetadata[];
}

export interface UiActionExecuteRequest {
  action_id: string;
  project?: string | null;
  run_id?: string | null;
  confirm: boolean;
}

export interface UiActionExecutionResult {
  status: 'OK' | 'WARN' | 'FAIL' | 'BLOCKED';
  action_id: string;
  message: string;
  artifact_path: string | null;
  suggested_next_command: string | null;
}
