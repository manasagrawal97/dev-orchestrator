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
  latest_batch_approval_status: string | null;
  latest_batch_review_status: string | null;
  batch_approval_requested_count: number;
  batch_approved_count: number;
  batch_rejected_count: number;
  batch_needs_changes_count: number;
  batch_approval_next_action: string;
  queue_count: number;
  latest_queue_id: string | null;
  latest_queue_status: string | null;
  current_queue_item: string | null;
  queue_pending_count: number;
  queue_completed_count: number;
  queue_blocked_count: number;
  queue_next_action: string;
  linked_worker_run_id: string | null;
  linked_worker_run_status: string | null;
  linked_run_plan_id: string | null;
  current_queue_item_worker_status: string | null;
  current_queue_item_review_status: string | null;
  queue_worker_next_action: string | null;
  handoff_count: number;
  latest_handoff_id: string | null;
  latest_handoff_type: string | null;
  latest_handoff_status: string | null;
  latest_handoff_path: string | null;
  handoff_next_action: string;
  worker_run_count: number;
  latest_worker_run_id: string | null;
  latest_worker_run_status: string | null;
  latest_worker_run_next_action: string | null;
  latest_worker_execution_status: string | null;
  latest_worker_execution_exit_code: number | null;
  latest_worker_execution_log_path: string | null;
  latest_worker_execution_next_action: string | null;
  latest_worker_report_status: string | null;
  latest_worker_report_path: string | null;
  latest_worker_report_summary: string | null;
  latest_worker_report_next_action: string | null;
  codex_run_plan_count: number;
  latest_codex_run_plan_id: string | null;
  latest_codex_run_plan_status: string | null;
  latest_codex_preflight_status: string | null;
  latest_codex_run_plan_next_action: string | null;
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
  batches: ProjectBatch[];
}

export interface BatchTaskSnapshot {
  task_id: string;
  title: string;
  lane: string;
  risk_level: string;
  status: string;
  dependencies: string[];
  acceptance_criteria_summary: string;
  validation_expectations_summary: string;
}

export interface ProjectBatch {
  project: string;
  batch_id: string;
  title: string;
  summary: string;
  source_backlog_reference: string;
  status: string;
  task_ids: string[];
  task_count: number;
  completed_task_count: number;
  blocked_task_count: number;
  risk_summary: Record<string, number>;
  lane_summary: Record<string, number>;
  dependencies: string[];
  approval_status: string;
  review_status: string;
  review_notes: string[];
  task_snapshots: BatchTaskSnapshot[];
  dependency_warnings: string[];
  created_at?: string;
  updated_at?: string;
}

export interface BatchApproval {
  project: string;
  batch_id: string;
  approval_status: string;
  review_status: string;
  requested_at: string | null;
  reviewed_at: string | null;
  approved_at: string | null;
  rejected_at: string | null;
  reviewer: string | null;
  approver: string | null;
  decision_note: string;
  review_notes: string[];
  dependency_warnings: string[];
  risk_summary: Record<string, number>;
  lane_summary: Record<string, number>;
  task_count: number;
  high_risk_task_count: number;
  blocked_dependency_count: number;
  scope_summary: string[];
  validation_summary: string[];
  next_action: string;
  created_at?: string;
  updated_at?: string;
}

export interface BatchApprovalsResponse {
  project: string;
  count: number;
  approvals: BatchApproval[];
}

export interface ProjectQueuesResponse {
  project: string;
  count: number;
  queues: ExecutionQueue[];
}

export interface QueueItem {
  item_id: string;
  task_id: string;
  title: string;
  lane: string;
  risk_level: string;
  status: string;
  batch_id: string;
  dependencies: string[];
  acceptance_criteria: string[];
  validation_expectations: string[];
  started_at: string | null;
  completed_at: string | null;
  notes: string[];
}

export interface ExecutionQueue {
  project: string;
  queue_id: string;
  title: string;
  source_batch_id: string;
  source_backlog_reference: string;
  status: string;
  items: QueueItem[];
  item_count: number;
  pending_count: number;
  running_count: number;
  completed_count: number;
  blocked_count: number;
  failed_count: number;
  pause_reason: string | null;
  resume_hint: string | null;
  current_item_id: string | null;
  created_at?: string;
  updated_at?: string;
}

export interface CodexQueueWorkerStatus {
  project: string;
  queue_id: string;
  queue_status: string;
  current_item_id: string | null;
  current_item_status: string | null;
  current_task_id: string | null;
  linked_worker_run_id: string | null;
  linked_worker_run_status: string | null;
  linked_run_plan_id: string | null;
  linked_run_plan_status: string | null;
  latest_worker_execution_status: string | null;
  latest_worker_execution_exit_code: number | null;
  latest_worker_execution_log_path: string | null;
  next_action: string;
}

