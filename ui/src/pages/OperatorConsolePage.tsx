import { useEffect, useState } from 'react';
import { devoApi } from '../api/client';
import { CommandCopyBox } from '../components/CommandCopyBox';
import { EmptyState, ErrorState, LoadingState } from '../components/SectionState';
import { StatusBadge } from '../components/StatusBadge';
import { SummaryCard } from '../components/SummaryCard';
import type {
  OperatorConsoleAction,
  OperatorConsoleMaterializeResponse,
  OperatorConsoleProjection,
  OperatorConsoleReviewStatus,
  RoughGoalIntakePlan
} from '../types/devo';

interface OperatorConsolePageProps {
  selectedProject: string | null;
}

type PendingAction =
  | 'create_intake'
  | 'materialize'
  | 'approve_materialized_plan'
  | 'prepare'
  | 'approve_plan'
  | 'run_goal'
  | 'review_worker'
  | 'resume_worker'
  | 'retry_worker';

const REVIEW_STATUSES: Array<{ value: OperatorConsoleReviewStatus; label: string }> = [
  { value: 'passed', label: 'Passed' },
  { value: 'needs_changes', label: 'Needs changes' },
  { value: 'rejected', label: 'Rejected' },
  { value: 'blocked', label: 'Blocked' }
];

export function OperatorConsolePage({ selectedProject }: OperatorConsolePageProps) {
  const [consoleData, setConsoleData] = useState<OperatorConsoleProjection | null>(null);
  const [loading, setLoading] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [pendingAction, setPendingAction] = useState<PendingAction | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [actionMessage, setActionMessage] = useState<string | null>(null);

  const [goalMarkdown, setGoalMarkdown] = useState('');
  const [confirmCreate, setConfirmCreate] = useState(false);
  const [intake, setIntake] = useState<RoughGoalIntakePlan | null>(null);
  const [confirmMaterialize, setConfirmMaterialize] = useState(false);
  const [materialized, setMaterialized] = useState<OperatorConsoleMaterializeResponse | null>(null);
  const [planningApproved, setPlanningApproved] = useState(false);
  const [planningApprover, setPlanningApprover] = useState('');
  const [planningNote, setPlanningNote] = useState('');
  const [confirmPlanningApproval, setConfirmPlanningApproval] = useState(false);
  const [reviewedBy, setReviewedBy] = useState('');
  const [confirmDraftReviewed, setConfirmDraftReviewed] = useState(false);
  const [enableSupervisedDelivery, setEnableSupervisedDelivery] = useState(false);
  const [deliveryAuthorizer, setDeliveryAuthorizer] = useState('');
  const [confirmSupervisedDelivery, setConfirmSupervisedDelivery] = useState(false);
  const [confirmPrepare, setConfirmPrepare] = useState(false);

  const [operatorName, setOperatorName] = useState('');
  const [approvalNote, setApprovalNote] = useState('');
  const [confirmAction, setConfirmAction] = useState(false);
  const [runMessage, setRunMessage] = useState('');
  const [runNote, setRunNote] = useState('');
  const [maxSteps, setMaxSteps] = useState(10);
  const [maxWaitSeconds, setMaxWaitSeconds] = useState(30);
  const [reviewStatus, setReviewStatus] = useState<OperatorConsoleReviewStatus>('passed');
  const [reviewSummary, setReviewSummary] = useState('');
  const [reviewNote, setReviewNote] = useState('');
  const [recoveryReason, setRecoveryReason] = useState('');

  useEffect(() => {
    setConsoleData(null);
    setLoadError(null);
    resetIntakeFlow();
    clearActionFeedback();
    if (!selectedProject) {
      setLoading(false);
      return;
    }
    let active = true;
    setLoading(true);
    devoApi
      .getProjectOperatorConsole(selectedProject)
      .then((data) => {
        if (active) {
          setConsoleData(data);
          setLoadError(null);
        }
      })
      .catch((error: unknown) => {
        if (active) {
          setLoadError(friendlyError(error));
        }
      })
      .finally(() => {
        if (active) {
          setLoading(false);
        }
      });
    return () => {
      active = false;
    };
  }, [selectedProject]);

  if (!selectedProject) {
    return <EmptyState message="Select a project to open its operator console." />;
  }

  const goal = consoleData?.active_goal ?? null;
  const supportedAction = consoleData?.supported_actions[0] ?? null;

  async function refreshConsole() {
    if (!selectedProject) return;
    setLoading(true);
    setLoadError(null);
    try {
      setConsoleData(await devoApi.getProjectOperatorConsole(selectedProject));
    } catch (error) {
      setLoadError(friendlyError(error));
    } finally {
      setLoading(false);
    }
  }

  async function createIntake() {
    if (!selectedProject) return;
    await perform('create_intake', async () => {
      const response = await devoApi.createProjectOperatorConsoleIntake(selectedProject, {
        goal_markdown: goalMarkdown.trim(),
        confirm_create: confirmCreate
      });
      setIntake(response.intake);
      setMaterialized(null);
      setPlanningApproved(false);
      setConfirmCreate(false);
      setActionMessage(`Created ${response.intake.intake_id}. Review the draft before materializing it.`);
    });
  }

  async function materializeIntake() {
    if (!selectedProject || !intake) return;
    await perform('materialize', async () => {
      const response = await devoApi.materializeProjectOperatorConsoleIntake(selectedProject, intake.intake_id, {
        confirm_materialize: confirmMaterialize
      });
      setMaterialized(response);
      setConfirmMaterialize(false);
      setActionMessage(`Materialized ${intake.intake_id}. Inspect every task and boundary before approval.`);
    });
  }

  async function approveMaterializedPlan() {
    if (!selectedProject || !intake || !materialized) return;
    await perform('approve_materialized_plan', async () => {
      await devoApi.approveProjectOperatorConsoleMaterializedPlan(selectedProject, intake.intake_id, {
        batch_id: materialized.materialization.batch_id,
        approver: planningApprover.trim(),
        note: planningNote.trim(),
        confirm_approve: confirmPlanningApproval
      });
      setPlanningApproved(true);
      setReviewedBy((current) => current || planningApprover.trim());
      setConfirmPlanningApproval(false);
      setActionMessage('The materialized draft is approved. Preparation remains a separate confirmed step.');
    });
  }

  async function prepareGoal() {
    if (!selectedProject || !intake) return;
    await perform('prepare', async () => {
      const response = await devoApi.prepareProjectOperatorConsoleIntake(selectedProject, intake.intake_id, {
        confirm_prepare: confirmPrepare,
        confirm_materialized_plan_reviewed: confirmDraftReviewed,
        reviewed_by: reviewedBy.trim(),
        enable_supervised_delivery: enableSupervisedDelivery,
        confirm_supervised_delivery: enableSupervisedDelivery && confirmSupervisedDelivery,
        supervised_delivery_authorized_by: enableSupervisedDelivery ? deliveryAuthorizer.trim() : ''
      });
      setConsoleData(response.console);
      resetIntakeFlow();
      setActionMessage(`Prepared ${response.preparation.preparation_id}. The approval bundle is not approved yet.`);
    });
  }

  async function approveGoalPlan() {
    if (!selectedProject || !goal) return;
    await perform('approve_plan', async () => {
      const response = await devoApi.approveProjectOperatorConsoleGoal(selectedProject, goal.intake_id, {
        bundle_id: goal.bundle_id,
        approver: operatorName.trim(),
        note: approvalNote.trim(),
        confirm_approve: confirmAction
      });
      setConsoleData(response.console);
      resetGuardedActionForm();
      setActionMessage(`Approved ${response.bundle.bundle_id}. Starting execution still requires separate confirmation.`);
    });
  }

  async function runGoal() {
    if (!selectedProject || !goal) return;
    await perform('run_goal', async () => {
      const response = await devoApi.runProjectOperatorConsoleGoal(selectedProject, goal.intake_id, {
        bundle_id: goal.bundle_id,
        message: runMessage.trim(),
        note: runNote.trim(),
        max_steps: maxSteps,
        poll_interval_seconds: 1,
        max_wait_seconds: maxWaitSeconds,
        confirm_run: confirmAction
      });
      setConsoleData(response.console);
      resetGuardedActionForm();
      setActionMessage(`Goal supervisor stopped with status ${response.result.status}: ${response.result.next_action}`);
    });
  }

  async function reviewWorker() {
    if (!selectedProject || !goal?.current_queue_worker_run_id) return;
    await perform('review_worker', async () => {
      const response = await devoApi.reviewProjectOperatorConsoleWorker(selectedProject, goal.current_queue_worker_run_id!, {
        bundle_id: goal.bundle_id,
        status: reviewStatus,
        summary: reviewSummary.trim(),
        recorded_by: operatorName.trim(),
        note: reviewNote.trim(),
        confirm_review: confirmAction
      });
      setConsoleData(response.console);
      resetGuardedActionForm();
      setReviewSummary('');
      setReviewNote('');
      setActionMessage(`Recorded ${response.review.evidence_status} review evidence for ${response.review.run_id}.`);
    });
  }

  async function recoverWorker(action: 'resume_worker' | 'retry_worker') {
    if (!selectedProject || !goal?.current_queue_worker_run_id) return;
    await perform(action, async () => {
      const response = await devoApi.recoverProjectOperatorConsoleWorker(selectedProject, goal.current_queue_worker_run_id!, {
        intake_id: goal.intake_id,
        bundle_id: goal.bundle_id,
        action,
        operator: operatorName.trim(),
        reason: recoveryReason.trim(),
        confirm_recovery: confirmAction
      });
      setConsoleData(response.console);
      resetGuardedActionForm();
      setRecoveryReason('');
      setActionMessage(`${action === 'retry_worker' ? 'Retried' : 'Resumed'} worker as ${response.run.run_id}.`);
    });
  }

  async function perform(action: PendingAction, operation: () => Promise<void>) {
    setPendingAction(action);
    setActionError(null);
    setActionMessage(null);
    try {
      await operation();
    } catch (error) {
      setActionError(friendlyError(error));
    } finally {
      consumeConfirmation(action);
      setPendingAction(null);
    }
  }

  function consumeConfirmation(action: PendingAction) {
    if (action === 'create_intake') setConfirmCreate(false);
    if (action === 'materialize') setConfirmMaterialize(false);
    if (action === 'approve_materialized_plan') setConfirmPlanningApproval(false);
    if (action === 'prepare') {
      setConfirmDraftReviewed(false);
      setConfirmSupervisedDelivery(false);
      setConfirmPrepare(false);
    }
    if (['approve_plan', 'run_goal', 'review_worker', 'resume_worker', 'retry_worker'].includes(action)) {
      setConfirmAction(false);
    }
  }

  function resetIntakeFlow() {
    setGoalMarkdown('');
    setConfirmCreate(false);
    setIntake(null);
    setConfirmMaterialize(false);
    setMaterialized(null);
    setPlanningApproved(false);
    setPlanningApprover('');
    setPlanningNote('');
    setConfirmPlanningApproval(false);
    setReviewedBy('');
    setConfirmDraftReviewed(false);
    setEnableSupervisedDelivery(false);
    setDeliveryAuthorizer('');
    setConfirmSupervisedDelivery(false);
    setConfirmPrepare(false);
  }

  function resetGuardedActionForm() {
    setConfirmAction(false);
    setApprovalNote('');
    setRunMessage('');
    setRunNote('');
  }

  function clearActionFeedback() {
    setActionError(null);
    setActionMessage(null);
  }

  const busy = pendingAction !== null;

  return (
    <section className="operator-console">
      <div className="section-heading operator-heading">
        <div className="operator-project-context">
          <span className="operator-kicker">Active project</span>
          <strong>{selectedProject}</strong>
        </div>
        <button className="secondary-action-button" disabled={loading || busy} type="button" onClick={() => void refreshConsole()}>
          {loading ? 'Refreshing...' : 'Refresh state'}
        </button>
      </div>

      {loadError ? <ErrorState message={loadError} /> : null}
      {loading && !consoleData ? <LoadingState message="Loading canonical operator state..." /> : null}
      {actionError ? <p className="error-text operator-feedback" role="alert">{actionError}</p> : null}
      {actionMessage ? <p className="operator-success operator-feedback" role="status">{actionMessage}</p> : null}

      {consoleData ? (
        <>
          <section className="operator-safety-note">
            <strong>Safety boundary</strong>
            <span>{consoleData.safety_note}</span>
          </section>

          {consoleData.attention_required ? (
            <AttentionPanel title="Operator attention required" items={consoleData.attention_items} />
          ) : null}

          {goal ? (
            <>
              <ActiveGoalPanel goal={goal} />
              <LiveEvidencePanel goal={goal} />
            </>
          ) : (
            <EmptyState message="No active prepared goal. Start with a rough goal below; no project artifacts are created until you confirm each step." />
          )}

          {goal && supportedAction ? (
            <GuardedActionPanel action={supportedAction}>
              {supportedAction.action_id === 'approve_plan' ? (
                <>
                  <IdentityField label="Approver" value={operatorName} onChange={setOperatorName} placeholder="Name recorded in approval evidence" />
                  <TextAreaField label="Approval note" value={approvalNote} onChange={setApprovalNote} placeholder="What scope, risk, and validation did you review?" />
                  <Confirmation checked={confirmAction} onChange={setConfirmAction}>
                    I reviewed this bounded plan and authorize this approval bundle once.
                  </Confirmation>
                  <ActionButton busy={pendingAction === 'approve_plan'} disabled={busy || !operatorName.trim() || !confirmAction} label="Approve bounded plan" onClick={approveGoalPlan} />
                </>
              ) : null}

              {['start_goal', 'resume_goal', 'record_validation'].includes(supportedAction.action_id) ? (
                <>
                  <div className="operator-form-grid">
                    <label className="field-label">
                      Maximum supervisor steps
                      <input min={1} max={100} type="number" value={maxSteps} onChange={(event) => setMaxSteps(clampNumber(event.target.value, 1, 100, 10))} />
                    </label>
                    <label className="field-label">
                      Wait limit (seconds)
                      <input min={1} max={600} type="number" value={maxWaitSeconds} onChange={(event) => setMaxWaitSeconds(clampNumber(event.target.value, 1, 600, 30))} />
                    </label>
                  </div>
                  <TextAreaField label="Worker message (optional)" value={runMessage} onChange={setRunMessage} placeholder="Context for the bounded worker" compact />
                  <TextAreaField label="Audit note (optional)" value={runNote} onChange={setRunNote} placeholder="Why this continuation is being run" compact />
                  <Confirmation checked={confirmAction} onChange={setConfirmAction}>
                    I authorize this bounded supervisor continuation. It will not automatically retry failed or ambiguous work.
                  </Confirmation>
                  <ActionButton busy={pendingAction === 'run_goal'} disabled={busy || !confirmAction} label={supportedAction.label} onClick={runGoal} />
                </>
              ) : null}

              {supportedAction.action_id === 'review_worker' ? (
                <>
                  <div className="operator-form-grid">
                    <IdentityField label="Recorded by" value={operatorName} onChange={setOperatorName} placeholder="Reviewer name" />
                    <label className="field-label">
                      Review decision
                      <select value={reviewStatus} onChange={(event) => setReviewStatus(event.target.value as OperatorConsoleReviewStatus)}>
                        {REVIEW_STATUSES.map((status) => <option key={status.value} value={status.value}>{status.label}</option>)}
                      </select>
                    </label>
                  </div>
                  <TextAreaField label="Review summary" value={reviewSummary} onChange={setReviewSummary} placeholder="Describe the evidence you reviewed and why this decision is correct." />
                  <TextAreaField label="Review note (optional)" value={reviewNote} onChange={setReviewNote} placeholder="Additional audit context" compact />
                  <Confirmation checked={confirmAction} onChange={setConfirmAction}>
                    I personally reviewed the bounded worker result and want to record this semantic decision.
                  </Confirmation>
                  <ActionButton busy={pendingAction === 'review_worker'} disabled={busy || !operatorName.trim() || !reviewSummary.trim() || !confirmAction} label="Record semantic review" onClick={reviewWorker} />
                </>
              ) : null}

              {['resume_worker', 'retry_worker'].includes(supportedAction.action_id) ? (
                <>
                  <IdentityField label="Recovery operator" value={operatorName} onChange={setOperatorName} placeholder="Name recorded as recovery authority" />
                  <TextAreaField label="Recovery reason" value={recoveryReason} onChange={setRecoveryReason} placeholder="Explain what changed and why manual recovery is safe." />
                  <Confirmation checked={confirmAction} onChange={setConfirmAction}>
                    I reviewed the current run and authorize this one manual {supportedAction.action_id === 'retry_worker' ? 'retry' : 'resume'}.
                  </Confirmation>
                  <ActionButton
                    busy={pendingAction === supportedAction.action_id}
                    disabled={busy || !operatorName.trim() || !recoveryReason.trim() || !confirmAction}
                    label={supportedAction.label}
                    onClick={() => recoverWorker(supportedAction.action_id as 'resume_worker' | 'retry_worker')}
                    danger={supportedAction.action_id === 'retry_worker'}
                  />
                </>
              ) : null}
            </GuardedActionPanel>
          ) : null}

          {goal && !supportedAction ? (
            <section className="panel quiet-panel">
              <h3>No guarded action is currently available</h3>
              <p className="compact">{goal.next_action}</p>
            </section>
          ) : null}

          {!goal ? (
            <IntakeBuilder
              goalMarkdown={goalMarkdown}
              setGoalMarkdown={setGoalMarkdown}
              confirmCreate={confirmCreate}
              setConfirmCreate={setConfirmCreate}
              intake={intake}
              confirmMaterialize={confirmMaterialize}
              setConfirmMaterialize={setConfirmMaterialize}
              materialized={materialized}
              planningApproved={planningApproved}
              planningApprover={planningApprover}
              setPlanningApprover={setPlanningApprover}
              planningNote={planningNote}
              setPlanningNote={setPlanningNote}
              confirmPlanningApproval={confirmPlanningApproval}
              setConfirmPlanningApproval={setConfirmPlanningApproval}
              reviewedBy={reviewedBy}
              setReviewedBy={setReviewedBy}
              confirmDraftReviewed={confirmDraftReviewed}
              setConfirmDraftReviewed={setConfirmDraftReviewed}
              enableSupervisedDelivery={enableSupervisedDelivery}
              setEnableSupervisedDelivery={setEnableSupervisedDelivery}
              deliveryAuthorizer={deliveryAuthorizer}
              setDeliveryAuthorizer={setDeliveryAuthorizer}
              confirmSupervisedDelivery={confirmSupervisedDelivery}
              setConfirmSupervisedDelivery={setConfirmSupervisedDelivery}
              confirmPrepare={confirmPrepare}
              setConfirmPrepare={setConfirmPrepare}
              pendingAction={pendingAction}
              busy={busy}
              onCreate={createIntake}
              onMaterialize={materializeIntake}
              onApproveMaterializedPlan={approveMaterializedPlan}
              onPrepare={prepareGoal}
            />
          ) : null}

          {consoleData.recent_completion ? (
            <SummaryCard title="Most recent completed goal">
              <div className="operator-completion">
                <strong>{consoleData.recent_completion.goal_summary}</strong>
                <span>{consoleData.recent_completion.intake_id} · {consoleData.recent_completion.bundle_id} · {consoleData.recent_completion.child_count} children</span>
                <small>{formatDate(consoleData.recent_completion.completed_at)}</small>
              </div>
            </SummaryCard>
          ) : null}

          {consoleData.warnings.length ? <AttentionPanel title="Projection warnings" items={consoleData.warnings} quiet /> : null}
        </>
      ) : null}
    </section>
  );
}

