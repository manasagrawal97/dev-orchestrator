import { useEffect, useMemo, useState } from 'react';
import { devoApi } from '../api/client';
import { CommandCopyBox } from '../components/CommandCopyBox';
import { EmptyState, ErrorState, LoadingState } from '../components/SectionState';
import { StatusBadge } from '../components/StatusBadge';
import { SummaryCard } from '../components/SummaryCard';
import type {
  DeliveryApproval,
  DeliveryCheck,
  DeliveryCommitResult,
  DeliveryPlan,
  DeliveryPushResult,
  DeliveryReport,
  ProjectOverview
} from '../types/devo';

interface DeliveryPageProps {
  selectedProject: string | null;
}

interface DeliveryState {
  overview: ProjectOverview | null;
  checks: DeliveryCheck[];
  plans: DeliveryPlan[];
  approvals: DeliveryApproval[];
  reports: DeliveryReport[];
  commit: DeliveryCommitResult | null;
  push: DeliveryPushResult | null;
  loading: boolean;
  error: string | null;
}

const emptyState: DeliveryState = {
  overview: null,
  checks: [],
  plans: [],
  approvals: [],
  reports: [],
  commit: null,
  push: null,
  loading: false,
  error: null
};

export function DeliveryPage({ selectedProject }: DeliveryPageProps) {
  const [state, setState] = useState<DeliveryState>(emptyState);

  useEffect(() => {
    if (!selectedProject) {
      setState(emptyState);
      return;
    }

    const projectName = selectedProject;
    let active = true;
    setState({ ...emptyState, loading: true });

    async function loadDelivery() {
      const [overview, checks, plans, approvals, reports] = await Promise.all([
        devoApi.getProjectOverview(projectName),
        devoApi.getProjectDeliveryChecks(projectName),
        devoApi.getProjectDeliveryPlans(projectName),
        devoApi.getProjectDeliveryApprovals(projectName),
        devoApi.getProjectDeliveryReports(projectName)
      ]);
      const latestReport = reports.delivery_reports[0] ?? null;
      const [commit, push] = latestReport
        ? await Promise.all([
            loadOptional(() => devoApi.getProjectDeliveryCommit(projectName, latestReport.delivery_id)),
            loadOptional(() => devoApi.getProjectDeliveryPush(projectName, latestReport.delivery_id))
          ])
        : [null, null];

      if (active) {
        setState({
          overview,
          checks: checks.delivery_checks,
          plans: plans.delivery_plans,
          approvals: approvals.delivery_approvals,
          reports: reports.delivery_reports,
          commit,
          push,
          loading: false,
          error: null
        });
      }
    }

    loadDelivery().catch((err: Error) => {
      if (active) {
        setState({ ...emptyState, loading: false, error: err.message });
      }
    });

    return () => {
      active = false;
    };
  }, [selectedProject]);

  const latestCheck = state.checks[0] ?? null;
  const latestPlan = state.plans[0] ?? null;
  const latestApproval = state.approvals[0] ?? null;
  const latestReport = state.reports[0] ?? null;
  const blockers = latestCheck?.blockers ?? [];
  const warnings = latestCheck?.warnings ?? [];
  const nextAction = latestReport?.next_action ?? latestPlan?.next_action ?? latestCheck?.next_action ?? state.overview?.delivery_next_action;

  const commands = useMemo(() => {
    if (!selectedProject) {
      return [];
    }
    const deliveryId = latestCheck?.delivery_id ?? latestPlan?.delivery_id ?? latestReport?.delivery_id ?? '<deliveryId>';
    const planId = latestPlan?.delivery_id ?? deliveryId;
    const reportId = latestReport?.delivery_id ?? deliveryId;
    return [
      `devo delivery check --project ${selectedProject} --write`,
      `devo delivery plan --project ${selectedProject} --delivery ${deliveryId} --message "<message>"`,
      `devo delivery approval-request --project ${selectedProject} --plan ${planId} --note "<note>"`,
      `devo delivery approve --project ${selectedProject} --plan ${planId} --approver "<name>" --note "<note>"`,
      `devo delivery report-prepare --project ${selectedProject} --plan ${planId}`,
      `devo delivery commit-preview --project ${selectedProject} --report ${reportId}`,
      `devo delivery commit --project ${selectedProject} --report ${reportId} --confirm-commit`,
      `devo delivery push-preview --project ${selectedProject} --report ${reportId}`,
      `devo delivery push --project ${selectedProject} --report ${reportId} --confirm-push`,
      `devo delivery push-show --project ${selectedProject} --delivery ${reportId}`
    ];
  }, [latestCheck, latestPlan, latestReport, selectedProject]);

  if (!selectedProject) {
    return <p className="muted">Select a project to view delivery state.</p>;
  }

  if (state.loading) {
    return <LoadingState message="Loading delivery artifacts..." />;
  }

  if (state.error) {
    return <ErrorState message={state.error} />;
  }

  if (!latestCheck && !latestPlan && !latestReport) {
    return (
      <section>
        <div className="section-heading">
          <h2>Delivery</h2>
          <p>{selectedProject}</p>
        </div>
        <EmptyState message="No delivery artifacts exist yet. Run a delivery check from the CLI when a reviewed change is ready.">
          <CommandCopyBox command={`devo delivery check --project ${selectedProject} --write`} />
        </EmptyState>
      </section>
    );
  }

  return (
    <section>
      <div className="section-heading">
        <h2>Delivery</h2>
        <p>{selectedProject}</p>
      </div>

      <section className="readonly-banner">
        <strong>Read-only delivery visibility.</strong>
        <span>Commit and push remain CLI-only with explicit confirmation flags. This page only shows state and copyable commands.</span>
      </section>

      <div className="summary-grid">
        <SummaryCard title="Latest check" value={latestCheck ? <StatusBadge status={latestCheck.readiness_status} /> : 'none'} />
        <SummaryCard title="Latest plan" value={latestPlan ? <StatusBadge status={latestPlan.delivery_status} /> : 'none'} />
        <SummaryCard title="Approval" value={latestApproval ? <StatusBadge status={latestApproval.approval_status} /> : 'none'} />
        <SummaryCard title="Report" value={latestReport ? <StatusBadge status={latestReport.final_status} /> : 'none'} />
        <SummaryCard title="Commit" value={state.commit ? <StatusBadge status={state.commit.status} /> : state.overview?.latest_delivery_commit_status ?? 'none'} />
        <SummaryCard title="Push" value={state.push ? <StatusBadge status={state.push.push_status} /> : state.overview?.latest_delivery_push_status ?? 'none'} />
      </div>

      <div className="dashboard-grid">
        <SummaryCard title="Latest delivery summary">
          <dl className="key-value-list">
            <div>
              <dt>Delivery id</dt>
              <dd>{latestReport?.delivery_id ?? latestCheck?.delivery_id ?? 'none'}</dd>
            </div>
            <div>
              <dt>Changed / staged / unstaged / untracked</dt>
              <dd>{countsLabel(latestReport ?? latestCheck)}</dd>
            </div>
            <div>
              <dt>Commit message</dt>
              <dd>{latestReport?.proposed_commit_message ?? latestPlan?.intended_commit_message ?? 'none'}</dd>
            </div>
            <div>
              <dt>Commit hash</dt>
              <dd>{state.commit?.commit_hash ?? latestReport?.commit_hash ?? 'none'}</dd>
            </div>
            <div>
              <dt>Push target</dt>
              <dd>{state.push ? `${state.push.push_remote ?? 'unknown'} ${state.push.push_branch ?? 'unknown'}` : `${latestReport?.push_remote ?? 'unknown'} ${latestReport?.push_branch ?? 'unknown'}`}</dd>
            </div>
            <div>
              <dt>Next action</dt>
              <dd>{nextAction ?? 'Review delivery artifacts.'}</dd>
            </div>
          </dl>
        </SummaryCard>

        <SummaryCard title="Readiness snapshot">
          <p className="muted compact">
            Delivery reports preserve readiness at report preparation time. After commit or push, treat that data as historical and run a new delivery check for current repo state.
          </p>
          <dl className="key-value-list">
            <div>
              <dt>Status</dt>
              <dd>{latestReport?.readiness_snapshot_status ?? latestReport?.final_status ?? latestCheck?.readiness_status ?? 'none'}</dd>
            </div>
            <div>
              <dt>Currentness</dt>
              <dd>{latestReport?.readiness_currentness ?? 'current'}</dd>
            </div>
            <div>
              <dt>Captured at</dt>
              <dd>{latestReport?.readiness_snapshot_at ?? latestCheck?.updated_at ?? 'unknown'}</dd>
            </div>
            <div>
              <dt>Note</dt>
              <dd>{latestReport?.readiness_snapshot_note ?? 'Readiness check is current for the check artifact only.'}</dd>
            </div>
          </dl>
        </SummaryCard>

        <SummaryCard title="Blockers and warnings">
          <h3>Blockers</h3>
          <SimpleList items={blockers.length ? blockers : latestReport?.blocker_summary && latestReport.blocker_summary !== 'none' ? [latestReport.blocker_summary] : []} />
          <h3>Warnings</h3>
          <SimpleList items={warnings.length ? warnings : latestReport?.warning_summary && latestReport.warning_summary !== 'none' ? [latestReport.warning_summary] : []} />
          <p className="muted compact">Unreadable global Git ignore warnings are non-blocking when Git status and diff checks otherwise pass.</p>
        </SummaryCard>

        <SummaryCard title="Copyable CLI commands">
          {commands.map((command) => (
            <CommandCopyBox command={command} key={command} />
          ))}
        </SummaryCard>
      </div>

      <div className="two-column">
        <ArtifactList title="Delivery Checks" items={state.checks} statusOf={(item) => item.readiness_status} />
        <ArtifactList title="Delivery Plans" items={state.plans} statusOf={(item) => item.delivery_status} />
        <ArtifactList title="Delivery Approvals" items={state.approvals} statusOf={(item) => item.approval_status} />
        <ArtifactList title="Delivery Reports" items={state.reports} statusOf={(item) => item.final_status} />
        <section className="panel">
          <h3>Commit Results</h3>
          {state.commit ? (
            <p>
              <StatusBadge status={state.commit.status} /> {state.commit.commit_hash ?? 'no commit hash'}
            </p>
          ) : (
            <p className="muted compact">No commit result artifact for the latest report.</p>
          )}
        </section>
        <section className="panel">
          <h3>Push Results</h3>
          {state.push ? (
            <p>
              <StatusBadge status={state.push.push_status} /> {state.push.push_remote ?? 'unknown'} {state.push.push_branch ?? 'unknown'}
            </p>
          ) : (
            <p className="muted compact">No push result artifact for the latest report.</p>
          )}
        </section>
      </div>
    </section>
  );
}

