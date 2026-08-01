import { useEffect, useMemo, useState } from 'react';
import { devoApi } from '../api/client';
import { CommandCopyBox } from '../components/CommandCopyBox';
import { KeyValueList } from '../components/KeyValueList';
import { EmptyState, ErrorState, LoadingState } from '../components/SectionState';
import { StatusBadge } from '../components/StatusBadge';
import { SummaryCard } from '../components/SummaryCard';
import type {
  CodexHandoff,
  CodexWorkerReport,
  ExecutionQueue,
  ProjectHandoffsResponse,
  ProjectProgress,
  ProjectQueuesResponse,
  WorkerRun,
  WorkerReportsResponse,
  WorkerRunsResponse
} from '../types/devo';

interface WorkerRunsPageProps {
  selectedProject: string | null;
}

interface OptionalState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
}

const emptyOptional = <T,>(): OptionalState<T> => ({ data: null, loading: false, error: null });

export function WorkerRunsPage({ selectedProject }: WorkerRunsPageProps) {
  const [workerRuns, setWorkerRuns] = useState<OptionalState<WorkerRunsResponse>>(emptyOptional);
  const [workerReports, setWorkerReports] = useState<OptionalState<WorkerReportsResponse>>(emptyOptional);
  const [handoffs, setHandoffs] = useState<OptionalState<ProjectHandoffsResponse>>(emptyOptional);
  const [queues, setQueues] = useState<OptionalState<ProjectQueuesResponse>>(emptyOptional);
  const [progress, setProgress] = useState<OptionalState<ProjectProgress>>(emptyOptional);
  const [selectedWorkerRunId, setSelectedWorkerRunId] = useState<string | null>(null);
  const [selectedWorkerRun, setSelectedWorkerRun] = useState<OptionalState<WorkerRun>>(emptyOptional);
  const [selectedReport, setSelectedReport] = useState<OptionalState<CodexWorkerReport>>(emptyOptional);

  useEffect(() => {
    if (!selectedProject) {
      setWorkerRuns(emptyOptional<WorkerRunsResponse>());
      setWorkerReports(emptyOptional<WorkerReportsResponse>());
      setHandoffs(emptyOptional<ProjectHandoffsResponse>());
      setQueues(emptyOptional<ProjectQueuesResponse>());
      setProgress(emptyOptional<ProjectProgress>());
      setSelectedWorkerRunId(null);
      setSelectedWorkerRun(emptyOptional<WorkerRun>());
      setSelectedReport(emptyOptional<CodexWorkerReport>());
      return;
    }

    let active = true;
    setWorkerRuns({ data: null, loading: true, error: null });
    setWorkerReports({ data: null, loading: true, error: null });
    setHandoffs({ data: null, loading: true, error: null });
    setQueues({ data: null, loading: true, error: null });
    setProgress({ data: null, loading: true, error: null });
    setSelectedWorkerRun(emptyOptional<WorkerRun>());
    setSelectedReport(emptyOptional<CodexWorkerReport>());

    loadOptional(devoApi.getProjectWorkerRuns(selectedProject)).then((state) => {
      if (!active) {
        return;
      }
      setWorkerRuns(state);
      setSelectedWorkerRunId((current) => current ?? state.data?.worker_runs[0]?.worker_run_id ?? null);
    });
    loadOptional(devoApi.getProjectWorkerReports(selectedProject)).then((state) => active && setWorkerReports(state));
    loadOptional(devoApi.getProjectHandoffs(selectedProject)).then((state) => active && setHandoffs(state));
    loadOptional(devoApi.getProjectQueues(selectedProject)).then((state) => active && setQueues(state));
    loadOptional(devoApi.getProjectProgress(selectedProject)).then((state) => active && setProgress(state));

    return () => {
      active = false;
    };
  }, [selectedProject]);

  useEffect(() => {
    if (!selectedProject || !selectedWorkerRunId) {
      setSelectedWorkerRun(emptyOptional<WorkerRun>());
      setSelectedReport(emptyOptional<CodexWorkerReport>());
      return;
    }

    let active = true;
    setSelectedWorkerRun({ data: null, loading: true, error: null });
    setSelectedReport({ data: null, loading: true, error: null });

    loadOptional(devoApi.getProjectWorkerRun(selectedProject, selectedWorkerRunId)).then((state) => active && setSelectedWorkerRun(state));
    loadOptional(devoApi.getProjectWorkerReport(selectedProject, selectedWorkerRunId)).then((state) => active && setSelectedReport(state));

    return () => {
      active = false;
    };
  }, [selectedProject, selectedWorkerRunId]);

  const workerRunList = workerRuns.data?.worker_runs ?? [];
  const reportList = workerReports.data?.reports ?? [];
  const latestWorkerRun = workerRunList[0] ?? null;
  const latestReport = reportList[0] ?? null;
  const selected = selectedWorkerRun.data ?? workerRunList.find((run) => run.worker_run_id === selectedWorkerRunId) ?? null;
  const report = selectedReport.data ?? reportList.find((item) => item.worker_run_id === selectedWorkerRunId) ?? null;
  const reportByRun = useMemo(() => new Map(reportList.map((item) => [item.worker_run_id, item])), [reportList]);
  const selectedHandoff = handoffs.data?.handoffs.find((handoff) => handoff.handoff_id === selected?.source_handoff_id) ?? null;
  const selectedQueue = queues.data?.queues.find((queue) => queue.queue_id === selected?.source_queue_id) ?? null;

  if (!selectedProject) {
    return <p className="muted">Select a project to view Codex worker runs.</p>;
  }

  return (
    <section>
      <div className="section-heading">
        <h2>Worker Runs</h2>
        <p>{selectedProject}</p>
      </div>

      <SummaryCard title="Read-only assisted handoff visibility">
        <p className="compact">
          Worker runs and imported reports are evidence for review. This page does not run Codex, import reports, execute target commands,
          run validation, commit, push, restore backups, modify schedulers, or complete queue items.
        </p>
      </SummaryCard>

      <div className="summary-grid detail-panel">
        <SummaryCard title="Worker runs" value={workerRuns.loading ? 'Loading' : workerRuns.data?.count ?? 0} />
        <SummaryCard title="Latest worker run" value={latestWorkerRun?.worker_run_id ?? 'none'} />
        <SummaryCard title="Latest worker status" value={latestWorkerRun ? <StatusBadge status={latestWorkerRun.status} /> : 'none'} />
        <SummaryCard title="Imported reports" value={workerReports.loading ? 'Loading' : workerReports.data?.count ?? 0} />
        <SummaryCard title="Latest report status" value={latestReport ? <StatusBadge status={latestReport.status_reported_by_worker} /> : 'none'} />
        <SummaryCard title="Latest next action" value={latestWorkerRun?.next_action ?? 'none'} />
      </div>

      {workerRuns.loading ? <LoadingState message="Loading worker runs..." /> : null}
      {workerRuns.error ? <ErrorState message={workerRuns.error} /> : null}
      {workerReports.error ? <ErrorState message={workerReports.error} /> : null}
      {handoffs.error ? <ErrorState message={handoffs.error} /> : null}
      {queues.error ? <ErrorState message={queues.error} /> : null}
      {progress.error ? <ErrorState message={progress.error} /> : null}

      {!workerRuns.loading && !workerRuns.error && !workerRunList.length ? (
        <EmptyState message="No Codex worker runs are recorded yet.">
          <CommandCopyBox command={`devo project handoff-next --project ${selectedProject} --queue <queueId>`} />
          <CommandCopyBox command={`devo worker codex run-create --project ${selectedProject} --handoff <handoffId>`} />
        </EmptyState>
      ) : null}

      {workerRunList.length ? (
        <>
          <div className="two-column">
            <section className="panel">
              <h3>Worker Run List</h3>
              <div className="list-stack">
                {workerRunList.map((workerRun) => {
                  const runReport = reportByRun.get(workerRun.worker_run_id);
                  return (
                    <button
                      className={workerRun.worker_run_id === selectedWorkerRunId ? 'work-row selected-row' : 'work-row'}
                      key={workerRun.worker_run_id}
                      type="button"
                      onClick={() => setSelectedWorkerRunId(workerRun.worker_run_id)}
                    >
                      <span>{workerRun.worker_run_id}</span>
                      <small>
                        {workerRun.status} | {workerRun.mode} | handoff {workerRun.source_handoff_id ?? 'none'}
                      </small>
                      <small>
                        queue {workerRun.source_queue_id ?? 'none'} | item {workerRun.source_queue_item_id ?? 'none'} | task{' '}
                        {workerRun.source_task_id ?? 'none'}
                      </small>
                      <small>
                        report {workerRun.report.report_status} | worker said {runReport?.status_reported_by_worker ?? 'none'} | updated{' '}
                        {workerRun.updated_at ?? 'unknown'}
                      </small>
                      <small>{workerRun.next_action}</small>
                    </button>
                  );
                })}
              </div>
            </section>

            <section className="panel">
              <h3>Selected Worker Run</h3>
              {selectedWorkerRun.loading ? <LoadingState message="Loading worker run detail..." /> : null}
              {selectedWorkerRun.error ? <ErrorState message={selectedWorkerRun.error} /> : null}
              {selected ? (
                <WorkerRunDetail workerRun={selected} handoff={selectedHandoff} queue={selectedQueue} />
              ) : (
                <p className="muted compact">Select a worker run to inspect metadata.</p>
              )}
            </section>
          </div>

          <div className="two-column">
            <section className="panel">
              <h3>Imported Report</h3>
              {selectedReport.loading ? <LoadingState message="Loading imported report..." /> : null}
              {selectedReport.error ? <ErrorState message={selectedReport.error} /> : null}
              {!selectedReport.loading && !selectedReport.error && !report ? (
                <EmptyState message="No imported report exists for the selected worker run yet.">
                  <CommandCopyBox command={`devo worker codex report-template --project ${selectedProject} --run ${selectedWorkerRunId ?? '<workerRunId>'}`} />
                </EmptyState>
              ) : null}
              {report ? <WorkerReportDetail report={report} workerRun={selected} /> : null}
            </section>

            <section className="panel">
              <h3>Review Guidance</h3>
              <p className="muted compact">
                Imported reports are not proof of completion. Independently review changed files, validation evidence, and safety warnings before
                updating queue/task state.
              </p>
              <CommandCopyBox command={`devo worker codex run-list --project ${selectedProject}`} />
              <CommandCopyBox command={`devo worker codex run-show --project ${selectedProject} --run ${selectedWorkerRunId ?? '<workerRunId>'}`} />
              <CommandCopyBox
                command={`devo worker codex run-status --project ${selectedProject} --run ${selectedWorkerRunId ?? '<workerRunId>'} --status waiting_review --note "<note>"`}
              />
              <CommandCopyBox command={`devo worker codex report-template --project ${selectedProject} --run ${selectedWorkerRunId ?? '<workerRunId>'}`} />
              <CommandCopyBox
                command={`devo worker codex report-validate --project ${selectedProject} --run ${selectedWorkerRunId ?? '<workerRunId>'} --file <file>`}
              />
              <CommandCopyBox
                command={`devo worker codex report-import --project ${selectedProject} --run ${selectedWorkerRunId ?? '<workerRunId>'} --file <file>`}
              />
              <CommandCopyBox command={`devo worker codex report-show --project ${selectedProject} --run ${selectedWorkerRunId ?? '<workerRunId>'}`} />
              <CommandCopyBox command={`devo worker codex report-list --project ${selectedProject}`} />
              {selected?.source_queue_id ? (
                <>
                  <CommandCopyBox command={`devo project queue-next --project ${selectedProject} --queue ${selected.source_queue_id}`} />
                  <CommandCopyBox
                    command={`devo project queue-complete-item --project ${selectedProject} --queue ${selected.source_queue_id} --item ${
                      selected.source_queue_item_id ?? '<itemId>'
                    } --note "<reviewed result>"`}
                  />
                </>
              ) : null}
            </section>
          </div>
        </>
      ) : null}

      {progress.loading ? <LoadingState message="Loading project progress context..." /> : null}
    </section>
  );
}

