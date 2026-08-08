import { useEffect, useMemo, useState } from 'react';
import { devoApi } from '../api/client';
import { CommandCopyBox } from '../components/CommandCopyBox';
import { KeyValueList } from '../components/KeyValueList';
import { EmptyState, ErrorState, LoadingState } from '../components/SectionState';
import { StatusBadge } from '../components/StatusBadge';
import { SummaryCard } from '../components/SummaryCard';
import type {
  CodexHandoff,
  CodexRunPlan,
  CodexRunPlansResponse,
  CodexWorkerReport,
  ExecutionQueue,
  ProjectHandoffsResponse,
  ProjectProgress,
  ProjectQueuesResponse,
  WorkerReview,
  WorkerReviewsResponse,
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
  const [workerReviews, setWorkerReviews] = useState<OptionalState<WorkerReviewsResponse>>(emptyOptional);
  const [runPlans, setRunPlans] = useState<OptionalState<CodexRunPlansResponse>>(emptyOptional);
  const [handoffs, setHandoffs] = useState<OptionalState<ProjectHandoffsResponse>>(emptyOptional);
  const [queues, setQueues] = useState<OptionalState<ProjectQueuesResponse>>(emptyOptional);
  const [progress, setProgress] = useState<OptionalState<ProjectProgress>>(emptyOptional);
  const [selectedWorkerRunId, setSelectedWorkerRunId] = useState<string | null>(null);
  const [selectedWorkerRun, setSelectedWorkerRun] = useState<OptionalState<WorkerRun>>(emptyOptional);
  const [selectedReport, setSelectedReport] = useState<OptionalState<CodexWorkerReport>>(emptyOptional);
  const [selectedReview, setSelectedReview] = useState<OptionalState<WorkerReview>>(emptyOptional);

  useEffect(() => {
    if (!selectedProject) {
      setWorkerRuns(emptyOptional<WorkerRunsResponse>());
      setWorkerReports(emptyOptional<WorkerReportsResponse>());
      setWorkerReviews(emptyOptional<WorkerReviewsResponse>());
      setRunPlans(emptyOptional<CodexRunPlansResponse>());
      setHandoffs(emptyOptional<ProjectHandoffsResponse>());
      setQueues(emptyOptional<ProjectQueuesResponse>());
      setProgress(emptyOptional<ProjectProgress>());
      setSelectedWorkerRunId(null);
      setSelectedWorkerRun(emptyOptional<WorkerRun>());
      setSelectedReport(emptyOptional<CodexWorkerReport>());
      setSelectedReview(emptyOptional<WorkerReview>());
      return;
    }

    let active = true;
    setWorkerRuns({ data: null, loading: true, error: null });
    setWorkerReports({ data: null, loading: true, error: null });
    setWorkerReviews({ data: null, loading: true, error: null });
    setRunPlans({ data: null, loading: true, error: null });
    setHandoffs({ data: null, loading: true, error: null });
    setQueues({ data: null, loading: true, error: null });
    setProgress({ data: null, loading: true, error: null });
    setSelectedWorkerRun(emptyOptional<WorkerRun>());
    setSelectedReport(emptyOptional<CodexWorkerReport>());
    setSelectedReview(emptyOptional<WorkerReview>());

    loadOptional(devoApi.getProjectWorkerRuns(selectedProject)).then((state) => {
      if (!active) {
        return;
      }
      setWorkerRuns(state);
      setSelectedWorkerRunId((current) => current ?? state.data?.worker_runs[0]?.worker_run_id ?? null);
    });
    loadOptional(devoApi.getProjectWorkerReports(selectedProject)).then((state) => active && setWorkerReports(state));
    loadOptional(devoApi.getProjectWorkerReviews(selectedProject)).then((state) => active && setWorkerReviews(state));
    loadOptional(devoApi.getProjectWorkerRunPlans(selectedProject)).then((state) => active && setRunPlans(state));
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
      setSelectedReview(emptyOptional<WorkerReview>());
      return;
    }

    let active = true;
    setSelectedWorkerRun({ data: null, loading: true, error: null });
    setSelectedReport({ data: null, loading: true, error: null });
    setSelectedReview({ data: null, loading: true, error: null });

    loadOptional(devoApi.getProjectWorkerRun(selectedProject, selectedWorkerRunId)).then((state) => active && setSelectedWorkerRun(state));
    loadOptional(devoApi.getProjectWorkerReport(selectedProject, selectedWorkerRunId)).then((state) => active && setSelectedReport(state));
    loadOptional(devoApi.getProjectWorkerReview(selectedProject, selectedWorkerRunId)).then((state) => active && setSelectedReview(state));

    return () => {
      active = false;
    };
  }, [selectedProject, selectedWorkerRunId]);

  const workerRunList = workerRuns.data?.worker_runs ?? [];
  const reportList = workerReports.data?.reports ?? [];
  const reviewList = workerReviews.data?.reviews ?? [];
  const runPlanList = runPlans.data?.run_plans ?? [];
  const latestWorkerRun = workerRunList[0] ?? null;
  const latestReport = reportList[0] ?? null;
  const latestReview = reviewList[0] ?? null;
  const latestRunPlan = runPlanList[0] ?? null;
  const selected = selectedWorkerRun.data ?? workerRunList.find((run) => run.worker_run_id === selectedWorkerRunId) ?? null;
  const report = selectedReport.data ?? reportList.find((item) => item.worker_run_id === selectedWorkerRunId) ?? null;
  const review = selectedReview.data ?? reviewList.find((item) => item.worker_run_id === selectedWorkerRunId) ?? null;
  const reportByRun = useMemo(() => new Map(reportList.map((item) => [item.worker_run_id, item])), [reportList]);
  const reviewByRun = useMemo(() => new Map(reviewList.map((item) => [item.worker_run_id, item])), [reviewList]);
  const plansByRun = useMemo(() => new Map(runPlanList.map((item) => [item.worker_run_id, item])), [runPlanList]);
  const selectedRunPlan = selected ? plansByRun.get(selected.worker_run_id) ?? null : null;
  const selectedHandoff = handoffs.data?.handoffs.find((handoff) => handoff.handoff_id === selected?.source_handoff_id) ?? null;
  const selectedQueue = queues.data?.queues.find((queue) => queue.queue_id === selected?.source_queue_id) ?? null;
  const selectedCompletionReady = review?.review_status === 'reviewed_passed' && review.validation_evidence.validation_status !== 'failed';

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
        <SummaryCard title="Reviews" value={workerReviews.loading ? 'Loading' : workerReviews.data?.count ?? 0} />
        <SummaryCard title="Latest review" value={latestReview ? <StatusBadge status={latestReview.review_status} /> : 'none'} />
        <SummaryCard title="Latest validation" value={latestReview ? <StatusBadge status={latestReview.validation_evidence.validation_status} /> : 'none'} />
        <SummaryCard title="Run plans" value={runPlans.loading ? 'Loading' : runPlans.data?.count ?? 0} />
        <SummaryCard title="Latest preflight" value={latestRunPlan ? <StatusBadge status={latestRunPlan.preflight_status} /> : 'none'} />
        <SummaryCard title="Latest next action" value={latestWorkerRun?.next_action ?? 'none'} />
      </div>

      {workerRuns.loading ? <LoadingState message="Loading worker runs..." /> : null}
      {workerRuns.error ? <ErrorState message={workerRuns.error} /> : null}
      {workerReports.error ? <ErrorState message={workerReports.error} /> : null}
      {workerReviews.error ? <ErrorState message={workerReviews.error} /> : null}
      {runPlans.error ? <ErrorState message={runPlans.error} /> : null}
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
                  const runReview = reviewByRun.get(workerRun.worker_run_id);
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
                      <small>
                        review {runReview?.review_status ?? 'none'} | validation {runReview?.validation_evidence.validation_status ?? 'none'}
                      </small>
                      <small>
                        run plan {plansByRun.get(workerRun.worker_run_id)?.plan_id ?? 'none'} | preflight{' '}
                        {plansByRun.get(workerRun.worker_run_id)?.preflight_status ?? 'none'}
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
              <h3>Run Plan Preview</h3>
              {runPlans.loading ? <LoadingState message="Loading run plans..." /> : null}
              {!runPlans.loading && !selectedRunPlan ? (
                <EmptyState message="No run plan exists for the selected worker run yet.">
                  <CommandCopyBox command={`devo worker codex preflight --project ${selectedProject} --run ${selectedWorkerRunId ?? '<workerRunId>'}`} />
                  <CommandCopyBox command={`devo worker codex run-plan --project ${selectedProject} --run ${selectedWorkerRunId ?? '<workerRunId>'}`} />
                </EmptyState>
              ) : null}
              {selectedRunPlan ? <RunPlanDetail plan={selectedRunPlan} /> : null}
            </section>
          </div>

          <section className="panel">
            <h3>Review Evidence</h3>
            {selectedReview.loading ? <LoadingState message="Loading worker review..." /> : null}
            {selectedReview.error ? <ErrorState message={selectedReview.error} /> : null}
            {!selectedReview.loading && !selectedReview.error && !review ? (
              <EmptyState message="No worker review exists for the selected run yet.">
                <CommandCopyBox command={`devo worker codex review-template --project ${selectedProject} --run ${selectedWorkerRunId ?? '<workerRunId>'}`} />
              </EmptyState>
            ) : null}
            {review ? <WorkerReviewDetail review={review} /> : null}
          </section>

          <div className="two-column">
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
              <CommandCopyBox command={`devo worker codex review-template --project ${selectedProject} --run ${selectedWorkerRunId ?? '<workerRunId>'}`} />
              <CommandCopyBox
                command={`devo worker codex review-attach-evidence --project ${selectedProject} --run ${selectedWorkerRunId ?? '<workerRunId>'} --status provided --summary "<validation summary>"`}
              />
              <CommandCopyBox
                command={`devo worker codex review-record --project ${selectedProject} --run ${selectedWorkerRunId ?? '<workerRunId>'} --status reviewed_passed --reviewer "<name>" --note "<note>"`}
              />
              <CommandCopyBox command={`devo worker codex review-show --project ${selectedProject} --run ${selectedWorkerRunId ?? '<workerRunId>'}`} />
              <CommandCopyBox command={`devo worker codex review-list --project ${selectedProject}`} />
              <CommandCopyBox command={`devo worker codex preflight --project ${selectedProject} --run ${selectedWorkerRunId ?? '<workerRunId>'}`} />
              <CommandCopyBox command={`devo worker codex run-plan --project ${selectedProject} --run ${selectedWorkerRunId ?? '<workerRunId>'}`} />
              <CommandCopyBox command={`devo worker codex run-plan-list --project ${selectedProject}`} />
              <CommandCopyBox command={`devo worker codex run-plan-show --project ${selectedProject} --plan ${selectedRunPlan?.plan_id ?? '<planId>'}`} />
              <CommandCopyBox
                command={`devo worker codex execute-preview --project ${selectedProject} --run ${selectedWorkerRunId ?? '<workerRunId>'} --plan ${selectedRunPlan?.plan_id ?? '<planId>'}`}
              />
              <CommandCopyBox
                command={`devo worker codex execute --project ${selectedProject} --run ${selectedWorkerRunId ?? '<workerRunId>'} --plan ${selectedRunPlan?.plan_id ?? '<planId>'} --confirm-execute`}
              />
              <CommandCopyBox command={`devo worker codex execute-log --project ${selectedProject} --run ${selectedWorkerRunId ?? '<workerRunId>'}`} />
              {selected?.source_queue_id ? (
                <>
                  <CommandCopyBox command={`devo worker codex queue-status --project ${selectedProject} --queue ${selected.source_queue_id}`} />
                  <CommandCopyBox command={`devo worker codex prepare-next --project ${selectedProject} --queue ${selected.source_queue_id}`} />
                  <CommandCopyBox command={`devo project queue-next --project ${selectedProject} --queue ${selected.source_queue_id}`} />
                  {selectedCompletionReady ? (
                    <CommandCopyBox
                      command={`devo project queue-complete-item --project ${selectedProject} --queue ${selected.source_queue_id} --item ${
                        selected.source_queue_item_id ?? '<itemId>'
                      } --note "<reviewed result>"`}
                    />
                  ) : (
                    <CommandCopyBox
                      command={`devo worker codex review-record --project ${selectedProject} --run ${
                        selected.worker_run_id
                      } --status reviewed_passed --reviewer "<name>" --note "<note>"`}
                    />
                  )}
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
          ['Execution exit code', workerRun.execution_exit_code ?? 'none'],
          ['Execution command', workerRun.execution_command_label ?? 'none'],
          ['Execution started by', workerRun.execution_started_by ?? 'none'],
          ['Execution log path', workerRun.execution_log_path ?? 'none'],
          ['Execution stderr path', workerRun.execution_stderr_log_path ?? 'none'],
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

function WorkerReviewDetail({ review }: { review: WorkerReview }) {
  return (
    <div className="task-detail">
      <div className="detail-card-title">
        <strong>{review.review_id}</strong>
        <StatusBadge status={review.review_status} />
      </div>
      <KeyValueList
        items={[
          ['Worker run', review.worker_run_id],
          ['Reviewer', review.reviewer ?? 'none'],
          ['Validation status', review.validation_evidence.validation_status],
          ['Validation summary', review.validation_evidence.validation_summary || 'none'],
          ['Decision note', review.decision_note || 'none'],
          ['Source report', review.source_report_path ?? 'none'],
          ['Next action', review.next_action]
        ]}
      />
      <DetailList title="Commands Reported" values={review.validation_evidence.commands_reported} />
      <DetailList title="Tests Reported" values={review.validation_evidence.tests_reported} />
      <DetailList title="Evidence Paths" values={review.validation_evidence.evidence_paths} />
      <DetailList title="Validation Warnings" values={review.validation_evidence.warnings} />
      <DetailList title="Acceptance Criteria Review" values={review.acceptance_criteria_review} />
      <DetailList title="Changed Files Review" values={review.changed_files_review} />
      <DetailList title="Safety Review" values={review.safety_review} />
      <DetailList title="Follow-Up Items" values={review.follow_up_items} />
      <p className="muted compact">
        Review evidence is not completion. The dashboard does not record reviews or complete queue items.
      </p>
    </div>
  );
}

function RunPlanDetail({ plan }: { plan: CodexRunPlan }) {
  return (
    <div className="task-detail">
      <div className="detail-card-title">
        <strong>{plan.plan_id}</strong>
        <StatusBadge status={plan.status} />
      </div>
      <KeyValueList
        items={[
          ['Worker run', plan.worker_run_id],
          ['Handoff', plan.handoff_id || 'none'],
          ['Queue', plan.queue_id ?? 'none'],
          ['Queue item', plan.queue_item_id ?? 'none'],
          ['Task', plan.task_id ?? 'none'],
          ['Approval required', plan.approval_required ? 'yes' : 'no'],
          ['Approval status', plan.approval_status],
          ['Approval note', plan.approval_note ?? 'none'],
          ['Preflight status', plan.preflight_status],
          ['Working directory', plan.proposed_working_directory],
          ['Command label', plan.proposed_command_label],
          ['Command preview', plan.proposed_command_preview],
          ['Next action', plan.next_action]
        ]}
      />
      <div className="detail-list">
        <strong>Preflight checks</strong>
        {plan.preflight_checks.length ? (
          <ul className="plain-list">
            {plan.preflight_checks.map((check) => (
              <li key={check.name}>
                {check.status} {check.name}: {check.detail}
              </li>
            ))}
          </ul>
        ) : (
          <p className="muted compact">No preflight checks recorded.</p>
        )}
      </div>
      <DetailList title="Blocked reasons" values={plan.blocked_reasons} />
      <DetailList title="Warnings" values={plan.warnings} />
      <DetailList title="Allowed scope" values={plan.allowed_scope} />
      <DetailList title="Forbidden scope" values={plan.forbidden_scope} />
      <DetailList title="Validation expectations" values={plan.validation_expectations} />
      <DetailList title="Safety boundaries" values={plan.safety_boundaries} />
      <p className="muted compact">
        This run plan is a safe preview only. The dashboard does not run Codex or execute the preview command.
      </p>
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
