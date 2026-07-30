import { useEffect, useMemo, useState } from 'react';
import { devoApi } from '../api/client';
import { CommandCopyBox } from '../components/CommandCopyBox';
import { JsonDetails } from '../components/JsonDetails';
import { LoadingState } from '../components/SectionState';
import { StatusBadge } from '../components/StatusBadge';
import { SummaryCard } from '../components/SummaryCard';
import type { UiActionExecutionResult, UiActionMetadata, UiActionsResponse } from '../types/devo';

const CATEGORY_LABELS: Record<UiActionMetadata['category'], string> = {
  read_only: 'Read-only',
  workspace_safe: 'Workspace-safe candidates',
  approval_required: 'Approval-required deferred',
  dangerous_deferred: 'Dangerous deferred'
};

const EXECUTABLE_WORKSPACE_ACTIONS = new Set([
  'work.scope_template.generate',
  'visual.work_package.generate',
  'visual.project_activity.generate',
  'onboarding.report.write'
]);
const RUN_REQUIRED_ACTIONS = new Set(['work.scope_template.generate', 'visual.work_package.generate']);

interface ActionSafetyPageProps {
  selectedProject: string | null;
  selectedRun: string | null;
}

export function ActionSafetyPage({ selectedProject, selectedRun }: ActionSafetyPageProps) {
  const [actions, setActions] = useState<UiActionsResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [projectInput, setProjectInput] = useState(selectedProject ?? '');
  const [runInput, setRunInput] = useState(selectedRun ?? '');
  const [confirmed, setConfirmed] = useState(false);
  const [runningActionId, setRunningActionId] = useState<string | null>(null);
  const [result, setResult] = useState<UiActionExecutionResult | null>(null);
  const [executeError, setExecuteError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    devoApi
      .getUiActions()
      .then((data) => {
        if (active) {
          setActions(data);
          setError(null);
        }
      })
      .catch((err: Error) => {
        if (active) {
          setError(err.message);
        }
      });
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (selectedProject) {
      setProjectInput(selectedProject);
    }
  }, [selectedProject]);

  useEffect(() => {
    if (selectedRun) {
      setRunInput(selectedRun);
    }
  }, [selectedRun]);

  const groupedActions = useMemo(() => {
    const groups = new Map<UiActionMetadata['category'], UiActionMetadata[]>();
    for (const action of actions?.actions ?? []) {
      const items = groups.get(action.category) ?? [];
      items.push(action);
      groups.set(action.category, items);
    }
    return groups;
  }, [actions]);

  const readOnlyCount = actions?.actions.filter((action) => action.allowed_in_ui_v1).length ?? 0;
  const workspaceCandidateCount = actions?.actions.filter((action) => action.category === 'workspace_safe').length ?? 0;
  const executableWorkspaceCount = actions?.actions.filter((action) => EXECUTABLE_WORKSPACE_ACTIONS.has(action.id)).length ?? 0;
  const blockedCount = actions?.actions.filter((action) => action.status === 'blocked').length ?? 0;

  function canExecute(action: UiActionMetadata) {
    if (!EXECUTABLE_WORKSPACE_ACTIONS.has(action.id)) {
      return false;
    }
    if (!confirmed || !projectInput.trim()) {
      return false;
    }
    return !RUN_REQUIRED_ACTIONS.has(action.id) || Boolean(runInput.trim());
  }

  async function executeAction(action: UiActionMetadata) {
    setRunningActionId(action.id);
    setResult(null);
    setExecuteError(null);
    try {
      const data = await devoApi.executeUiAction({
        action_id: action.id,
        project: projectInput.trim(),
        run_id: runInput.trim() || null,
        confirm: confirmed
      });
      setResult(data);
    } catch (err) {
      setExecuteError(err instanceof Error ? err.message : 'Action execution failed.');
    } finally {
      setRunningActionId(null);
    }
  }

  return (
    <section>
      <div className="section-heading">
        <h2>UI Actions / Safety</h2>
        <p>{actions?.ui_mode ?? 'read-only'}</p>
      </div>

      <section className="readonly-banner safety-banner">
        <strong>Informational only.</strong>
        <span>This page describes action safety boundaries. It does not execute, approve, validate, commit, push, restore, or modify schedulers.</span>
      </section>

      {error ? <p className="error-text">{error}</p> : null}
      {!actions && !error ? <LoadingState message="Loading UI action safety registry..." /> : null}

      {actions ? (
        <>
          <div className="summary-grid">
            <SummaryCard title="UI mode" value={actions.ui_mode} />
            <SummaryCard title="Actions registered" value={actions.count} />
            <SummaryCard title="Allowed in UI v1" value={readOnlyCount} />
            <SummaryCard title="Workspace-safe candidates" value={workspaceCandidateCount} />
            <SummaryCard title="Executable workspace-safe actions" value={executableWorkspaceCount} />
            <SummaryCard title="Blocked/deferred dangerous actions" value={blockedCount} />
          </div>

          <section className="panel action-execute-panel">
            <h3>Controlled workspace-safe execution</h3>
            <p>
              These controls can write Devo workspace artifacts only. They do not touch target repositories, run validation, commit, push,
              restore backups, modify schedulers, run target apps, or call model APIs.
            </p>
            <div className="action-form-grid">
              <label className="field-label">
                Project
                <input value={projectInput} onChange={(event) => setProjectInput(event.target.value)} placeholder="DevOrchestrator" />
              </label>
              <label className="field-label">
                Run ID
                <input value={runInput} onChange={(event) => setRunInput(event.target.value)} placeholder="Required for run-specific actions" />
              </label>
            </div>
            <label className="confirm-row">
              <input checked={confirmed} type="checkbox" onChange={(event) => setConfirmed(event.target.checked)} />
              <span>I understand this writes Devo workspace artifacts only.</span>
            </label>
            {executeError ? <p className="error-text compact">{executeError}</p> : null}
            {result ? (
              <div className="action-result">
                <p>
                  <StatusBadge status={result.status} /> {result.message}
                </p>
                {result.artifact_path ? <p className="project-path">Artifact: {result.artifact_path}</p> : null}
                {result.suggested_next_command ? <CommandCopyBox command={result.suggested_next_command} /> : null}
              </div>
            ) : null}
          </section>

          <div className="action-group-stack">
            {Array.from(groupedActions.entries()).map(([category, items]) => (
              <section className="panel" key={category}>
                <div className="action-group-heading">
                  <h3>{CATEGORY_LABELS[category]}</h3>
                  <span>{items.length}</span>
                </div>
                <div className="action-card-grid">
                  {items.map((action) => (
                    <article className="action-card" key={action.id}>
                      <div className="action-card-title">
                        <strong>{action.label}</strong>
                        <StatusBadge status={action.status} />
                      </div>
                      <p>{action.description}</p>
                      <dl className="key-value-list compact-list">
                        <div>
                          <dt>Risk</dt>
                          <dd>{action.risk_level}</dd>
                        </div>
                        <div>
                          <dt>UI v1</dt>
                          <dd>{action.allowed_in_ui_v1 ? 'Allowed as read-only' : 'Not available'}</dd>
                        </div>
                        <div>
                          <dt>Mutates workspace</dt>
                          <dd>{action.mutates_workspace ? 'yes' : 'no'}</dd>
                        </div>
                        <div>
                          <dt>Mutates target</dt>
                          <dd>{action.mutates_target_project ? 'yes' : 'no'}</dd>
                        </div>
                        <div>
                          <dt>Approval</dt>
                          <dd>{action.requires_approval ? 'required' : 'not required'}</dd>
                        </div>
                      </dl>
                      <p className="action-reason">{action.reason}</p>
                      {action.required_cli_command ? <code className="inline-command">{action.required_cli_command}</code> : null}
                      {EXECUTABLE_WORKSPACE_ACTIONS.has(action.id) ? (
                        <button
                          className="secondary-action-button"
                          disabled={!canExecute(action) || runningActionId !== null}
                          type="button"
                          onClick={() => void executeAction(action)}
                        >
                          {runningActionId === action.id ? 'Generating...' : 'Generate workspace artifact'}
                        </button>
                      ) : null}
                    </article>
                  ))}
                </div>
              </section>
            ))}
          </div>

          <JsonDetails data={actions} label="View action metadata JSON" />
        </>
      ) : null}
    </section>
  );
}
