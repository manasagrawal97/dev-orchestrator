import { useEffect, useMemo, useState } from 'react';
import { devoApi } from '../api/client';
import { CommandCopyBox } from '../components/CommandCopyBox';
import { KeyValueList } from '../components/KeyValueList';
import { EmptyState, ErrorState, LoadingState } from '../components/SectionState';
import { StatusBadge } from '../components/StatusBadge';
import { SummaryCard } from '../components/SummaryCard';
import type { ProjectBacklog, ProjectBatchesResponse, ProjectOverview, ProjectProgress, ProjectQueuesResponse, PlanningProgressGroup } from '../types/devo';

interface ProgressPageProps {
  selectedProject: string | null;
}

interface OptionalState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
}

const emptyOptional = <T,>(): OptionalState<T> => ({ data: null, loading: false, error: null });

export function ProgressPage({ selectedProject }: ProgressPageProps) {
  const [progress, setProgress] = useState<OptionalState<ProjectProgress>>(emptyOptional);
  const [overview, setOverview] = useState<OptionalState<ProjectOverview>>(emptyOptional);
  const [backlog, setBacklog] = useState<OptionalState<ProjectBacklog>>(emptyOptional);
  const [batches, setBatches] = useState<OptionalState<ProjectBatchesResponse>>(emptyOptional);
  const [queues, setQueues] = useState<OptionalState<ProjectQueuesResponse>>(emptyOptional);

  useEffect(() => {
    if (!selectedProject) {
      setProgress(emptyOptional<ProjectProgress>());
      setOverview(emptyOptional<ProjectOverview>());
      setBacklog(emptyOptional<ProjectBacklog>());
      setBatches(emptyOptional<ProjectBatchesResponse>());
      setQueues(emptyOptional<ProjectQueuesResponse>());
      return;
    }

    let active = true;
    setProgress({ data: null, loading: true, error: null });
    setOverview({ data: null, loading: true, error: null });
    setBacklog({ data: null, loading: true, error: null });
    setBatches({ data: null, loading: true, error: null });
    setQueues({ data: null, loading: true, error: null });

    loadOptional(devoApi.getProjectProgress(selectedProject)).then((state) => active && setProgress(state));
    loadOptional(devoApi.getProjectOverview(selectedProject)).then((state) => active && setOverview(state));
    loadOptional(devoApi.getProjectBacklog(selectedProject)).then((state) => active && setBacklog(state));
    loadOptional(devoApi.getProjectBatches(selectedProject)).then((state) => active && setBatches(state));
    loadOptional(devoApi.getProjectQueues(selectedProject)).then((state) => active && setQueues(state));

    return () => {
      active = false;
    };
  }, [selectedProject]);

  const queueTotals = useMemo(
    () =>
      (queues.data?.queues ?? []).reduce(
        (acc, queue) => ({
          pending: acc.pending + queue.pending_count,
          running: acc.running + (queue.running_count ?? 0),
          completed: acc.completed + queue.completed_count,
          blocked: acc.blocked + queue.blocked_count,
          failed: acc.failed + (queue.failed_count ?? 0)
        }),
        { pending: 0, running: 0, completed: 0, blocked: 0, failed: 0 }
      ),
    [queues.data]
  );

  const batchCounts = useMemo(() => {
    const list = batches.data?.batches ?? [];
    return {
      total: list.length,
      approved: list.filter((batch) => batch.approval_status === 'approved').length,
      active: list.filter((batch) => ['approved', 'in_progress', 'reviewed'].includes(batch.status)).length,
      completed: list.filter((batch) => batch.status === 'completed').length
    };
  }, [batches.data]);

  if (!selectedProject) {
    return <p className="muted">Select a project to view progress.</p>;
  }

  if (progress.loading) {
    return <LoadingState message="Loading progress dashboard..." />;
  }

  if (progress.error) {
    return <ErrorState message={progress.error} />;
  }

  if (!progress.data) {
    return (
      <section>
        <div className="section-heading">
          <h2>Progress</h2>
          <p>{selectedProject}</p>
        </div>
        <EmptyState message="No progress summary is available yet.">
          <CommandCopyBox command={`devo project progress --project ${selectedProject}`} />
        </EmptyState>
      </section>
    );
  }

  return (
    <section>
      <div className="section-heading">
        <h2>Progress</h2>
        <p>{selectedProject}</p>
      </div>

      <div className="summary-grid">
        <SummaryCard title="Project completion" value={`${progress.data.project_completion_percent.toFixed(1)}%`} />
        <SummaryCard title="Backlog readiness" value={`${progress.data.backlog_readiness_percent.toFixed(1)}%`} />
        <SummaryCard title="Blocked" value={`${progress.data.blocked_percent.toFixed(1)}%`} />
        <SummaryCard title="Batch completion" value={`${progress.data.batch_completion_percent.toFixed(1)}%`} />
      </div>

      <section className="panel detail-panel">
        <h3>Progress Bars</h3>
        <ProgressBar label="Project completion" value={progress.data.project_completion_percent} />
        <ProgressBar label="Backlog readiness" value={progress.data.backlog_readiness_percent} />
        <ProgressBar label="Blocked tasks" value={progress.data.blocked_percent} />
        <ProgressBar label="Batch completion" value={progress.data.batch_completion_percent} />
      </section>

      <div className="dashboard-grid">
        <SummaryCard title="Task Counts">
          <KeyValueList
            items={[
              ['Total', progress.data.task_count],
              ['Draft', progress.data.draft_task_count],
              ['Ready', progress.data.ready_task_count],
              ['Approved', progress.data.approved_task_count],
              ['Active', progress.data.active_task_count],
              ['Completed', progress.data.completed_task_count],
              ['Blocked', progress.data.blocked_task_count],
              ['Backlog status', backlog.data?.status ?? progress.data.backlog_status]
            ]}
          />
        </SummaryCard>

        <SummaryCard title="Batch Counts">
          <KeyValueList
            items={[
              ['Total', progress.data.batch_count || batchCounts.total],
              ['Approved', progress.data.approved_batch_count || batchCounts.approved],
              ['Active', progress.data.active_batch_count || batchCounts.active],
              ['Completed', progress.data.completed_batch_count || batchCounts.completed],
              ['Latest batch', progress.data.latest_batch_id ?? overview.data?.latest_batch_id ?? 'none'],
              ['Latest status', progress.data.latest_batch_status ?? overview.data?.latest_batch_status ?? 'none']
            ]}
          />
        </SummaryCard>

        <SummaryCard title="Queue Counts">
          <KeyValueList
            items={[
              ['Total', queues.data?.count ?? overview.data?.queue_count ?? 0],
              ['Latest queue', overview.data?.latest_queue_id ?? queues.data?.queues[0]?.queue_id ?? 'none'],
              ['Latest status', overview.data?.latest_queue_status ?? queues.data?.queues[0]?.status ?? 'none'],
              ['Pending', overview.data?.queue_pending_count ?? queueTotals.pending],
              ['Running', queueTotals.running],
              ['Completed', overview.data?.queue_completed_count ?? queueTotals.completed],
              ['Blocked', overview.data?.queue_blocked_count ?? queueTotals.blocked],
              ['Failed', queueTotals.failed]
            ]}
          />
        </SummaryCard>

        <SummaryCard title="Next Action">
          <p>{progress.data.next_action}</p>
          <CommandCopyBox command={`devo project progress --project ${selectedProject}`} />
        </SummaryCard>
      </div>

      {progress.data.warnings.length ? (
        <section className="panel detail-panel">
          <h3>Warnings</h3>
          <ul className="plain-list compact-list">
            {progress.data.warnings.map((warning) => (
              <li key={warning}>{warning}</li>
            ))}
          </ul>
        </section>
      ) : (
        <SummaryCard title="Warnings" value="none" />
      )}

      <div className="two-column">
        <ProgressGroupList title="Milestone Progress" groups={progress.data.milestone_progress} />
        <ProgressGroupList title="Epic Progress" groups={progress.data.epic_progress} />
      </div>

      {overview.error ? <ErrorState message={overview.error} /> : null}
      {backlog.error ? <ErrorState message={backlog.error} /> : null}
      {batches.error ? <ErrorState message={batches.error} /> : null}
      {queues.error ? <ErrorState message={queues.error} /> : null}
    </section>
  );
}

