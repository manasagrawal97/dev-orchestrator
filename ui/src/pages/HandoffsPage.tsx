import { useEffect, useState } from 'react';
import { devoApi } from '../api/client';
import { CommandCopyBox } from '../components/CommandCopyBox';
import { KeyValueList } from '../components/KeyValueList';
import { EmptyState, ErrorState, LoadingState } from '../components/SectionState';
import { StatusBadge } from '../components/StatusBadge';
import { SummaryCard } from '../components/SummaryCard';
import type { CodexHandoff, ProjectHandoffsResponse, WorkerRunsResponse } from '../types/devo';

interface HandoffsPageProps {
  selectedProject: string | null;
}

interface OptionalState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
}

const emptyOptional = <T,>(): OptionalState<T> => ({ data: null, loading: false, error: null });

export function HandoffsPage({ selectedProject }: HandoffsPageProps) {
  const [handoffs, setHandoffs] = useState<OptionalState<ProjectHandoffsResponse>>(emptyOptional);
  const [workerRuns, setWorkerRuns] = useState<OptionalState<WorkerRunsResponse>>(emptyOptional);
  const [selectedHandoffId, setSelectedHandoffId] = useState<string | null>(null);
  const [selectedHandoff, setSelectedHandoff] = useState<OptionalState<CodexHandoff>>(emptyOptional);

  useEffect(() => {
    if (!selectedProject) {
      setHandoffs(emptyOptional<ProjectHandoffsResponse>());
      setWorkerRuns(emptyOptional<WorkerRunsResponse>());
      setSelectedHandoffId(null);
      setSelectedHandoff(emptyOptional<CodexHandoff>());
      return;
    }

    let active = true;
    setHandoffs({ data: null, loading: true, error: null });
    setWorkerRuns({ data: null, loading: true, error: null });
    setSelectedHandoff(emptyOptional<CodexHandoff>());

    loadOptional(devoApi.getProjectHandoffs(selectedProject)).then((state) => {
      if (!active) {
        return;
      }
      setHandoffs(state);
      setSelectedHandoffId((current) => current ?? state.data?.handoffs[0]?.handoff_id ?? null);
    });

    loadOptional(devoApi.getProjectWorkerRuns(selectedProject)).then((state) => {
      if (active) {
        setWorkerRuns(state);
      }
    });

    return () => {
      active = false;
    };
  }, [selectedProject]);

  useEffect(() => {
    if (!selectedProject || !selectedHandoffId) {
      setSelectedHandoff(emptyOptional<CodexHandoff>());
      return;
    }

    let active = true;
    setSelectedHandoff({ data: null, loading: true, error: null });
    loadOptional(devoApi.getProjectHandoff(selectedProject, selectedHandoffId)).then((state) => active && setSelectedHandoff(state));
    return () => {
      active = false;
    };
  }, [selectedHandoffId, selectedProject]);

  const handoffList = handoffs.data?.handoffs ?? [];
  const workerRunList = workerRuns.data?.worker_runs ?? [];
  const latestHandoff = handoffList[0] ?? null;
  const latestWorkerRun = workerRunList[0] ?? null;
  const selected = selectedHandoff.data ?? handoffList.find((handoff) => handoff.handoff_id === selectedHandoffId) ?? null;

  if (!selectedProject) {
    return <p className="muted">Select a project to view Codex handoffs.</p>;
  }

  return (
    <section>
      <div className="section-heading">
        <h2>Handoffs</h2>
        <p>{selectedProject}</p>
      </div>

      <div className="summary-grid">
        <SummaryCard title="Handoffs" value={handoffs.loading ? 'Loading' : handoffs.data?.count ?? 0} />
        <SummaryCard title="Latest handoff" value={latestHandoff?.handoff_id ?? 'none'} />
        <SummaryCard title="Latest type" value={latestHandoff?.handoff_type ?? 'none'} />
        <SummaryCard title="Latest status" value={latestHandoff ? <StatusBadge status={latestHandoff.status} /> : 'none'} />
        <SummaryCard title="Worker runs" value={workerRuns.loading ? 'Loading' : workerRuns.data?.count ?? 0} />
        <SummaryCard title="Latest worker" value={latestWorkerRun?.worker_run_id ?? 'none'} />
        <SummaryCard title="Worker status" value={latestWorkerRun ? <StatusBadge status={latestWorkerRun.status} /> : 'none'} />
      </div>

      {handoffs.loading ? <LoadingState message="Loading handoffs..." /> : null}
      {handoffs.error ? <ErrorState message={handoffs.error} /> : null}
      {workerRuns.error ? <ErrorState message={workerRuns.error} /> : null}
      {!handoffs.loading && !handoffs.error && !handoffList.length ? (
        <EmptyState message="No handoff artifacts are available yet.">
          <CommandCopyBox command={`devo project handoff-next --project ${selectedProject} --queue <queueId>`} />
          <CommandCopyBox command={`devo project handoff-task --project ${selectedProject} --task <taskId>`} />
          <CommandCopyBox command={`devo project handoff-batch --project ${selectedProject} --batch <batchId>`} />
        </EmptyState>
      ) : null}

      {handoffList.length ? (
        <>
          <div className="two-column">
            <section className="panel">
              <h3>Handoff List</h3>
              <div className="list-stack">
                {handoffList.map((handoff) => (
                  <button
                    className={handoff.handoff_id === selectedHandoffId ? 'work-row selected-row' : 'work-row'}
                    key={handoff.handoff_id}
                    type="button"
                    onClick={() => setSelectedHandoffId(handoff.handoff_id)}
                  >
                    <span>
                      {handoff.handoff_id}: {handoff.title}
                    </span>
                    <small>
                      {handoff.handoff_type} | {handoff.status} | task {handoff.source_task_id ?? 'none'}
                    </small>
                    <small>
                      queue {handoff.source_queue_id ?? 'none'} | batch {handoff.source_batch_id ?? 'none'} | item {handoff.source_item_id ?? 'none'}
                    </small>
                    <small>{handoff.prompt_path}</small>
                  </button>
                ))}
              </div>
            </section>

            <section className="panel">
              <h3>Selected Handoff</h3>
              {selectedHandoff.loading ? <LoadingState message="Loading handoff detail..." /> : null}
              {selectedHandoff.error ? <ErrorState message={selectedHandoff.error} /> : null}
              {selected ? <HandoffDetail handoff={selected} /> : <p className="muted compact">Select a handoff to inspect metadata.</p>}
            </section>
          </div>

          <SummaryCard title="CLI Guidance">
            <CommandCopyBox command={`devo project handoff-list --project ${selectedProject}`} />
            <CommandCopyBox command={`devo project handoff-show --project ${selectedProject} --handoff ${selectedHandoffId ?? '<handoffId>'}`} />
            <CommandCopyBox command={`devo project handoff-next --project ${selectedProject} --queue ${selected?.source_queue_id ?? '<queueId>'}`} />
            <CommandCopyBox command={`devo project handoff-task --project ${selectedProject} --task ${selected?.source_task_id ?? '<taskId>'}`} />
            <CommandCopyBox command={`devo project handoff-batch --project ${selectedProject} --batch ${selected?.source_batch_id ?? '<batchId>'}`} />
            <CommandCopyBox command={`devo project handoff-mark-used --project ${selectedProject} --handoff ${selectedHandoffId ?? '<handoffId>'}`} />
          </SummaryCard>
          <SummaryCard title="Worker Run Tracking">
            <p className="muted compact">
              Worker runs are read-only tracking records for manual Codex handoffs. They do not run Codex or prove delivery is complete.
            </p>
            {workerRuns.loading ? <LoadingState message="Loading worker runs..." /> : null}
            {!workerRuns.loading && !workerRunList.length ? <p className="muted compact">No worker runs have been recorded yet.</p> : null}
            {latestWorkerRun ? (
              <KeyValueList
                items={[
                  ['Latest run', latestWorkerRun.worker_run_id],
                  ['Status', latestWorkerRun.status],
                  ['Source handoff', latestWorkerRun.source_handoff_id ?? 'none'],
                  ['Report status', latestWorkerRun.report.report_status],
                  ['Next action', latestWorkerRun.next_action]
                ]}
              />
            ) : null}
            <CommandCopyBox command={`devo worker codex run-create --project ${selectedProject} --handoff ${selectedHandoffId ?? '<handoffId>'}`} />
            <CommandCopyBox command={`devo worker codex run-list --project ${selectedProject}`} />
            <CommandCopyBox command={`devo worker codex run-show --project ${selectedProject} --run ${latestWorkerRun?.worker_run_id ?? '<workerRunId>'}`} />
            <CommandCopyBox command={`devo worker codex run-status --project ${selectedProject} --run ${latestWorkerRun?.worker_run_id ?? '<workerRunId>'} --status waiting_review --note "<note>"`} />
          </SummaryCard>
        </>
      ) : null}
    </section>
  );
}

function HandoffDetail({ handoff }: { handoff: CodexHandoff }) {
  return (
    <div className="task-detail">
      <div className="detail-card-title">
        <strong>
          {handoff.handoff_id}: {handoff.title}
        </strong>
        <StatusBadge status={handoff.status} />
      </div>
      <KeyValueList
        items={[
          ['Type', handoff.handoff_type],
          ['Prompt path', handoff.prompt_path],
          ['Source queue', handoff.source_queue_id ?? 'none'],
          ['Source batch', handoff.source_batch_id ?? 'none'],
          ['Source item', handoff.source_item_id ?? 'none'],
          ['Source task', handoff.source_task_id ?? 'none'],
          ['Created', handoff.created_at ?? 'unknown'],
          ['Updated', handoff.updated_at ?? 'unknown']
        ]}
      />
      <p className="muted compact">
        Prompt contents stay in the generated artifact. This dashboard shows metadata only; use the CLI command above to inspect the full handoff.
      </p>
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