function WorkerRunDetail({
  workerRun,
  handoff,
  queue
}: {
  workerRun: WorkerRun;
  handoff: CodexHandoff | null;
  queue: ExecutionQueue | null;
}) {
  return (
    <div className="task-detail">
      <div className="detail-card-title">
        <strong>
          {workerRun.worker_run_id}: {workerRun.title}
        </strong>
        <StatusBadge status={workerRun.status} />
      </div>
      <KeyValueList
        items={[
          ['Worker type', workerRun.worker_type],
          ['Mode', workerRun.mode],
          ['Source handoff', workerRun.source_handoff_id ?? 'none'],
          ['Source queue', workerRun.source_queue_id ?? 'none'],
          ['Source item', workerRun.source_queue_item_id ?? 'none'],
          ['Source task', workerRun.source_task_id ?? 'none'],
          ['Prompt path', workerRun.prompt_path],
          ['Transcript path', workerRun.transcript_path ?? 'none'],
          ['Report path', workerRun.report_path ?? 'none'],
          ['Target repo', workerRun.target_repo_path],
          ['Report status', workerRun.report.report_status],
          ['Reported changed files', workerRun.report.reported_changed_files.length],
          ['Reported validation', workerRun.report.reported_validation.length],
          ['Safety warnings', workerRun.report.safety_warnings.length],
          ['Imported at', workerRun.report.imported_at ?? 'not imported'],
          ['Status note', workerRun.status_note || 'none'],
          ['Next action', workerRun.next_action],
          ['Created', workerRun.created_at ?? 'unknown'],
          ['Updated', workerRun.updated_at ?? 'unknown']
        ]}
      />
      <DetailList title="Allowed scope" values={workerRun.allowed_scope} />
      <DetailList title="Forbidden scope" values={workerRun.forbidden_scope} />
      <DetailList title="Validation expectations" values={workerRun.validation_expectations} />
      <DetailList title="Safety boundaries" values={workerRun.safety_boundaries} />
      {handoff ? <p className="muted compact">Linked handoff: {handoff.handoff_id} is available in the Handoffs page.</p> : null}
      {queue ? <p className="muted compact">Linked queue: {queue.queue_id} currently has status {queue.status}.</p> : null}
    </div>
  );
}

