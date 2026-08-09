import type {
  ApiHealth,
  BatchApproval,
  BatchApprovalsResponse,
  CurrentContext,
  DoctorReport,
  DeliveryApprovalsResponse,
  DeliveryChecksResponse,
  DeliveryCommitResult,
  DeliveryPlansResponse,
  DeliveryPushResult,
  DeliveryReportsResponse,
  CodexWorkerReport,
  CodexQueueWorkerStatus,
  CodexRunPlan,
  CodexRunPlansResponse,
  CodexHandoff,
  ExecutionQueue,
  ProjectBacklog,
  ProjectBatchesResponse,
  ProjectBlueprint,
  ProjectBatch,
  ProjectBrief,
  ProjectActivity,
  ProjectHandoffsResponse,
  ProjectOverview,
  ProjectProgress,
  ProjectQueuesResponse,
  ProjectTasksResponse,
  ProjectsResponse,
  RunOverview,
  UiActionExecuteRequest,
  UiActionExecutionResult,
  UiActionMetadata,
  UiActionsResponse,
  WorkerExecutionMetadata,
  WorkerReview,
  WorkerReviewsResponse,
  WorkerRun,
  WorkerReportsResponse,
  WorkerRunsResponse,
  WorkPackageOverview
} from '../types/devo';

const DEFAULT_API_BASE = 'http://127.0.0.1:8765';

const API_BASE = (import.meta.env.VITE_DEVO_API_BASE || DEFAULT_API_BASE).replace(/\/$/, '');

async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    method: 'GET',
    headers: {
      Accept: 'application/json'
    }
  });

  if (!response.ok) {
    const body = await response.text();
    throw new Error(`GET ${path} failed: ${response.status} ${body}`);
  }

  return (await response.json()) as T;
}

async function postJson<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(body)
  });

  if (!response.ok) {
    const responseBody = await response.text();
    throw new Error(`POST ${path} failed: ${response.status} ${responseBody}`);
  }

  return (await response.json()) as T;
}