function ProgressGroupList({ title, groups }: { title: string; groups: PlanningProgressGroup[] }) {
  return (
    <section className="panel">
      <h3>{title}</h3>
      {groups.length ? (
        <div className="list-stack">
          {groups.map((group) => (
            <div className="detail-card" key={group.id}>
              <div className="detail-card-title">
                <strong>
                  {group.id}: {group.title ?? 'Untitled'}
                </strong>
                <StatusBadge status={`${group.completion_percent.toFixed(1)}%`} />
              </div>
              <ProgressBar label="Completion" value={group.completion_percent} />
              <KeyValueList
                items={[
                  ['Tasks', group.task_count],
                  ['Draft', group.draft_task_count],
                  ['Ready', group.ready_task_count],
                  ['Approved', group.approved_task_count],
                  ['Active', group.active_task_count],
                  ['Completed', group.completed_task_count],
                  ['Blocked', group.blocked_task_count],
                  ['Readiness', `${group.readiness_percent.toFixed(1)}%`],
                  ['Blocked percent', `${group.blocked_percent.toFixed(1)}%`]
                ]}
              />
            </div>
          ))}
        </div>
      ) : (
        <p className="muted compact">No progress groups recorded.</p>
      )}
    </section>
  );
}

function ProgressBar({ label, value }: { label: string; value: number }) {
  const bounded = Math.max(0, Math.min(100, value));
  return (
    <div className="progress-meter">
      <div className="progress-meter-heading">
        <span>{label}</span>
        <strong>{bounded.toFixed(1)}%</strong>
      </div>
      <div className="progress-meter-track">
        <span style={{ width: `${bounded}%` }} />
      </div>
    </div>
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