interface IntakeBuilderProps {
  goalMarkdown: string;
  setGoalMarkdown: (value: string) => void;
  confirmCreate: boolean;
  setConfirmCreate: (value: boolean) => void;
  intake: RoughGoalIntakePlan | null;
  confirmMaterialize: boolean;
  setConfirmMaterialize: (value: boolean) => void;
  materialized: OperatorConsoleMaterializeResponse | null;
  planningApproved: boolean;
  planningApprover: string;
  setPlanningApprover: (value: string) => void;
  planningNote: string;
  setPlanningNote: (value: string) => void;
  confirmPlanningApproval: boolean;
  setConfirmPlanningApproval: (value: boolean) => void;
  reviewedBy: string;
  setReviewedBy: (value: string) => void;
  confirmDraftReviewed: boolean;
  setConfirmDraftReviewed: (value: boolean) => void;
  enableSupervisedDelivery: boolean;
  setEnableSupervisedDelivery: (value: boolean) => void;
  deliveryAuthorizer: string;
  setDeliveryAuthorizer: (value: string) => void;
  confirmSupervisedDelivery: boolean;
  setConfirmSupervisedDelivery: (value: boolean) => void;
  confirmPrepare: boolean;
  setConfirmPrepare: (value: boolean) => void;
  pendingAction: PendingAction | null;
  busy: boolean;
  onCreate: () => Promise<void>;
  onMaterialize: () => Promise<void>;
  onApproveMaterializedPlan: () => Promise<void>;
  onPrepare: () => Promise<void>;
}

