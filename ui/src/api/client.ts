import type {
  ApiHealth,
  CurrentContext,
  DoctorReport,
  ProjectActivity,
  ProjectOverview,
  ProjectsResponse,
  RunOverview,
  UiActionMetadata,
  UiActionsResponse,
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

export const devoApi = {
  baseUrl: API_BASE,
  getHealth: () => getJson<ApiHealth>('/api/health'),
  getCurrent: () => getJson<CurrentContext>('/api/current'),
  getProjects: () => getJson<ProjectsResponse>('/api/projects'),
  getProjectOverview: (project: string) => getJson<ProjectOverview>(`/api/projects/${encodeURIComponent(project)}/overview`),
  getProjectActivity: (project: string) => getJson<ProjectActivity>(`/api/projects/${encodeURIComponent(project)}/activity`),
  getProjectDoctor: (project: string) => getJson<DoctorReport>(`/api/projects/${encodeURIComponent(project)}/doctor`),
  getRunOverview: (project: string, runId: string) =>
    getJson<RunOverview>(`/api/projects/${encodeURIComponent(project)}/runs/${encodeURIComponent(runId)}/overview`),
  getWorkPackageOverview: (project: string, runId: string) =>
    getJson<WorkPackageOverview>(`/api/projects/${encodeURIComponent(project)}/runs/${encodeURIComponent(runId)}/work-package`),
  getUiActions: () => getJson<UiActionsResponse>('/api/actions'),
  getAllowedUiActions: () => getJson<UiActionsResponse>('/api/actions/allowed'),
  getUiAction: (actionId: string) => getJson<UiActionMetadata>(`/api/actions/${encodeURIComponent(actionId)}`)
};