async function loadOptional<T>(loader: () => Promise<T>): Promise<T | null> {
  try {
    return await loader();
  } catch {
    return null;
  }
}

function countsLabel(item: DeliveryReport | DeliveryCheck | null): string {
  if (!item) {
    return 'none';
  }
  return `${item.changed_files.length} / ${item.staged_files.length} / ${item.unstaged_files.length} / ${item.untracked_files.length}`;
}

function SimpleList({ items }: { items: string[] }) {
  if (!items.length) {
    return <p className="muted compact">none</p>;
  }
  return (
    <ul className="compact-list">
      {items.map((item) => (
        <li key={item}>{item}</li>
      ))}
    </ul>
  );
}

function ArtifactList<T extends { delivery_id: string; updated_at?: string }>({
  title,
  items,
  statusOf
}: {
  title: string;
  items: T[];
  statusOf: (item: T) => string;
}) {
  return (
    <section className="panel">
      <h3>{title}</h3>
      {items.length ? (
        <div className="list-stack">
          {items.map((item) => (
            <div className="work-row static-row" key={`${title}-${item.delivery_id}`}>
              <span>{item.delivery_id}</span>
              <StatusBadge status={statusOf(item)} />
              <small>{item.updated_at ?? 'unknown time'}</small>
            </div>
          ))}
        </div>
      ) : (
        <p className="muted compact">No artifacts.</p>
      )}
    </section>
  );
}