function IntakeBuilder(props: IntakeBuilderProps) {
  return (
    <section className="operator-intake-stack">
      <section className="panel operator-step">
        <StepHeading number={1} title="Describe the goal" status={props.intake ? 'complete' : 'current'} />
        <TextAreaField
          label="Rough goal (Markdown)"
          value={props.goalMarkdown}
          onChange={props.setGoalMarkdown}
          placeholder={'# Goal\n\nDescribe the outcome.\n\n# Scope\n\n- Bound the work.\n\n# Allowed files\n\n- path/to/file\n\n# Validation\n\n- command'}
          rows={12}
          disabled={Boolean(props.intake)}
        />
        {!props.intake ? (
          <>
            <Confirmation checked={props.confirmCreate} onChange={props.setConfirmCreate}>
              Create a draft intake in Devo workspace artifacts for this project.
            </Confirmation>
            <ActionButton busy={props.pendingAction === 'create_intake'} disabled={props.busy || !props.goalMarkdown.trim() || !props.confirmCreate} label="Create draft intake" onClick={props.onCreate} />
          </>
        ) : null}
      </section>

      {props.intake ? (
        <section className="panel operator-step">
          <StepHeading number={2} title="Review the draft" status={props.materialized ? 'complete' : 'current'} />
          <p className="operator-lead">This is still a preview. Confirm that the candidate tasks, allowed files, exclusions, validation, and risks reflect the intended goal.</p>
          <DraftReview intake={props.intake} />
          {!props.materialized ? (
            <>
              <Confirmation checked={props.confirmMaterialize} onChange={props.setConfirmMaterialize}>
                I reviewed this preview and want to materialize its proposed backlog, batch, queue, and source policy.
              </Confirmation>
              <ActionButton busy={props.pendingAction === 'materialize'} disabled={props.busy || !props.confirmMaterialize} label="Materialize reviewed draft" onClick={props.onMaterialize} />
            </>
          ) : null}
        </section>
      ) : null}

      {props.materialized ? (
        <section className="panel operator-step">
          <StepHeading number={3} title="Approve the materialized plan" status={props.planningApproved ? 'complete' : 'current'} />
          <p className="operator-lead">Review the authoritative materialized task details below. Approval is recorded separately from materialization and preparation.</p>
          <MaterializedReview response={props.materialized} />
          {!props.planningApproved ? (
            <>
              <div className="operator-form-grid">
                <IdentityField label="Planning approver" value={props.planningApprover} onChange={props.setPlanningApprover} placeholder="Reviewer name" />
                <TextAreaField label="Approval note" value={props.planningNote} onChange={props.setPlanningNote} placeholder="Record what was checked in the materialized plan." compact />
              </div>
              <Confirmation checked={props.confirmPlanningApproval} onChange={props.setConfirmPlanningApproval}>
                I reviewed the materialized task scopes and authorize this planning batch.
              </Confirmation>
              <ActionButton
                busy={props.pendingAction === 'approve_materialized_plan'}
                disabled={props.busy || !props.planningApprover.trim() || !props.planningNote.trim() || !props.confirmPlanningApproval}
                label="Approve materialized plan"
                onClick={props.onApproveMaterializedPlan}
              />
            </>
          ) : <p className="operator-success compact">Materialized plan approval recorded.</p>}
        </section>
      ) : null}

      {props.materialized && props.planningApproved ? (
        <section className="panel operator-step">
          <StepHeading number={4} title="Prepare bounded execution" status="current" />
          <p className="operator-lead">Preparation creates child policies and a requested approval bundle. It does not approve or run the goal.</p>
          <IdentityField label="Materialized plan reviewed by" value={props.reviewedBy} onChange={props.setReviewedBy} placeholder="Reviewer name" />
          <Confirmation checked={props.confirmDraftReviewed} onChange={props.setConfirmDraftReviewed}>
            I confirm the materialized plan shown above was reviewed by this person.
          </Confirmation>
          <label className="confirm-row operator-option">
            <input checked={props.enableSupervisedDelivery} type="checkbox" onChange={(event) => props.setEnableSupervisedDelivery(event.target.checked)} />
            <span>Enable the existing supervised trusted-delivery workflow for this goal.</span>
          </label>
          {props.enableSupervisedDelivery ? (
            <div className="operator-nested-confirmation">
              <IdentityField label="Delivery authorized by" value={props.deliveryAuthorizer} onChange={props.setDeliveryAuthorizer} placeholder="Delivery authorizer name" />
              <Confirmation checked={props.confirmSupervisedDelivery} onChange={props.setConfirmSupervisedDelivery}>
                I explicitly authorize supervised delivery. Commit and push remain trusted-runner-only and gate-checked.
              </Confirmation>
            </div>
          ) : null}
          <Confirmation checked={props.confirmPrepare} onChange={props.setConfirmPrepare}>
            Prepare one sequential bounded child workflow from the reviewed materialized plan.
          </Confirmation>
          <ActionButton
            busy={props.pendingAction === 'prepare'}
            disabled={props.busy || !props.reviewedBy.trim() || !props.confirmDraftReviewed || !props.confirmPrepare || (props.enableSupervisedDelivery && (!props.deliveryAuthorizer.trim() || !props.confirmSupervisedDelivery))}
            label="Prepare goal for approval"
            onClick={props.onPrepare}
          />
        </section>
      ) : null}
    </section>
  );
}

