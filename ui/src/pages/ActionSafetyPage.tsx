import { useEffect, useMemo, useState } from 'react';
import { devoApi } from '../api/client';
import { JsonDetails } from '../components/JsonDetails';
import { LoadingState } from '../components/SectionState';
import { StatusBadge } from '../components/StatusBadge';
import { SummaryCard } from '../components/SummaryCard';
import type { UiActionMetadata, UiActionsResponse } from '../types/devo';

const CATEGORY_LABELS: Record<UiActionMetadata['category'], string> = {
  read_only: 'Read-only',
  workspace_safe: 'Workspace-safe candidates',
  approval_required: 'Approval-required deferred',
  dangerous_deferred: 'Dangerous deferred'
};

export function ActionSafetyPage() {
  const [actions, setActions] = useState<UiActionsResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

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
  const blockedCount = actions?.actions.filter((action) => action.status === 'blocked').length ?? 0;

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
            <SummaryCard title="Blocked/deferred dangerous actions" value={blockedCount} />
          </div>

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
