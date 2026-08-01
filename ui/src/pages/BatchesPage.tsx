import { useEffect, useMemo, useState } from 'react';
import { devoApi } from '../api/client';
import { CommandCopyBox } from '../components/CommandCopyBox';
import { KeyValueList } from '../components/KeyValueList';
import { EmptyState, ErrorState, LoadingState } from '../components/SectionState';
import { StatusBadge } from '../components/StatusBadge';
import { SummaryCard } from '../components/SummaryCard';
import type { BatchApproval, BatchApprovalsResponse, BatchTaskSnapshot, ProjectBatch, ProjectBatchesResponse, ProjectProgress, ProjectTasksResponse } from '../types/devo';

interface BatchesPageProps {
  selectedProject: string | null;
}

interface OptionalState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
}

const emptyOptional = <T,>(): OptionalState<T> => ({ data: null, loading: false, error: null });

export function BatchesPage({ selectedProject }: BatchesPageProps) {
  const [batches, setBatches] = useState<OptionalState<ProjectBatchesResponse>>(emptyOptional);
  const [approvals, setApprovals] = useState<OptionalState<BatchApprovalsResponse>>(emptyOptional);
  const [progress, setProgress] = useState<OptionalState<ProjectProgress>>(emptyOptional);
  const [tasks, setTasks] = useState<OptionalState<ProjectTasksResponse>>(emptyOptional);
  const [selectedBatchId, setSelectedBatchId] = useState<string | null>(null);
  const [selectedBatch, setSelectedBatch] = useState<OptionalState<ProjectBatch>>(emptyOptional);
  const [selectedApproval, setSelectedApproval] = useState<OptionalState<BatchApproval>>(emptyOptional);

  useEffect(() => {
    if (!selectedProject) {
      setBatches(emptyOptional<ProjectBatchesResponse>());
      setApprovals(emptyOptional<BatchApprovalsResponse>());
      setProgress(emptyOptional<ProjectProgress>());
      setTasks(emptyOptional<ProjectTasksResponse>());
      setSelectedBatchId(null);
      setSelectedBatch(emptyOptional<ProjectBatch>());
      setSelectedApproval(emptyOptional<BatchApproval>());
      return;
    }

    let active = true;
    setBatches({ data: null, loading: true, error: null });
    setApprovals({ data: null, loading: true, error: null });
    setProgress({ data: null, loading: true, error: null });
    setTasks({ data: null, loading: true, error: null });
    setSelectedBatch(emptyOptional<ProjectBatch>());
    setSelectedApproval(emptyOptional<BatchApproval>());

    loadOptional(devoApi.getProjectBatches(selectedProject)).then((state) => {
      if (!active) {
        return;
      }
      setBatches(state);
      setSelectedBatchId((current) => current ?? state.data?.batches[0]?.batch_id ?? null);
    });
    loadOptional(devoApi.getProjectBatchApprovals(selectedProject)).then((state) => active && setApprovals(state));
    loadOptional(devoApi.getProjectProgress(selectedProject)).then((state) => active && setProgress(state));
    loadOptional(devoApi.getProjectTasks(selectedProject)).then((state) => active && setTasks(state));

    return () => {
      active = false;
    };
  }, [selectedProject]);

  useEffect(() => {
    if (!selectedProject || !selectedBatchId) {
      setSelectedBatch(emptyOptional<ProjectBatch>());
      setSelectedApproval(emptyOptional<BatchApproval>());
      return;
    }

    let active = true;
    setSelectedBatch({ data: null, loading: true, error: null });
    setSelectedApproval({ data: null, loading: true, error: null });
    loadOptional(devoApi.getProjectBatch(selectedProject, selectedBatchId)).then((state) => active && setSelectedBatch(state));
    loadOptional(devoApi.getProjectBatchApproval(selectedProject, selectedBatchId)).then((state) => active && setSelectedApproval(state));
    return () => {
      active = false;
    };
  }, [selectedBatchId, selectedProject]);

  const batchList = batches.data?.batches ?? [];
  const latestBatch = batchList[0] ?? null;
  const approvedCount = useMemo(() => batchList.filter((batch) => batch.approval_status === 'approved').length, [batchList]);
  const selected = selectedBatch.data ?? batchList.find((batch) => batch.batch_id === selectedBatchId) ?? null;
  const approvalList = approvals.data?.approvals ?? [];
  const selectedApprovalData = selectedApproval.data ?? approvalList.find((approval) => approval.batch_id === selectedBatchId) ?? null;
  const approvalRequestedCount = useMemo(() => approvalList.filter((approval) => approval.approval_status === 'requested').length, [approvalList]);
  const rejectedCount = useMemo(() => approvalList.filter((approval) => approval.approval_status === 'rejected').length, [approvalList]);
  const needsChangesCount = useMemo(() => approvalList.filter((approval) => approval.review_status === 'needs_changes').length, [approvalList]);
  const taskStatusById = useMemo(() => {
    const result: Record<string, string> = {};
    for (const task of tasks.data?.tasks ?? []) {
      result[task.id] = task.status;
    }
    return result;
  }, [tasks.data]);

  if (!selectedProject) {
    return <p className="muted">Select a project to view planning batches.</p>;
  }

  return (
    <section>
      <div className="section-heading">
        <h2>Batches</h2>
        <p>{selectedProject}</p>
      </div>

      <div className="summary-grid">
        <SummaryCard title="Batches" value={batches.loading ? 'Loading' : batches.data?.count ?? 0} />
        <SummaryCard title="Approved" value={approvedCount} />
        <SummaryCard title="Requested" value={approvalRequestedCount} />
        <SummaryCard title="Needs changes" value={needsChangesCount} />
        <SummaryCard title="Rejected" value={rejectedCount} />
        <SummaryCard title="Latest batch" value={latestBatch?.batch_id ?? 'none'} />
        <SummaryCard title="Completion" value={progress.data ? `${progress.data.batch_completion_percent.toFixed(1)}%` : 'unknown'} />
      </div>

      {batches.loading ? <LoadingState message="Loading batches..." /> : null}
      {batches.error ? <ErrorState message={batches.error} /> : null}
      {!batches.loading && !batches.error && !batchList.length ? (
        <EmptyState message="No batch artifacts are available yet.">
          <CommandCopyBox command={`devo project batch-suggest --project ${selectedProject} --limit 10`} />
          <CommandCopyBox command={`devo project batch-suggest --project ${selectedProject} --limit 10 --write`} />
        </EmptyState>
      ) : null}

      {batchList.length ? (
        <>
          <div className="two-column">
            <section className="panel">
              <h3>Batch List</h3>
              <div className="list-stack">
                {batchList.map((batch) => (
                  <button
                    className={batch.batch_id === selectedBatchId ? 'work-row selected-row' : 'work-row'}
                    key={batch.batch_id}
                    type="button"
                    onClick={() => setSelectedBatchId(batch.batch_id)}
                  >
                    <span>
                      {batch.batch_id}: {batch.title}
                    </span>
                    <small>
                      {batch.status} | approval {batch.approval_status} | review {batch.review_status} | {batch.task_count} tasks
                    </small>
                    <small>
                      {batch.completed_task_count ?? 0} completed, {batch.blocked_task_count ?? 0} blocked
                    </small>
                    <small>Risk {formatSummary(batch.risk_summary)} | Lane {formatSummary(batch.lane_summary)}</small>
                  </button>
                ))}
              </div>
            </section>

            <section className="panel">
              <h3>Selected Batch</h3>
              {selectedBatch.loading ? <LoadingState message="Loading batch detail..." /> : null}
              {selectedBatch.error ? <ErrorState message={selectedBatch.error} /> : null}
              {selected ? (
                <BatchDetail batch={selected} approval={selectedApprovalData} approvalLoading={selectedApproval.loading} taskStatusById={taskStatusById} />
              ) : (
                <p className="muted compact">Select a batch to inspect details.</p>
              )}
            </section>
          </div>

          <SummaryCard title="CLI Guidance">
            <CommandCopyBox command={`devo project batch-list --project ${selectedProject}`} />
            <CommandCopyBox command={`devo project batch-show --project ${selectedProject} --batch ${selectedBatchId ?? '<batchId>'}`} />
            <CommandCopyBox command={`devo project batch-approval-request --project ${selectedProject} --batch ${selectedBatchId ?? '<batchId>'} --note "<note>"`} />
            <CommandCopyBox command={`devo project batch-approval-show --project ${selectedProject} --batch ${selectedBatchId ?? '<batchId>'}`} />
            <CommandCopyBox command={`devo project batch-suggest --project ${selectedProject} --limit 10`} />
            <CommandCopyBox command={`devo project batch-suggest --project ${selectedProject} --limit 10 --write`} />
            <CommandCopyBox command={`devo project batch-review --project ${selectedProject} --batch ${selectedBatchId ?? '<batchId>'} --note "<review note>"`} />
            <CommandCopyBox command={`devo project batch-review --project ${selectedProject} --batch ${selectedBatchId ?? '<batchId>'} --note "<review note>" --needs-changes`} />
            <CommandCopyBox command={`devo project batch-approve --project ${selectedProject} --batch ${selectedBatchId ?? '<batchId>'} --note "<decision note>"`} />
            <CommandCopyBox command={`devo project batch-reject --project ${selectedProject} --batch ${selectedBatchId ?? '<batchId>'} --note "<decision note>"`} />
          </SummaryCard>
        </>
      ) : null}

      {approvals.loading ? <LoadingState message="Loading batch approval metadata..." /> : null}
      {approvals.error ? <ErrorState message={approvals.error} /> : null}
      {progress.loading ? <LoadingState message="Loading batch progress..." /> : null}
      {progress.error ? <ErrorState message={progress.error} /> : null}
      {tasks.error ? <ErrorState message={tasks.error} /> : null}
    </section>
  );
}