function ActiveGoalPanel({ goal }: { goal: NonNullable<OperatorConsoleProjection['active_goal']> }) {
  const completion = goal.child_count ? Math.round((goal.completed_child_count / goal.child_count) * 100) : 0;
  return (
    <section className="operator-goal">
      <div className="operator-goal-header">
        <div>
          <span className="operator-kicker">Active prepared goal</span>
          <h3>{goal.goal_summary}</h3>
          <p>{goal.intake_id} · {goal.preparation_id} · {goal.bundle_id}</p>
        </div>
        <StatusBadge status={goal.status} />
      </div>
      <div className="summary-grid operator-summary-grid">
        <SummaryCard title="Current stage" value={humanize(goal.current_stage)} />
        <SummaryCard title="Current child" value={goal.current_task_id ?? 'none'}>
          {goal.current_task_title ? <small>{goal.current_task_title}</small> : null}
        </SummaryCard>
        <SummaryCard title="Bundle" value={<StatusBadge status={goal.bundle_status} />} />
        <SummaryCard title="Worker" value={goal.current_queue_worker_status ? <StatusBadge status={goal.current_queue_worker_status} /> : 'not started'} />
        <SummaryCard title="Review" value={goal.current_review_status ? <StatusBadge status={goal.current_review_status} /> : 'not recorded'} />
        <SummaryCard title="Delivery" value={<StatusBadge status={goal.delivery_state} />} />
      </div>
      <div className="operator-progress" aria-label={`${completion}% of goal children complete`}>
        <div><span>Goal progress</span><strong>{goal.completed_child_count} / {goal.child_count} children</strong></div>
        <div className="progress-meter-track"><span style={{ width: `${completion}%` }} /></div>
      </div>
      <ol className="operator-stage-timeline" aria-label="Execution stage timeline">
        {goal.stage_timeline.map((stage) => (
          <li className={stage.status} key={stage.stage_id}>
            <span className="operator-stage-marker" aria-hidden="true" />
            <div>
              <strong>{stage.label}</strong>
              <small>{stage.detail}</small>
            </div>
            <StatusBadge status={humanize(stage.status)} />
          </li>
        ))}
      </ol>
      <ol className="operator-child-list">
        {goal.children.map((child) => (
          <li className={`${child.is_current ? 'current' : ''} ${child.stage === 'completed' ? 'complete' : ''}`} key={child.task_id}>
            <span className="operator-child-position">{child.position}</span>
            <div>
              <strong>{child.task_id}: {child.title}</strong>
              <small>{child.queue_item_id} · {child.policy_id} · risk {child.risk_level}</small>
            </div>
            <StatusBadge status={humanize(child.stage)} />
          </li>
        ))}
      </ol>
      <section className="operator-next-action">
        <strong>Canonical next action</strong>
        <p>{goal.next_action}</p>
      </section>
      {goal.attention_items.length ? <AttentionPanel title="Goal blockers and attention" items={goal.attention_items} /> : null}
    </section>
  );
}