export const devoApi = {
  baseUrl: API_BASE,
  getHealth: () => getJson<ApiHealth>('/api/health'),
  getCurrent: () => getJson<CurrentContext>('/api/current'),
  getProjects: () => getJson<ProjectsResponse>('/api/projects'),
  getProjectOverview: (project: string) => getJson<ProjectOverview>(`/api/projects/${encodeURIComponent(project)}/overview`),
  getProjectBrief: (project: string) => getJson<ProjectBrief>(`/api/projects/${encodeURIComponent(project)}/brief`),
  getProjectBlueprint: (project: string) => getJson<ProjectBlueprint>(`/api/projects/${encodeURIComponent(project)}/blueprint`),
  getProjectBacklog: (project: string) => getJson<ProjectBacklog>(`/api/projects/${encodeURIComponent(project)}/backlog`),
  getProjectTasks: (project: string) => getJson<ProjectTasksResponse>(`/api/projects/${encodeURIComponent(project)}/tasks`),
  getProjectBatches: (project: string) => getJson<ProjectBatchesResponse>(`/api/projects/${encodeURIComponent(project)}/batches`),
  getProjectBatchApprovals: (project: string) => getJson<BatchApprovalsResponse>(`/api/projects/${encodeURIComponent(project)}/batch-approvals`),
  getProjectBatch: (project: string, batchId: string) =>
    getJson<ProjectBatch>(`/api/projects/${encodeURIComponent(project)}/batches/${encodeURIComponent(batchId)}`),
  getProjectBatchApproval: (project: string, batchId: string) =>
    getJson<BatchApproval>(`/api/projects/${encodeURIComponent(project)}/batches/${encodeURIComponent(batchId)}/approval`),
  getProjectQueues: (project: string) => getJson<ProjectQueuesResponse>(`/api/projects/${encodeURIComponent(project)}/queues`),
  getProjectQueue: (project: string, queueId: string) =>
    getJson<ExecutionQueue>(`/api/projects/${encodeURIComponent(project)}/queues/${encodeURIComponent(queueId)}`),
  getProjectQueueWorkerStatus: (project: string, queueId: string) =>
    getJson<CodexQueueWorkerStatus>(`/api/projects/${encodeURIComponent(project)}/queues/${encodeURIComponent(queueId)}/worker-status`),
  getProjectHandoffs: (project: string) => getJson<ProjectHandoffsResponse>(`/api/projects/${encodeURIComponent(project)}/handoffs`),
  getProjectHandoff: (project: string, handoffId: string) =>
    getJson<CodexHandoff>(`/api/projects/${encodeURIComponent(project)}/handoffs/${encodeURIComponent(handoffId)}`),
  getProjectWorkerRuns: (project: string) => getJson<WorkerRunsResponse>(`/api/projects/${encodeURIComponent(project)}/worker-runs`),
  getProjectWorkerRun: (project: string, workerRunId: string) =>
    getJson<WorkerRun>(`/api/projects/${encodeURIComponent(project)}/worker-runs/${encodeURIComponent(workerRunId)}`),
  getProjectWorkerRunExecution: (project: string, workerRunId: string) =>
    getJson<WorkerExecutionMetadata>(`/api/projects/${encodeURIComponent(project)}/worker-runs/${encodeURIComponent(workerRunId)}/execution`),
  getProjectWorkerReports: (project: string) => getJson<WorkerReportsResponse>(`/api/projects/${encodeURIComponent(project)}/worker-reports`),
  getProjectWorkerReport: (project: string, workerRunId: string) =>
    getJson<CodexWorkerReport>(`/api/projects/${encodeURIComponent(project)}/worker-runs/${encodeURIComponent(workerRunId)}/report`),
  getProjectWorkerReviews: (project: string) => getJson<WorkerReviewsResponse>(`/api/projects/${encodeURIComponent(project)}/worker-reviews`),
  getProjectWorkerReview: (project: string, workerRunId: string) =>
    getJson<WorkerReview>(`/api/projects/${encodeURIComponent(project)}/worker-runs/${encodeURIComponent(workerRunId)}/review`),
  getProjectWorkerRunPlans: (project: string) => getJson<CodexRunPlansResponse>(`/api/projects/${encodeURIComponent(project)}/worker-run-plans`),
  getProjectWorkerRunPlan: (project: string, planId: string) =>
    getJson<CodexRunPlan>(`/api/projects/${encodeURIComponent(project)}/worker-run-plans/${encodeURIComponent(planId)}`),
  getProjectProgress: (project: string) => getJson<ProjectProgress>(`/api/projects/${encodeURIComponent(project)}/progress`),
  getProjectActivity: (project: string) => getJson<ProjectActivity>(`/api/projects/${encodeURIComponent(project)}/activity`),
  getProjectDoctor: (project: string) => getJson<DoctorReport>(`/api/projects/${encodeURIComponent(project)}/doctor`),
  getProjectDeliveryChecks: (project: string) => getJson<DeliveryChecksResponse>(`/api/projects/${encodeURIComponent(project)}/delivery-checks`),
  getProjectDeliveryPlans: (project: string) => getJson<DeliveryPlansResponse>(`/api/projects/${encodeURIComponent(project)}/delivery-plans`),
  getProjectDeliveryApprovals: (project: string) =>
    getJson<DeliveryApprovalsResponse>(`/api/projects/${encodeURIComponent(project)}/delivery-approvals`),
  getProjectDeliveryReports: (project: string) =>
    getJson<DeliveryReportsResponse>(`/api/projects/${encodeURIComponent(project)}/delivery-reports`),
  getProjectDeliveryCommit: (project: string, deliveryId: string) =>
    getJson<DeliveryCommitResult>(`/api/projects/${encodeURIComponent(project)}/delivery-reports/${encodeURIComponent(deliveryId)}/commit`),
  getProjectDeliveryPush: (project: string, deliveryId: string) =>
    getJson<DeliveryPushResult>(`/api/projects/${encodeURIComponent(project)}/delivery-reports/${encodeURIComponent(deliveryId)}/push`),
  getRunOverview: (project: string, runId: string) =>
    getJson<RunOverview>(`/api/projects/${encodeURIComponent(project)}/runs/${encodeURIComponent(runId)}/overview`),
  getWorkPackageOverview: (project: string, runId: string) =>
    getJson<WorkPackageOverview>(`/api/projects/${encodeURIComponent(project)}/runs/${encodeURIComponent(runId)}/work-package`),
  getUiActions: () => getJson<UiActionsResponse>('/api/actions'),
  getAllowedUiActions: () => getJson<UiActionsResponse>('/api/actions/allowed'),
  getUiAction: (actionId: string) => getJson<UiActionMetadata>(`/api/actions/${encodeURIComponent(actionId)}`),
  executeUiAction: (request: UiActionExecuteRequest) => postJson<UiActionExecutionResult>('/api/actions/execute', request)
};
