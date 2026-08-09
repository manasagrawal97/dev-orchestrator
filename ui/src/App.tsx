import { useEffect, useMemo, useState } from 'react';
import { devoApi } from './api/client';
import { ActionSafetyPage } from './pages/ActionSafetyPage';
import { ActivityPage } from './pages/ActivityPage';
import { BacklogPage } from './pages/BacklogPage';
import { BatchesPage } from './pages/BatchesPage';
import { BlueprintPage } from './pages/BlueprintPage';
import { DeliveryPage } from './pages/DeliveryPage';
import { HandoffsPage } from './pages/HandoffsPage';
import { HealthPage } from './pages/HealthPage';
import { PlanningIntakePage } from './pages/PlanningIntakePage';
import { ProgressPage } from './pages/ProgressPage';
import { ProjectOverviewPage } from './pages/ProjectOverviewPage';
import { ProjectsPage } from './pages/ProjectsPage';
import { QueuesPage } from './pages/QueuesPage';
import { WorkerRunsPage } from './pages/WorkerRunsPage';
import { WorkPackagePage } from './pages/WorkPackagePage';
import type { CurrentContext } from './types/devo';

type PageId =
  | 'projects'
  | 'overview'
  | 'planning'
  | 'blueprint'
  | 'backlog'
  | 'batches'
  | 'queues'
  | 'handoffs'
  | 'worker-runs'
  | 'progress'
  | 'delivery'
  | 'work'
  | 'activity'
  | 'health'
  | 'actions';

const pages: Array<{ id: PageId; label: string }> = [
  { id: 'projects', label: 'Projects' },
  { id: 'overview', label: 'Project Overview' },
  { id: 'planning', label: 'Planning Intake' },
  { id: 'blueprint', label: 'Blueprint' },
  { id: 'backlog', label: 'Backlog' },
  { id: 'batches', label: 'Batches' },
  { id: 'queues', label: 'Queues' },
  { id: 'handoffs', label: 'Handoffs' },
  { id: 'worker-runs', label: 'Worker Runs' },
  { id: 'progress', label: 'Progress' },
  { id: 'delivery', label: 'Delivery' },
  { id: 'work', label: 'Work Package' },
  { id: 'activity', label: 'Activity' },
  { id: 'health', label: 'Health' },
  { id: 'actions', label: 'Action Safety' }
];

export default function App() {
  const [activePage, setActivePage] = useState<PageId>('projects');
  const [selectedProject, setSelectedProject] = useState<string | null>(null);
  const [selectedRun, setSelectedRun] = useState<string | null>(null);
  const [current, setCurrent] = useState<CurrentContext | null>(null);

  useEffect(() => {
    let active = true;
    devoApi
      .getCurrent()
      .then((data) => {
        if (active) {
          setCurrent(data);
          if (data.project) {
            setSelectedProject(data.project);
          }
          if (data.run) {
            setSelectedRun(data.run);
          }
        }
      })
      .catch(() => {
        if (active) {
          setCurrent(null);
        }
      });
    return () => {
      active = false;
    };
  }, []);

  const pageTitle = useMemo(() => pages.find((page) => page.id === activePage)?.label ?? 'Projects', [activePage]);

  function selectProject(project: string) {
    setSelectedProject(project);
    setSelectedRun(null);
    setActivePage('overview');
  }

  function selectRun(runId: string) {
    setSelectedRun(runId);
    setActivePage('work');
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">DevOrchestrator</p>
          <h1>Devo Dashboard</h1>
        </div>
        <div className="api-pill">
          <span>API</span>
          <strong>{devoApi.baseUrl}</strong>
        </div>
      </header>

      <div className="body-shell">
        <aside className="sidebar" aria-label="Dashboard navigation">
          <nav>
            {pages.map((page) => (
              <button
                className={page.id === activePage ? 'nav-button active' : 'nav-button'}
                key={page.id}
                type="button"
                onClick={() => setActivePage(page.id)}
              >
                {page.label}
              </button>
            ))}
          </nav>
          <div className="context-panel">
            <span>Dashboard selection</span>
            <strong>{selectedProject ?? 'none'}</strong>
            <span>Selected run</span>
            <strong>{selectedRun ?? 'none'}</strong>
          </div>
          <div className="context-panel cli-context">
            <span>CLI current context</span>
            <strong>{current?.project ?? 'none'}</strong>
            <span>CLI current run</span>
            <strong>{current?.run ?? 'none'}</strong>
            {!current?.project ? <small>Select a project or run `devo use --project &lt;project&gt;`.</small> : null}
          </div>
        </aside>

        <main className="content-shell">
          <section className="readonly-banner">
            <strong>Read-only dashboard.</strong>
            <span>Use CLI/Codex for approvals, validation, delivery, restore, and scheduler changes.</span>
          </section>

          <div className="page-title">
            <p className="eyebrow">Dashboard</p>
            <h2>{pageTitle}</h2>
          </div>

          {activePage === 'projects' ? <ProjectsPage selectedProject={selectedProject} onSelectProject={selectProject} /> : null}
          {activePage === 'overview' ? <ProjectOverviewPage selectedProject={selectedProject} onSelectRun={selectRun} onOpenPage={setActivePage} /> : null}
          {activePage === 'planning' ? <PlanningIntakePage selectedProject={selectedProject} onOpenPage={setActivePage} /> : null}
          {activePage === 'blueprint' ? <BlueprintPage selectedProject={selectedProject} /> : null}
          {activePage === 'backlog' ? <BacklogPage selectedProject={selectedProject} /> : null}
          {activePage === 'batches' ? <BatchesPage selectedProject={selectedProject} /> : null}
          {activePage === 'queues' ? <QueuesPage selectedProject={selectedProject} /> : null}
          {activePage === 'handoffs' ? <HandoffsPage selectedProject={selectedProject} onOpenPage={setActivePage} /> : null}
          {activePage === 'worker-runs' ? <WorkerRunsPage selectedProject={selectedProject} /> : null}
          {activePage === 'progress' ? <ProgressPage selectedProject={selectedProject} /> : null}
          {activePage === 'delivery' ? <DeliveryPage selectedProject={selectedProject} /> : null}
          {activePage === 'work' ? (
            <WorkPackagePage
              selectedProject={selectedProject}
              selectedRun={selectedRun}
              onSelectRun={setSelectedRun}
              onOpenRun={selectRun}
            />
          ) : null}
          {activePage === 'activity' ? <ActivityPage selectedProject={selectedProject} /> : null}
          {activePage === 'health' ? <HealthPage selectedProject={selectedProject} /> : null}
          {activePage === 'actions' ? <ActionSafetyPage selectedProject={selectedProject} selectedRun={selectedRun} /> : null}
        </main>
      </div>
    </div>
  );
}