function LiveEvidencePanel({ goal }: { goal: NonNullable<OperatorConsoleProjection['active_goal']> }) {
  const worker = goal.worker_evidence;
  const review = goal.review_evidence;
  const validation = goal.validation_evidence;
  const delivery = goal.delivery_evidence;

  return (
    <section className="panel operator-evidence-panel">
      <div className="operator-evidence-heading">
        <div>
          <span className="operator-kicker">Canonical live evidence</span>
          <h3>Execution, review, validation, and delivery</h3>
        </div>
        <span className="operator-evidence-refresh-note">Refresh state to load newly recorded evidence.</span>
      </div>

      <div className="operator-evidence-grid">
        <EvidenceCard title="Worker execution" status={worker?.report_status ?? worker?.queue_worker_status ?? 'not started'}>
          {worker ? (
            <>
              <EvidenceFacts items={[
                ['Queue worker run', worker.queue_worker_run_id],
                ['Worker run', worker.worker_run_id ?? 'not assigned'],
                ['Queue status', humanize(worker.queue_worker_status)],
                ['Worker status', worker.worker_status ? humanize(worker.worker_status) : 'not recorded']
              ]} />
              {worker.summary ? <p className="operator-evidence-summary">{worker.summary}</p> : null}
              <div className="operator-evidence-lists">
                <ListBlock label="Work performed" items={worker.work_performed} empty="not reported" />
                <ListBlock label="Changed files" items={worker.changed_files} empty="none reported" />
                <ListBlock label="Commands and tests" items={worker.commands_run} empty="none reported" />
                <ListBlock label="Risks" items={worker.risks} empty="none reported" />
                <ListBlock label="Blockers" items={worker.blockers} empty="none reported" />
              </div>
              {worker.artifact_path || worker.patch_proposal_present ? (
                <EvidenceFacts items={[
                  ['Worker artifact', worker.artifact_path ?? 'not recorded'],
                  ['Patch proposal', worker.patch_proposal_present ? (worker.patch_artifact_path ?? 'included in worker result') : 'none']
                ]} />
              ) : null}
              <DiffPreview preview={worker.diff_preview} note={worker.diff_note} truncated={worker.diff_truncated} />
            </>
          ) : <p className="operator-evidence-empty">No worker evidence is recorded for the current child.</p>}
        </EvidenceCard>

        <EvidenceCard title="Human semantic review" status={review?.status ?? 'not recorded'}>
          {review ? (
            <>
              <EvidenceFacts items={[
                ['Reviewer', review.reviewer ?? 'not recorded'],
                ['Decision', humanize(review.status)]
              ]} />
              {review.decision_note ? <p className="operator-evidence-summary">{review.decision_note}</p> : null}
              <div className="operator-evidence-lists">
                <ListBlock label="Changed files review" items={review.changed_files_review} empty="not recorded" />
                <ListBlock label="Safety review" items={review.safety_review} empty="not recorded" />
                <ListBlock label="Acceptance criteria review" items={review.acceptance_criteria_review} empty="not recorded" />
                <ListBlock label="Follow-up items" items={review.follow_up_items} empty="none" />
              </div>
            </>
          ) : <p className="operator-evidence-empty">No human semantic review is recorded. Review remains a separate explicit action.</p>}
        </EvidenceCard>

        <EvidenceCard title="Validation" status={validation?.status ?? 'not provided'}>
          {validation ? (
            <>
              <EvidenceFacts items={[
                ['Latest attempt', validation.latest_attempt_id ?? 'not recorded'],
                ['Status', humanize(validation.status)]
              ]} />
              {validation.summary ? <p className="operator-evidence-summary">{validation.summary}</p> : null}
              <div className="operator-evidence-lists">
                <ListBlock label="Commands" items={validation.commands} empty="not reported" />
                <ListBlock label="Tests" items={validation.tests} empty="not reported" />
                <ListBlock label="Warnings" items={validation.warnings} empty="none" />
                <ListBlock label="Evidence artifacts" items={validation.artifact_paths} empty="none" />
              </div>
            </>
          ) : <p className="operator-evidence-empty">No approved validation evidence is recorded.</p>}
        </EvidenceCard>

        <EvidenceCard title="Trusted delivery" status={delivery?.state ?? goal.delivery_state}>
          {delivery ? (
            <>
              <EvidenceFacts items={[
                ['Request', delivery.request_id ?? 'not requested'],
                ['Request status', delivery.request_status ? humanize(delivery.request_status) : 'not recorded'],
                ['Runner run', delivery.runner_run_id ?? 'not started'],
                ['Runner status', delivery.runner_status ? humanize(delivery.runner_status) : 'not recorded'],
                ['Commit', delivery.commit_hash ?? 'not created'],
                ['Pushed', delivery.pushed ? 'yes' : 'no']
              ]} />
              {delivery.validation_summary ? <p className="operator-evidence-summary"><strong>Validation:</strong> {delivery.validation_summary}</p> : null}
              {delivery.test_summary ? <p className="operator-evidence-summary"><strong>Tests:</strong> {delivery.test_summary}</p> : null}
              <div className="operator-evidence-lists">
                <ListBlock label="Expected changed files" items={delivery.expected_changed_files} empty="none recorded" />
                <ListBlock label="Blockers" items={delivery.blockers} empty="none" />
                <ListBlock label="Warnings" items={delivery.warnings} empty="none" />
              </div>
              {delivery.next_action ? <p className="operator-delivery-next"><strong>Delivery next action</strong><span>{delivery.next_action}</span></p> : null}
            </>
          ) : <p className="operator-evidence-empty">Trusted delivery has not been requested.</p>}
        </EvidenceCard>
      </div>
    </section>
  );
}

