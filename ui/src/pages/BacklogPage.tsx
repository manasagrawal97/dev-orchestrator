import { useEffect, useMemo, useState } from 'react';
import { devoApi } from '../api/client';
import { CommandCopyBox } from '../components/CommandCopyBox';
import { KeyValueList } from '../components/KeyValueList';
import { EmptyState, ErrorState, LoadingState } from '../components/SectionState';
import { StatusBadge } from '../components/StatusBadge';
import { SummaryCard } from '../components/SummaryCard';
import type { BacklogTask, ProjectBacklog, ProjectOverview, ProjectProgress, ProjectTasksResponse } from '../types/devo';

interface BacklogPageProps {
  selectedProject: string | null;
}

interface OptionalState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
}

const emptyOptional = <T,>(): OptionalState<T> => ({ data: null, loading: false, error: null });

export function BacklogPage({ selectedProject }: BacklogPageProps) {
  const [overview, setOverview] = useState<OptionalState<ProjectOverview>>(emptyOptional);
  const [backlog, setBacklog] = useState<OptionalState<ProjectBacklog>>(emptyOptional);
  const [tasks, setTasks] = useState<OptionalState<ProjectTasksResponse>>(emptyOptional);
  const [progress, setProgress] = useState<OptionalState<ProjectProgress>>(emptyOptional);
  const [statusFilter, setStatusFilter] = useState('all');
  const [laneFilter, setLaneFilter] = useState('all');
  const [riskFilter, setRiskFilter] = useState('all');
  const [query, setQuery] = useState('');
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);

  useEffect(() => {
    if (!selectedProject) {
      setOverview(emptyOptional<ProjectOverview>());
      setBacklog(emptyOptional<ProjectBacklog>());
      setTasks(emptyOptional<ProjectTasksResponse>());
      setProgress(emptyOptional<ProjectProgress>());
      setSelectedTaskId(null);
      return;
    }

    let active = true;
    setOverview({ data: null, loading: true, error: null });
    setBacklog({ data: null, loading: true, error: null });
    setTasks({ data: null, loading: true, error: null });
    setProgress({ data: null, loading: true, error: null });

    loadOptional(devoApi.getProjectOverview(selectedProject)).then((state) => active && setOverview(state));
    loadOptional(devoApi.getProjectBacklog(selectedProject)).then((state) => active && setBacklog(state));
    loadOptional(devoApi.getProjectTasks(selectedProject)).then((state) => active && setTasks(state));
    loadOptional(devoApi.getProjectProgress(selectedProject)).then((state) => active && setProgress(state));

    return () => {
      active = false;
    };
  }, [selectedProject]);

  const allTasks = tasks.data?.tasks ?? [];
  const filteredTasks = useMemo(
    () =>
      allTasks.filter((task) => {
        const haystack = `${task.id} ${task.title}`.toLowerCase();
        return (
          (statusFilter === 'all' || task.status === statusFilter) &&
          (laneFilter === 'all' || task.lane === laneFilter) &&
          (riskFilter === 'all' || task.risk_level === riskFilter) &&
          (!query.trim() || haystack.includes(query.trim().toLowerCase()))
        );
      }),
    [allTasks, laneFilter, query, riskFilter, statusFilter]
  );

  useEffect(() => {
    if (!allTasks.length) {
      setSelectedTaskId(null);
      return;
    }
    if (!selectedTaskId || !allTasks.some((task) => task.id === selectedTaskId)) {
      setSelectedTaskId(allTasks[0].id);
    }
  }, [allTasks, selectedTaskId]);

  const selectedTask = allTasks.find((task) => task.id === selectedTaskId) ?? filteredTasks[0] ?? null;

  if (!selectedProject) {
    return <p className="muted">Select a project to view its backlog.</p>;
  }

  if (backlog.loading) {
    return <LoadingState message="Loading backlog..." />;
  }

  if (backlog.error) {
    return <ErrorState message={backlog.error} />;
  }

  if (!backlog.data) {
    return (
      <section>
        <div className="section-heading">
          <h2>Backlog</h2>
          <p>{selectedProject}</p>
        </div>
        <EmptyState message="No Backlog artifact is available yet.">
          <CommandCopyBox command={`devo project backlog-create --project ${selectedProject}`} />
        </EmptyState>
      </section>
    );
  }

  return (
    <section>
      <div className="section-heading">
        <h2>Backlog</h2>
        <p>{selectedProject}</p>
      </div>

      <div className="summary-grid">
        <SummaryCard title="Status" value={<StatusBadge status={backlog.data.status} />} />
        <SummaryCard title="Tasks" value={backlog.data.task_count} />
        <SummaryCard title="Ready" value={backlog.data.ready_task_count} />
        <SummaryCard title="Blocked" value={backlog.data.blocked_task_count} />
      </div>

      <div className="dashboard-grid">
        <SummaryCard title={backlog.data.title}>
          <KeyValueList
            items={[
              ['Completed', backlog.data.completed_task_count],
              ['Backlog readiness', progress.data ? `${progress.data.backlog_readiness_percent.toFixed(1)}%` : 'unknown'],
              ['Blocked percent', progress.data ? `${progress.data.blocked_percent.toFixed(1)}%` : 'unknown'],
              ['Refinement prompt', overview.data?.backlog_refinement_prompt_exists ? 'available' : 'missing'],
              ['Markdown', backlog.data.artifact_paths?.markdown ?? 'none']
            ]}
          />
        </SummaryCard>

        <SummaryCard title="CLI guidance">
          <CommandCopyBox command={`devo project backlog-show --project ${selectedProject}`} />
          <CommandCopyBox command={`devo project task-list --project ${selectedProject}`} />
          <CommandCopyBox command={`devo project backlog-prompt --project ${selectedProject}`} />
          <CommandCopyBox command={`devo project backlog-import --project ${selectedProject} --file <file>`} />
          <CommandCopyBox command={`devo project backlog-approve --project ${selectedProject}`} />
        </SummaryCard>
      </div>

      <section className="panel detail-panel">
        <h3>Task Filters</h3>
        <div className="filter-grid">
          <label className="field-label">
            Search
            <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Task id or title" />
          </label>
          <SelectFilter label="Status" value={statusFilter} values={uniqueValues(allTasks.map((task) => task.status))} onChange={setStatusFilter} />
          <SelectFilter label="Lane" value={laneFilter} values={uniqueValues(allTasks.map((task) => task.lane))} onChange={setLaneFilter} />
          <SelectFilter label="Risk" value={riskFilter} values={uniqueValues(allTasks.map((task) => task.risk_level))} onChange={setRiskFilter} />
        </div>
      </section>

      {tasks.loading ? <LoadingState message="Loading backlog tasks..." /> : null}
      {tasks.error ? <ErrorState message={tasks.error} /> : null}

      <div className="two-column">
        <section className="panel">
          <h3>Tasks</h3>
          {filteredTasks.length ? (
            <div className="list-stack">
              {filteredTasks.map((task) => (
                <button className={task.id === selectedTask?.id ? 'work-row selected-row' : 'work-row'} key={task.id} type="button" onClick={() => setSelectedTaskId(task.id)}>
                  <span>
                    {task.id}: {task.title}
                  </span>
                  <small>
                    {task.status} | {task.lane} | {task.risk_level}
                  </small>
                  <small>
                    {task.milestone_id ?? 'no milestone'} / {task.epic_id ?? 'no epic'}
                  </small>
                </button>
              ))}
            </div>
          ) : (
            <p className="muted compact">No tasks match the current filters.</p>
          )}
        </section>

        <section className="panel">
          <h3>Task Detail</h3>
          {selectedTask ? (
            <TaskDetail task={selectedTask} />
          ) : (
            <p className="muted compact">Select a task to inspect details.</p>
          )}
        </section>
      </div>

      {progress.loading ? <LoadingState message="Loading backlog progress..." /> : null}
      {progress.error ? <ErrorState message={progress.error} /> : null}
    </section>
  );
}