export interface ProjectHandoffsResponse {
  project: string;
  count: number;
  handoffs: CodexHandoff[];
}

export interface CodexHandoff {
  project: string;
  handoff_id: string;
  handoff_type: string;
  title: string;
  status: string;
  source_queue_id: string | null;
  source_batch_id: string | null;
  source_item_id: string | null;
  source_task_id: string | null;
  prompt_path: string;
  created_at?: string;
  updated_at?: string;
}

export interface WorkerReportMetadata {
  report_status: string;
  reported_changed_files: string[];
  reported_validation: string[];
  reported_commit_hash: string | null;
  safety_warnings: string[];
  reviewer_notes: string[];
  imported_at: string | null;
}

export interface CodexWorkerReport {
  project: string;
  worker_run_id: string;
  source_handoff_id: string | null;
  source_queue_id: string | null;
  source_queue_item_id: string | null;
  source_task_id: string | null;
  status_reported_by_worker: string;
  summary: string;
  changed_files: string[];
  validation_attempted: boolean;
  validation_results: string[];
  tests_run: string[];
  commands_run: string[];
  commit_hash: string | null;
  safety_warnings: string[];
  blockers: string[];
  follow_up_needed: string[];
  notes: string[];
  reported_at: string | null;
}

export interface WorkerRun {
  project: string;
  worker_run_id: string;
  worker_type: string;
  mode: string;
  source_handoff_id: string | null;
  source_queue_id: string | null;
  source_queue_item_id: string | null;
  source_batch_id: string | null;
  source_task_id: string | null;
  title: string;
  status: string;
  prompt_path: string;
  transcript_path: string | null;
  report_path: string | null;
  target_repo_path: string;
  execution_exit_code: number | null;
  execution_command_label: string | null;
  execution_started_by: string | null;
  execution_log_path: string | null;
  execution_stderr_log_path: string | null;
  allowed_scope: string[];
  forbidden_scope: string[];
  validation_expectations: string[];
  safety_boundaries: string[];
  report: WorkerReportMetadata;
  started_at: string | null;
  completed_at: string | null;
  created_at?: string;
  updated_at?: string;
  status_note: string;
  next_action: string;
}

export interface WorkerRunsResponse {
  project: string;
  count: number;
  worker_runs: WorkerRun[];
}

export interface WorkerExecutionMetadata {
  project: string;
  worker_run_id: string;
  status: string;
  execution_exit_code: number | null;
  execution_command_label: string | null;
  execution_started_by: string | null;
  execution_log_path: string;
  execution_stderr_log_path: string;
  next_action: string;
  status_note: string;
}

export interface CodexPreflightCheck {
  name: string;
  status: string;
  detail: string;
}

export interface CodexRunPlan {
  project: string;
  plan_id: string;
  worker_run_id: string;
  handoff_id: string;
  queue_id: string | null;
  queue_item_id: string | null;
  task_id: string | null;
  batch_id: string | null;
  status: string;
  target_repo_path: string;
  prompt_path: string;
  proposed_working_directory: string;
  proposed_command_label: string;
  proposed_command_preview: string;
  approval_required: boolean;
  approval_status: string;
  approval_note?: string | null;
  preflight_status: string;
  preflight_checks: CodexPreflightCheck[];
  safety_boundaries: string[];
  allowed_scope: string[];
  forbidden_scope: string[];
  validation_expectations: string[];
  blocked_reasons: string[];
  warnings: string[];
  next_action: string;
  created_at?: string;
  updated_at?: string;
}

export interface CodexRunPlansResponse {
  project: string;
  count: number;
  run_plans: CodexRunPlan[];
}

export interface WorkerReportsResponse {
  project: string;
  count: number;
  reports: CodexWorkerReport[];
}

export interface ProjectProgress {
  project: string;
  has_brief?: boolean;
  brief_status: string;
  has_blueprint?: boolean;
  blueprint_status: string;
  has_backlog?: boolean;
  backlog_status: string;
  task_count: number;
  completed_task_count: number;
  active_task_count: number;
  blocked_task_count: number;
  approved_task_count: number;
  ready_task_count: number;
  draft_task_count: number;
  project_completion_percent: number;
  backlog_readiness_percent: number;
  blocked_percent: number;
  batch_count: number;
  approved_batch_count: number;
  completed_batch_count: number;
  active_batch_count: number;
  batch_completion_percent: number;
  latest_batch_id: string | null;
  latest_batch_status: string | null;
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
  batch_id?: string | null;
  note?: string | null;
  needs_changes?: boolean;
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