function EvidenceCard({ title, status, children }: { title: string; status: string; children: React.ReactNode }) {
  return (
    <article className="operator-evidence-card">
      <div className="operator-evidence-card-heading"><h4>{title}</h4><StatusBadge status={humanize(status)} /></div>
      {children}
    </article>
  );
}

function EvidenceFacts({ items }: { items: Array<[string, string]> }) {
  return (
    <dl className="operator-evidence-facts">
      {items.map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}
    </dl>
  );
}

function DiffPreview({ preview, note, truncated }: { preview: string; note: string; truncated: boolean }) {
  return (
    <details className="operator-diff-preview" open={Boolean(preview)}>
      <summary>In-scope worker diff preview{truncated ? ' (truncated)' : ''}</summary>
      {note ? <p>{note}</p> : null}
      {preview ? <pre>{preview}</pre> : <span>No diff preview is available.</span>}
    </details>
  );
}

function DraftReview({ intake }: { intake: RoughGoalIntakePlan }) {
  return (
    <div className="operator-review-stack">
      <div className="operator-review-summary">
        <div><span>Intake</span><strong>{intake.intake_id}</strong></div>
        <div><span>Candidate tasks</span><strong>{intake.candidate_tasks.length}</strong></div>
        <div><span>Risk</span><strong>{intake.suggested_policy_draft.risk_level}</strong></div>
      </div>
      <p className="operator-goal-summary">{intake.normalized_goal_summary}</p>
      <div className="operator-card-list">
        {intake.candidate_tasks.map((task) => (
          <article className="operator-review-card" key={task.task_id}>
            <div className="detail-card-title"><strong>{task.task_id}: {task.title}</strong><StatusBadge status={task.risk_level} /></div>
            <p>{task.summary}</p>
            <ListBlock label="Allowed files" items={task.allowed_files} />
            <ListBlock label="Validation" items={task.validation} />
          </article>
        ))}
      </div>
      <div className="operator-boundary-grid">
        <ListBlock label="Suggested allowed files" items={intake.suggested_allowed_files} />
        <ListBlock label="Do not touch" items={intake.do_not_touch} />
        <ListBlock label="Missing sections" items={intake.missing_sections} empty="none" />
        <ListBlock label="Risk notes" items={intake.risk_notes} empty="none" />
      </div>
    </div>
  );
}