function TaskDetail({ task }: { task: BacklogTask }) {
  return (
    <div className="task-detail">
      <div className="detail-card-title">
        <strong>
          {task.id}: {task.title}
        </strong>
        <StatusBadge status={task.status} />
      </div>
      <KeyValueList
        items={[
          ['Lane', task.lane],
          ['Risk', task.risk_level],
          ['Milestone', task.milestone_id ?? 'none'],
          ['Epic', task.epic_id ?? 'none'],
          ['Source', task.source],
          ['Dependencies', task.dependencies]
        ]}
      />
      <p>{task.summary || 'No summary recorded.'}</p>
      <DetailList title="Acceptance Criteria" items={task.acceptance_criteria} />
      <DetailList title="Validation Expectations" items={task.validation_expectations} />
      <DetailList title="Allowed Scope" items={task.allowed_scope} />
      <DetailList title="Forbidden Scope" items={task.forbidden_scope} />
      <DetailList title="Notes" items={task.notes} />
    </div>
  );
}

function DetailList({ title, items }: { title: string; items: string[] }) {
  return (
    <div className="detail-list">
      <strong>{title}</strong>
      {items.length ? (
        <ul className="plain-list compact-list">
          {items.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      ) : (
        <p className="muted compact">No items recorded.</p>
      )}
    </div>
  );
}

function SelectFilter({ label, value, values, onChange }: { label: string; value: string; values: string[]; onChange: (value: string) => void }) {
  return (
    <label className="field-label">
      {label}
      <select value={value} onChange={(event) => onChange(event.target.value)}>
        <option value="all">All</option>
        {values.map((item) => (
          <option key={item} value={item}>
            {item}
          </option>
        ))}
      </select>
    </label>
  );
}

async function loadOptional<T>(request: Promise<T>): Promise<OptionalState<T>> {
  try {
    return { data: await request, loading: false, error: null };
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    if (message.includes('404')) {
      return { data: null, loading: false, error: null };
    }
    return { data: null, loading: false, error: message };
  }
}

function uniqueValues(values: string[]): string[] {
  return Array.from(new Set(values)).sort();
}
