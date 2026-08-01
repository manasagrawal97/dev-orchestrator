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
  brief_status: string;
  blueprint_status: string;
  blueprint_milestone_count: number;
  blueprint_epic_count: number;
  backlog_status: string;
  backlog_task_count: number;
  backlog_ready_count: number;
  backlog_blocked_count: number;
  backlog_completed_count: number;
  backlog_refinement_prompt_exists: boolean;
  backlog_refinement_prompt_path: string | null;
  batch_count: number;
  approved_batch_count: number;
  latest_batch_id: string | null;
  latest_batch_status: string | null;
  queue_count: number;
  latest_queue_id: string | null;
  latest_queue_status: string | null;
  current_queue_item: string | null;
  queue_pending_count: number;
  queue_completed_count: number;
  queue_blocked_count: number;
  queue_next_action: string;
  handoff_count: number;
  latest_handoff_id: string | null;
  latest_handoff_type: string | null;
  latest_handoff_status: string | null;
  latest_handoff_path: string | null;
  handoff_next_action: string;
  project_completion_percent: number;
  backlog_readiness_percent: number;
  blocked_percent: number;
  batch_completion_percent: number;
  progress_next_action: string;
  planning_next_action: string;
  recent_runs: RunOverview[];
  recent_work_packages: WorkPackageOverview[];
  suggested_next_action: string;
}

export interface ArtifactPaths {
  json?: string;
  markdown?: string;
}

export interface ProjectBrief {
  project: string;
  title: string;
  summary: string;
  status: string;
  artifact_paths?: ArtifactPaths;
}

export interface ProjectBlueprint {
  project: string;
  title: string;
  vision_summary: string;
  status: string;
  milestones: Array<{
    id: string;
    title: string;
    summary: string;
    target_outcome: string;
    status: string;
  }>;
  epics: Array<{
    id: string;
    milestone_id: string | null;
    title: string;
    summary: string;
    status: string;
  }>;
  architecture_notes: string[];
  risk_summary: string[];
  validation_strategy: string[];
  open_questions: string[];
  artifact_paths?: ArtifactPaths;
}

export interface ProjectBacklog {
  project: string;
  title: string;
  status: string;
  task_count: number;
  ready_task_count: number;
  blocked_task_count: number;
  completed_task_count: number;
  artifact_paths?: ArtifactPaths;
}

export interface BacklogTask {
  id: string;
  title: string;
  summary: string;
  milestone_id: string | null;
  epic_id: string | null;
  lane: string;
  risk_level: string;
  status: string;
  dependencies: string[];
  acceptance_criteria: string[];
  validation_expectations: string[];
  allowed_scope: string[];
  forbidden_scope: string[];
  notes: string[];
  source: string;
}

export interface ProjectTasksResponse {
  project: string;
  count: number;
  tasks: BacklogTask[];
}

export interface ProjectBatchesResponse {
  project: string;
  count: number;
  batches: Array<{
    batch_id: string;
    title: string;
    status: string;
    approval_status: string;
    task_count: number;
  }>;
}

export interface ProjectQueuesResponse {
  project: string;
  count: number;
  queues: Array<{
    queue_id: string;
    title: string;
    source_batch_id: string;
    status: string;
    current_item_id: string | null;
    pending_count: number;
    completed_count: number;
    blocked_count: number;
  }>;
}

export interface ProjectHandoffsResponse {
  project: string;
  count: number;
  handoffs: Array<{
    handoff_id: string;
    handoff_type: string;
    title: string;
    status: string;
    source_queue_id: string | null;
    source_batch_id: string | null;
    source_item_id: string | null;
    source_task_id: string | null;
    prompt_path: string;
  }>;
}

export interface ProjectProgress {
  project: string;
  brief_status: string;
  blueprint_status: string;
  backlog_status: string;
  project_completion_percent: number;
  backlog_readiness_percent: number;
  blocked_percent: number;
  batch_completion_percent: number;
  next_action: string;
  warnings: string[];
  milestone_progress: PlanningProgressGroup[];
  epic_progress: PlanningProgressGroup[];
}

export interface PlanningProgressGroup {
  id: string;
  title: string | null;
  task_count: number;
  active_task_count: number;
  completed_task_count: number;
  blocked_task_count: number;
  ready_task_count: number;
  approved_task_count: number;
  draft_task_count: number;
  completion_percent: number;
  readiness_percent: number;
  blocked_percent: number;
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
  goal?: string | null;
  lane?: string | null;
  confirm: boolean;
  no_template?: boolean;
}

export interface UiActionExecutionResult {
  status: 'OK' | 'WARN' | 'FAIL' | 'BLOCKED';
  action_id: string;
  message: string;
  project: string | null;
  run_id: string | null;
  lane: string | null;
  artifact_path: string | null;
  suggested_next_command: string | null;
}
