export type StatusTone = 'OK' | 'WARN' | 'FAIL' | 'SKIP' | 'PENDING' | 'READY' | 'unknown';

export interface ApiHealth {
  status: string;
  app: string;
  read_only: boolean;
  capabilities?: {
    read_projections: boolean;
    guarded_mutations: boolean;
    localhost_mutations_only: boolean;
    arbitrary_commands: boolean;
    automatic_retry: boolean;
  };
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
  delivery_check_count: number;
  latest_delivery_id: string | null;
  latest_delivery_readiness_status: string | null;
  latest_delivery_blocker_count: number;
  latest_delivery_warning_count: number;
  delivery_next_action: string | null;
  delivery_plan_count: number;
  latest_delivery_plan_id: string | null;
  latest_delivery_plan_status: string | null;
  latest_delivery_approval_status: string | null;
  latest_delivery_plan_next_action: string | null;
  delivery_report_count: number;
  latest_delivery_report_id: string | null;
  latest_delivery_report_status: string | null;
  latest_delivery_commit_ready: boolean;
  latest_delivery_push_ready: boolean;
  latest_delivery_report_next_action: string | null;
  latest_delivery_commit_hash: string | null;
  latest_delivery_commit_status: string | null;
  latest_delivery_pushed: boolean;
  latest_delivery_commit_next_action: string | null;
  latest_delivery_push_status: string | null;
  latest_delivery_push_remote: string | null;
  latest_delivery_push_branch: string | null;
  latest_delivery_pushed_at: string | null;
  latest_delivery_push_next_action: string | null;
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
  current_queue_item_completion_ready: boolean;
  current_queue_item_completion_blockers: string[];
  current_queue_item_validation_status: string | null;
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
  latest_worker_review_id: string | null;
  latest_worker_review_status: string | null;
  latest_worker_validation_status: string | null;
  latest_worker_review_reviewer: string | null;
  latest_worker_review_decision_note: string | null;
  review_next_action: string | null;
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
  selected_item_source: string;
  source_handoff_id: string | null;
  linked_worker_run_id: string | null;
  linked_worker_run_status: string | null;
  linked_run_plan_id: string | null;
  linked_run_plan_status: string | null;
  latest_worker_execution_status: string | null;
  latest_worker_execution_exit_code: number | null;
  latest_worker_execution_log_path: string | null;
  latest_worker_report_status: string | null;
  latest_worker_review_id: string | null;
  latest_worker_review_status: string | null;
  latest_worker_validation_status: string | null;
  current_queue_item_completion_ready: boolean;
  current_queue_item_completion_blockers: string[];
  current_queue_item_review_status: string | null;
  current_queue_item_validation_status: string | null;
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

export interface ValidationEvidence {
  validation_status: string;
  commands_reported: string[];
  tests_reported: string[];
  validation_summary: string;
  evidence_paths: string[];
  warnings: string[];
}

export interface WorkerReview {
  project: string;
  review_id: string;
  worker_run_id: string;
  source_queue_id: string | null;
  source_queue_item_id: string | null;
  source_task_id: string | null;
  source_handoff_id: string | null;
  source_report_path: string | null;
  review_status: string;
  reviewer: string | null;
  decision_note: string;
  validation_evidence: ValidationEvidence;
  changed_files_review: string[];
  safety_review: string[];
  acceptance_criteria_review: string[];
  follow_up_items: string[];
  next_action: string;
  created_at?: string;
  updated_at?: string;
}

export interface WorkerReviewsResponse {
  project: string;
  count: number;
  reviews: WorkerReview[];
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

export interface OperatorConsoleAction {
  action_id: string;
  label: string;
  command: string;
  confirmation_required: boolean;
  reason: string;
}

export interface OperatorConsoleChild {
  position: number;
  task_id: string;
  title: string;
  risk_level: string;
  queue_item_id: string;
  queue_item_status: string;
  policy_id: string;
  policy_status: string;
  stage: string;
  is_current: boolean;
}

export interface OperatorConsoleGoal {
  intake_id: string;
  goal_summary: string;
  status: string;
  recorded_preparation_status: string;
  preparation_id: string;
  bundle_id: string;
  bundle_status: string;
  child_count: number;
  completed_child_count: number;
  remaining_child_count: number;
  children: OperatorConsoleChild[];
  current_stage: string;
  current_task_id: string | null;
  current_task_title: string | null;
  current_policy_id: string | null;
  current_queue_worker_run_id: string | null;
  current_queue_worker_status: string | null;
  current_review_status: string | null;
  delivery_state: string;
  supervisor_run_id: string | null;
  supervisor_status: string | null;
  blockers: string[];
  attention_required: boolean;
  attention_items: string[];
  next_action: string;
}

export interface OperatorConsoleRecentCompletion {
  intake_id: string;
  goal_summary: string;
  bundle_id: string;
  child_count: number;
  completed_at: string | null;
}

export interface OperatorConsoleProjection {
  project: string;
  active_goal: OperatorConsoleGoal | null;
  recent_completion: OperatorConsoleRecentCompletion | null;
  attention_required: boolean;
  attention_items: string[];
  supported_actions: OperatorConsoleAction[];
  warnings: string[];
  generated_at: string;
  safety_note: string;
}

export interface RoughGoalTaskDraft {
  task_id: string;
  title: string;
  summary: string;
  allowed_files: string[];
  validation: string[];
  risk_level: string;
}

export interface RoughGoalBatchDraft {
  suggested_batch_id: string;
  title: string;
  task_ids: string[];
  notes: string[];
}

export interface RoughGoalQueueItemDraft {
  item_id: string;
  task_id: string;
  title: string;
}

export interface RoughGoalQueueDraft {
  suggested_queue_id: string;
  batch_id: string;
  items: RoughGoalQueueItemDraft[];
  notes: string[];
}

export interface RoughGoalPolicyDraft {
  suggested_policy_id: string;
  batch_id: string;
  queue_id: string;
  allowed_task_ids: string[];
  allowed_queue_item_ids: string[];
  allowed_file_patterns: string[];
  forbidden_file_patterns: string[];
  validation_commands: string[];
  risk_level: string;
  max_tasks: number;
  max_tasks_per_run: number;
  max_changed_files_per_task: number;
  notes: string[];
}

export interface RoughGoalIntakePlan {
  schema_version: string;
  project: string;
  intake_id: string;
  source_file: string;
  normalized_goal_summary: string;
  parsed_scope_notes: string[];
  parsed_context_notes: string[];
  candidate_tasks: RoughGoalTaskDraft[];
  suggested_batch_draft: RoughGoalBatchDraft;
  suggested_queue_draft: RoughGoalQueueDraft;
  suggested_policy_draft: RoughGoalPolicyDraft;
  suggested_allowed_files: string[];
  do_not_touch: string[];
  validation_notes: string[];
  delivery_notes: string[];
  missing_sections: string[];
  risk_notes: string[];
  recommended_next_commands: string[];
  preview_only: boolean;
  created_at: string;
}

export interface RoughGoalIntakeMaterialization {
  schema_version: string;
  project: string;
  intake_id: string;
  status: string;
  created_task_ids: string[];
  batch_id: string;
  queue_id: string;
  policy_id: string;
  allowed_file_patterns: string[];
  forbidden_file_patterns: string[];
  validation_notes: string[];
  delivery_notes: string[];
  risk_notes: string[];
  backlog_path: string;
  batch_path: string;
  queue_path: string;
  policy_path: string;
  next_commands: string[];
  safety_note: string;
  created_at: string;
}

export interface RoughGoalPreparation {
  schema_version: string;
  project: string;
  preparation_id: string;
  intake_id: string;
  status: string;
  batch_id: string;
  queue_id: string;
  source_policy_id: string;
  task_ids: string[];
  queue_item_ids: string[];
  policy_ids: string[];
  task_policy_ids: Record<string, string>;
  approval_bundle_id: string;
  approval_bundle_status: string;
  prepared_task_count: number;
  created_policy_ids: string[];
  reused_policy_ids: string[];
  total_max_tasks: number;
  total_max_changed_files: number;
  materialized_plan_reviewed_by: string | null;
  supervised_delivery_enabled: boolean;
  supervised_delivery_authorized_by: string | null;
  source_policy_permissions_updated: boolean;
  warnings: string[];
  blockers: string[];
  next_action: string;
  created_at: string;
  updated_at: string;
  safety_note: string;
}

export interface BatchExecutionPolicy {
  schema_version: string;
  project: string;
  policy_id: string;
  batch_id: string;
  queue_id: string | null;
  title: string;
  status: string;
  created_at: string;
  updated_at: string;
  requested_at: string | null;
  approved_at: string | null;
  rejected_at: string | null;
  cancelled_at: string | null;
  expires_at: string | null;
  approver: string | null;
  reviewer: string | null;
  decision_note: string;
  allowed_task_ids: string[];
  allowed_queue_item_ids: string[];
  allowed_file_patterns: string[];
  forbidden_file_patterns: string[];
  max_tasks: number;
  max_tasks_per_run: number;
  max_changed_files_per_task: number;
  max_total_changed_files: number;
  validation_commands: string[];
  auto_delivery_allowed: boolean;
  auto_push_allowed: boolean;
  requires_worker_review: boolean;
  requires_validation_evidence: boolean;
  pause_conditions: string[];
  risk_level: string;
  notes: string[];
  next_action: string;
}

export interface ExecutionPolicyApprovalBundle {
  schema_version: string;
  project: string;
  bundle_id: string;
  status: string;
  policy_ids: string[];
  policy_scope_fingerprints: Record<string, string>;
  policy_task_ids: Record<string, string[]>;
  policy_queue_item_ids: Record<string, string[]>;
  max_policies: number;
  total_max_tasks: number;
  total_max_changed_files: number;
  requested_at: string;
  updated_at: string;
  approved_at: string | null;
  approver: string | null;
  request_note: string;
  approval_note: string;
  goal_intake_id: string | null;
  allows_non_low_risk: boolean;
  next_action: string;
}

export interface QueueWorkerHandoffChecklist {
  objective: string;
  allowed_scope: string[];
  forbidden_scope: string[];
  relevant_files: string[];
  acceptance_criteria: string[];
  required_tests: string[];
  expected_worker_result_format: string[];
  risk_notes: string[];
  next_action: string;
}

export interface QueueWorkerRun {
  schema_version: string;
  project: string;
  run_id: string;
  policy_id: string;
  batch_id: string | null;
  queue_id: string | null;
  selected_queue_item_id: string | null;
  selected_task_id: string | null;
  selected_handoff_id: string | null;
  selected_worker_run_id: string | null;
  mode: string;
  status: string;
  started_at: string;
  completed_at: string | null;
  approver: string | null;
  steps_run: string[];
  blockers: string[];
  warnings: string[];
  skipped_queue_item_summaries: string[];
  handoff_checklist: QueueWorkerHandoffChecklist | null;
  policy_check_summary: string;
  selection_reason: string;
  pause_reason: string;
  failure_reason: string;
  cancel_reason: string;
  retry_of: string | null;
  retry_authorized_by?: string | null;
  delivery_request_id: string | null;
  delivery_request_status: string | null;
  delivery_requested_at: string | null;
  paused_at: string | null;
  resumed_at: string | null;
  failed_at: string | null;
  cancelled_at: string | null;
  updated_at: string;
  next_action: string;
}

export interface QueueWorkerEvidenceRecord {
  evidence_id: string;
  project: string;
  queue_worker_run_id: string;
  queue_item_id: string | null;
  task_id: string | null;
  evidence_type: string;
  status: string;
  summary: string;
  changed_files: string[];
  commands_run: string[];
  artifact_path: string | null;
  risks: string[];
  recommended_next_action: string;
  note: string;
  created_at: string;
  recorded_by: string | null;
}

export interface QueueWorkerEvidenceSummary {
  handoff_exists: boolean;
  worker_run_exists: boolean;
  worker_report_imported: boolean;
  worker_review_exists: boolean;
  worker_review_passed: boolean;
  validation_evidence_exists: boolean;
  validation_passed: boolean;
  worker_report_status: string | null;
  worker_review_status: string | null;
  validation_status: string | null;
  delivery_request_id: string | null;
  delivery_request_status: string | null;
  delivery_request_exists: boolean;
  delivery_completed: boolean;
  patch_proposal_present: boolean;
  patch_artifact_path: string | null;
  missing_evidence: string[];
  blockers: string[];
  warnings: string[];
}

export interface QueueWorkerEvidenceRecordResult {
  project: string;
  run_id: string;
  evidence_record: QueueWorkerEvidenceRecord | null;
  run_status: string;
  evidence_type: string;
  evidence_status: string;
  summary: string;
  action_taken: string;
  artifact_path: string | null;
  record_json_path: string | null;
  record_markdown_path: string | null;
  commands_run: string[];
  files_changed: string[];
  evidence: QueueWorkerEvidenceSummary;
  next_action: string;
  warnings: string[];
  blockers: string[];
}

export interface ApprovedBundleSupervisorEvent {
  sequence: number;
  event: string;
  status: string;
  policy_id: string | null;
  queue_item_id: string | null;
  task_id: string | null;
  queue_worker_run_id: string | null;
  delivery_request_id: string | null;
  detail: string;
  recorded_at: string;
}

export interface ApprovedBundleSupervisorResult {
  project: string;
  bundle_id: string;
  supervisor_run_id: string | null;
  dry_run: boolean;
  status: string;
  poll_interval_seconds: number;
  max_wait_seconds: number;
  selected_policy_id: string | null;
  selected_queue_item_id: string | null;
  selected_task_id: string | null;
  selected_queue_worker_run_id: string | null;
  current_queue_worker_status: string | null;
  planned_action: string;
  would_run_worker: boolean;
  would_run_review: boolean;
  would_run_validation: boolean;
  would_wait_for_trusted_delivery: boolean;
  would_consider_next_child: boolean;
  child_policy_ids_visited: string[];
  queue_item_ids_visited: string[];
  task_ids_visited: string[];
  queue_worker_run_ids: string[];
  delivery_request_ids: string[];
  delivery_wait_outcomes: string[];
  children_completed: number;
  initial_completed_child_keys: string[];
  resume_count: number;
  last_checkpoint: string;
  checkpointed_at: string | null;
  events: ApprovedBundleSupervisorEvent[];
  warnings: string[];
  blockers: string[];
  stop_reason: string;
  next_action: string;
  workflow_mutated: boolean;
  artifact_json_path: string | null;
  artifact_markdown_path: string | null;
  started_at: string;
  completed_at: string | null;
  safety_note: string;
}

export interface OperatorConsoleIntakeRequest {
  goal_markdown: string;
  confirm_create: boolean;
}

export interface OperatorConsoleMaterializeRequest {
  confirm_materialize: boolean;
}

export interface OperatorConsolePrepareRequest {
  confirm_prepare: boolean;
  confirm_materialized_plan_reviewed: boolean;
  reviewed_by: string;
  enable_supervised_delivery: boolean;
  confirm_supervised_delivery: boolean;
  supervised_delivery_authorized_by: string;
}

export interface OperatorConsolePlanningApprovalRequest {
  batch_id: string;
  approver: string;
  note: string;
  confirm_approve: boolean;
}

export interface OperatorConsoleApprovalRequest {
  bundle_id: string;
  approver: string;
  note: string;
  confirm_approve: boolean;
}

export interface OperatorConsoleRunRequest {
  bundle_id: string;
  message: string;
  note: string;
  max_steps: number;
  poll_interval_seconds: number;
  max_wait_seconds: number;
  confirm_run: boolean;
}

export type OperatorConsoleReviewStatus = 'passed' | 'needs_changes' | 'rejected' | 'blocked';

export interface OperatorConsoleReviewRequest {
  bundle_id: string;
  status: OperatorConsoleReviewStatus;
  summary: string;
  recorded_by: string;
  note: string;
  confirm_review: boolean;
}

export type OperatorConsoleRecoveryAction = 'resume_worker' | 'retry_worker';

export interface OperatorConsoleRecoveryRequest {
  intake_id: string;
  bundle_id: string;
  action: OperatorConsoleRecoveryAction;
  operator: string;
  reason: string;
  confirm_recovery: boolean;
}

export interface OperatorConsoleCreateIntakeResponse {
  intake: RoughGoalIntakePlan;
  artifact_paths: ArtifactPaths;
}

export interface OperatorConsoleMaterializeResponse {
  materialization: RoughGoalIntakeMaterialization;
  review: {
    backlog_tasks: BacklogTask[];
    batch: ProjectBatch;
    queue: ExecutionQueue;
    source_policy: BatchExecutionPolicy;
  };
  artifact_paths: ArtifactPaths;
}

export interface OperatorConsolePlanningApprovalResponse {
  materialization: RoughGoalIntakeMaterialization;
  batch: ProjectBatch;
  approval: BatchApproval;
  direct_approval: boolean;
  artifact_paths: {
    batch_json: string;
    batch_markdown: string;
    approval_json: string;
    approval_markdown: string;
  };
}

export interface OperatorConsolePrepareResponse {
  preparation: RoughGoalPreparation;
  materialization: RoughGoalIntakeMaterialization;
  console: OperatorConsoleProjection;
  artifact_paths: ArtifactPaths;
}

export interface OperatorConsoleApprovalResponse {
  bundle: ExecutionPolicyApprovalBundle;
  console: OperatorConsoleProjection;
  artifact_paths: ArtifactPaths;
}

export interface OperatorConsoleRunResponse {
  preparation: RoughGoalPreparation;
  result: ApprovedBundleSupervisorResult;
  console: OperatorConsoleProjection;
}

export interface OperatorConsoleReviewResponse {
  review: QueueWorkerEvidenceRecordResult;
  console: OperatorConsoleProjection;
}

export interface OperatorConsoleRecoveryResponse {
  action: OperatorConsoleRecoveryAction;
  run: QueueWorkerRun;
  console: OperatorConsoleProjection;
  artifact_paths: ArtifactPaths;
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

export interface DeliveryCheck {
  project: string;
  delivery_id: string;
  readiness_status: string;
  branch: string | null;
  remote: string | null;
  changed_files: string[];
  staged_files: string[];
  unstaged_files: string[];
  untracked_files: string[];
  blockers: string[];
  warnings: string[];
  next_action: string;
  updated_at?: string;
}

export interface DeliveryPlan {
  project: string;
  delivery_id: string;
  delivery_status: string;
  approval_status: string;
  readiness_status: string;
  intended_commit_message: string;
  blockers: string[];
  warnings: string[];
  next_action: string;
  updated_at?: string;
}

export interface DeliveryApproval {
  project: string;
  delivery_id: string;
  approval_status: string;
  readiness_status: string;
  blocker_count: number;
  warning_count: number;
  decision_note: string;
  next_action: string;
  updated_at?: string;
}

export interface DeliveryReport {
  project: string;
  delivery_id: string;
  final_status: string;
  commit_ready: boolean;
  push_ready: boolean;
  push_status: string | null;
  pushed: boolean;
  proposed_commit_message: string;
  changed_files: string[];
  staged_files: string[];
  unstaged_files: string[];
  untracked_files: string[];
  blocker_summary: string;
  warning_summary: string;
  readiness_snapshot_status: string | null;
  readiness_snapshot_at: string | null;
  readiness_currentness: string;
  readiness_snapshot_note: string;
  commit_hash: string | null;
  push_remote: string | null;
  push_branch: string | null;
  pushed_at: string | null;
  next_action: string;
  updated_at?: string;
}

export interface DeliveryCommitResult {
  project: string;
  delivery_id: string;
  status: string;
  commit_hash: string | null;
  commit_message: string;
  eligible_files: string[];
  next_action: string;
  updated_at?: string;
}

export interface DeliveryPushResult {
  project: string;
  delivery_id: string;
  push_status: string;
  pushed: boolean;
  source_commit_hash: string | null;
  push_remote: string | null;
  push_branch: string | null;
  blockers: string[];
  warnings: string[];
  next_action: string;
  updated_at?: string;
}

export interface DeliveryChecksResponse {
  project: string;
  count: number;
  delivery_checks: DeliveryCheck[];
}

export interface DeliveryPlansResponse {
  project: string;
  count: number;
  delivery_plans: DeliveryPlan[];
}

export interface DeliveryApprovalsResponse {
  project: string;
  count: number;
  delivery_approvals: DeliveryApproval[];
}

export interface DeliveryReportsResponse {
  project: string;
  count: number;
  delivery_reports: DeliveryReport[];
}