function MaterializedReview({ response }: { response: OperatorConsoleMaterializeResponse }) {
  const { materialization, review } = response;
  return (
    <div className="operator-review-stack">
      <div className="operator-review-summary">
        <div><span>Batch</span><strong>{materialization.batch_id}</strong></div>
        <div><span>Queue</span><strong>{materialization.queue_id}</strong></div>
        <div><span>Source policy</span><strong>{materialization.policy_id}</strong></div>
      </div>
      <div className="operator-card-list">
        {review.backlog_tasks.map((task) => (
          <article className="operator-review-card" key={task.id}>
            <div className="detail-card-title"><strong>{task.id}: {task.title}</strong><StatusBadge status={task.risk_level} /></div>
            <p>{task.summary}</p>
            <ListBlock label="Allowed scope" items={task.allowed_scope} />
            <ListBlock label="Forbidden scope" items={task.forbidden_scope} />
            <ListBlock label="Acceptance criteria" items={task.acceptance_criteria} />
            <ListBlock label="Validation" items={task.validation_expectations} />
          </article>
        ))}
      </div>
      <div className="operator-boundary-grid">
        <ListBlock label="Policy allowed files" items={review.source_policy.allowed_file_patterns} />
        <ListBlock label="Policy forbidden files" items={review.source_policy.forbidden_file_patterns} />
        <ListBlock label="Validation commands" items={review.source_policy.validation_commands} />
        <ListBlock label="Risk notes" items={materialization.risk_notes} empty="none" />
      </div>
    </div>
  );
}