function BatchDetail({
  batch,
  approval,
  approvalLoading,
  taskStatusById
}: {
  batch: ProjectBatch;
  approval: BatchApproval | null;
  approvalLoading: boolean;
  taskStatusById: Record<string, string>;
}) {
  return (
    <div className="task-detail">
      <div className="detail-card-title">
        <strong>
          {batch.batch_id}: {batch.title}
        </strong>
        <StatusBadge status={batch.status} />
      </div>
      <KeyValueList
        items={[
          ['Approval', batch.approval_status],
          ['Review', batch.review_status],
          ['Tasks', batch.task_count],
          ['Completed', batch.completed_task_count],
          ['Blocked', batch.blocked_task_count],
          ['Risk summary', batch.risk_summary],
          ['Lane summary', batch.lane_summary],
          ['Source backlog', batch.source_backlog_reference],
          ['Updated', batch.updated_at ?? 'unknown']
        ]}
      />
      <p>{batch.summary || 'No summary recorded.'}</p>
      <div className="detail-list">
        <strong>Approval Artifact</strong>
        {approvalLoading ? <LoadingState message="Loading approval artifact..." /> : null}
        {approval ? (
          <KeyValueList
            items={[
              ['Approval status', approval.approval_status],
              ['Review status', approval.review_status],
              ['Requested', approval.requested_at ?? 'none'],
              ['Reviewed', approval.reviewed_at ?? 'none'],
              ['Approved', approval.approved_at ?? 'none'],
              ['Rejected', approval.rejected_at ?? 'none'],
              ['High-risk tasks', approval.high_risk_task_count],
              ['Blocked dependencies', approval.blocked_dependency_count],
              ['Decision note', approval.decision_note || 'none'],
              ['Next action', approval.next_action]
            ]}
          />
        ) : approvalLoading ? null : (
          <p className="muted compact">No approval request artifact recorded for this batch.</p>
        )}
      </div>
      <DetailList title="Dependencies" items={batch.dependencies} />
      <DetailList title="Dependency Warnings" items={approval?.dependency_warnings ?? batch.dependency_warnings} />
      <DetailList title="Scope Summary" items={approval?.scope_summary ?? []} />
      <DetailList title="Validation Summary" items={approval?.validation_summary ?? []} />
      <DetailList title="Review Notes" items={approval?.review_notes ?? batch.review_notes} />
      <div className="detail-list">
        <strong>Task Snapshots</strong>
        {batch.task_snapshots.length ? (
          <div className="detail-card-grid">
            {batch.task_snapshots.map((task) => (
              <TaskSnapshotCard key={task.task_id} task={task} currentStatus={taskStatusById[task.task_id]} />
            ))}
          </div>
        ) : (
          <p className="muted compact">No task snapshots recorded.</p>
        )}
      </div>
    </div>
  );
}

function TaskSnapshotCard({ task, currentStatus }: { task: BatchTaskSnapshot; currentStatus?: string }) {
  return (
    <div className="detail-card">
      <div className="detail-card-title">
        <strong>
          {task.task_id}: {task.title}
        </strong>
        <StatusBadge status={currentStatus ?? task.status} />
      </div>
      <KeyValueList
        items={[
          ['Lane', task.lane],
          ['Risk', task.risk_level],
          ['Snapshot status', task.status],
          ['Current status', currentStatus ?? 'unknown'],
          ['Dependencies', task.dependencies]
        ]}
      />
      <p>{task.acceptance_criteria_summary || 'No acceptance criteria summary recorded.'}</p>
      <p>{task.validation_expectations_summary || 'No validation expectations summary recorded.'}</p>
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

function formatSummary(value: Record<string, number> | undefined): string {
  if (!value || !Object.keys(value).length) {
    return 'none';
  }
  return Object.entries(value)
    .map(([key, count]) => `${key}:${count}`)
    .join(', ');
}