function WorkerReportDetail({ report, workerRun }: { report: CodexWorkerReport; workerRun: WorkerRun | null }) {
  return (
    <div className="task-detail">
      <div className="detail-card-title">
        <strong>Report for {report.worker_run_id}</strong>
        <StatusBadge status={report.status_reported_by_worker} />
      </div>
      <KeyValueList
        items={[
          ['Report status', workerRun?.report.report_status ?? 'imported'],
          ['Worker reported', report.status_reported_by_worker],
          ['Summary', report.summary],
          ['Validation attempted', report.validation_attempted ? 'yes' : 'no'],
          ['Changed files', report.changed_files.length],
          ['Validation results', report.validation_results.length],
          ['Tests run', report.tests_run.length],
          ['Commands run', report.commands_run.length],
          ['Commit hash', report.commit_hash ?? 'none'],
          ['Imported time', workerRun?.report.imported_at ?? 'unknown'],
          ['Reported time', report.reported_at ?? 'unknown']
        ]}
      />
      <DetailList title="Changed files" values={report.changed_files} />
      <DetailList title="Validation results" values={report.validation_results} />
      <DetailList title="Tests run" values={report.tests_run} />
      <DetailList title="Commands run" values={report.commands_run} />
      <DetailList title="Safety warnings" values={[...report.safety_warnings, ...(workerRun?.report.safety_warnings ?? [])]} />
      <DetailList title="Blockers" values={report.blockers} />
      <DetailList title="Follow-up needed" values={report.follow_up_needed} />
      <DetailList title="Notes" values={report.notes} />
    </div>
  );
}

function DetailList({ title, values }: { title: string; values: string[] }) {
  return (
    <div className="detail-list">
      <strong>{title}</strong>
      {values.length ? (
        <ul className="plain-list">
          {values.map((value, index) => (
            <li key={`${title}-${index}`}>{value}</li>
          ))}
        </ul>
      ) : (
        <p className="muted compact">None recorded.</p>
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