function GuardedActionPanel({ action, children }: { action: OperatorConsoleAction; children: React.ReactNode }) {
  return (
    <section className="panel operator-action-panel">
      <div className="operator-action-heading">
        <div><span className="operator-kicker">Available guarded action</span><h3>{action.label}</h3></div>
        <StatusBadge status={action.confirmation_required ? 'confirmation required' : 'ready'} />
      </div>
      <p>{action.reason}</p>
      <div className="operator-action-form">{children}</div>
      <details className="quiet-details operator-cli-fallback">
        <summary>CLI recovery equivalent</summary>
        <CommandCopyBox command={action.command} />
      </details>
    </section>
  );
}

function StepHeading({ number, title, status }: { number: number; title: string; status: string }) {
  return <div className="operator-step-heading"><span>{number}</span><h3>{title}</h3><StatusBadge status={status} /></div>;
}

function IdentityField({ label, value, onChange, placeholder }: { label: string; value: string; onChange: (value: string) => void; placeholder: string }) {
  return <label className="field-label">{label}<input value={value} onChange={(event) => onChange(event.target.value)} placeholder={placeholder} /></label>;
}

function TextAreaField({ label, value, onChange, placeholder, rows = 5, compact = false, disabled = false }: { label: string; value: string; onChange: (value: string) => void; placeholder: string; rows?: number; compact?: boolean; disabled?: boolean }) {
  return <label className={`field-label wide-field ${compact ? 'compact-textarea' : ''}`}>{label}<textarea disabled={disabled} rows={rows} value={value} onChange={(event) => onChange(event.target.value)} placeholder={placeholder} /></label>;
}

function Confirmation({ checked, onChange, children }: { checked: boolean; onChange: (value: boolean) => void; children: React.ReactNode }) {
  return <label className="confirm-row operator-confirm"><input checked={checked} type="checkbox" onChange={(event) => onChange(event.target.checked)} /><span>{children}</span></label>;
}

function ActionButton({ busy, disabled, label, onClick, danger = false }: { busy: boolean; disabled: boolean; label: string; onClick: () => Promise<void>; danger?: boolean }) {
  return <button className={`operator-primary-button ${danger ? 'danger' : ''}`} disabled={disabled} type="button" onClick={() => void onClick()}>{busy ? 'Working...' : label}</button>;
}

function AttentionPanel({ title, items, quiet = false }: { title: string; items: string[]; quiet?: boolean }) {
  if (!items.length) return null;
  return <section className={`operator-attention ${quiet ? 'quiet' : ''}`}><strong>{title}</strong><ul>{items.map((item) => <li key={item}>{item}</li>)}</ul></section>;
}

function ListBlock({ label, items, empty = 'not specified' }: { label: string; items: string[]; empty?: string }) {
  return <div className="operator-list-block"><strong>{label}</strong>{items.length ? <ul>{items.map((item) => <li key={item}>{item}</li>)}</ul> : <span>{empty}</span>}</div>;
}

function friendlyError(error: unknown): string {
  const raw = error instanceof Error ? error.message : String(error);
  const detailMatch = raw.match(/"message"\s*:\s*"([^"]+)"/);
  return detailMatch?.[1] ?? raw;
}

function humanize(value: string): string {
  return value.replace(/_/g, ' ');
}

function clampNumber(value: string, minimum: number, maximum: number, fallback: number): number {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? Math.min(maximum, Math.max(minimum, parsed)) : fallback;
}

function formatDate(value: string | null): string {
  if (!value) return 'Completion time unavailable';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}
