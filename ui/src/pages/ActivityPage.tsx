import { useEffect, useState } from 'react';
import { devoApi } from '../api/client';
import { CommandCopyBox } from '../components/CommandCopyBox';
import { JsonDetails } from '../components/JsonDetails';
import { LoadingState } from '../components/SectionState';
import { StatusBadge } from '../components/StatusBadge';
import { SummaryCard } from '../components/SummaryCard';
import type { ProjectActivity } from '../types/devo';

interface ActivityPageProps {
  selectedProject: string | null;
}

export function ActivityPage({ selectedProject }: ActivityPageProps) {
  const [activity, setActivity] = useState<ProjectActivity | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!selectedProject) {
      setActivity(null);
      return;
    }

    let active = true;
    setLoading(true);
    devoApi
      .getProjectActivity(selectedProject)
      .then((data) => {
        if (active) {
          setActivity(data);
          setError(null);
        }
      })
      .catch((err: Error) => {
        if (active) {
          setError(err.message);
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
    return <p className="muted">Select a project to view activity.</p>;
  }

  if (loading) {
    return <LoadingState message="Loading project activity..." slowMessage="Still loading activity. Large workspaces can take a little longer to scan." />;
  }

  if (error) {
    return <p className="error-text">{error}</p>;
  }

  if (!activity) {
    return <p className="muted">No activity data is available.</p>;
  }

  return (
    <section>
      <div className="section-heading">
        <h2>Activity</h2>
        <p>{activity.project}</p>
      </div>

      <SummaryCard title="Suggested next action">
        <p>{friendlyNextAction(activity.suggested_next_action)}</p>
        <CommandCopyBox command={`devo project activity --project ${activity.project} --json`} />
      </SummaryCard>

      <div className="two-column">
        <ActivityList title="Recent runs" items={activity.recent_runs} />
        <section className="panel">
          <h3>Delivered work packages</h3>
          {activity.delivered_work_packages.length ? (
            <div className="list-stack">
              {activity.delivered_work_packages.map((item) => (
                <div className="activity-item" key={item.run_id}>
                  <strong>{item.delivery_summary ?? item.goal}</strong>
                  <span>{item.run_id}</span>
                  <span>{item.commit_hash ?? 'no commit recorded'}</span>
                  <StatusBadge status={item.status} />
                </div>
              ))}
            </div>
          ) : (
            <p className="muted compact">No delivered packages in the recent window.</p>
          )}
        </section>
        <ActivityList title="Validation summaries" items={activity.latest_validation_runs} />
        <ActivityList title="Reports" items={activity.latest_reports} collapsed />
        <ActivityList title="Context updates" items={activity.latest_context_updates} collapsed />
        <SummaryCard title="Current Git status" value={activity.current_git_status} />
      </div>

      <JsonDetails data={activity} label="View activity JSON" />
    </section>
  );
}

function ActivityList({ title, items, collapsed = false }: { title: string; items: string[]; collapsed?: boolean }) {
  const content = items.length ? (
    <ul className="plain-list activity-list">
      {items.map((item) => (
        <li key={item}>
          <strong>{friendlyActivityLabel(item)}</strong>
          {friendlyActivityDetail(item) ? <small>{friendlyActivityDetail(item)}</small> : null}
        </li>
      ))}
    </ul>
  ) : (
    <p className="muted compact">None found.</p>
  );

  const panelBody = collapsed ? (
    <details className="quiet-details">
      <summary>Show {items.length} item{items.length === 1 ? '' : 's'}</summary>
      {content}
    </details>
  ) : (
    content
  );

  return (
    <section className={collapsed ? 'panel quiet-panel' : 'panel'}>
      <h3>{title}</h3>
      {panelBody}
    </section>
  );
}

function friendlyNextAction(nextAction: string): string {
  if (/^Continue\s+\S+:\s+Implement approved scope/i.test(nextAction)) {
    return 'Review project activity before starting the next scoped work package.';
  }
  return nextAction || 'Review project activity.';
}

function friendlyActivityLabel(item: string): string {
  const [label] = item.split(': ');
  return label.replace(/\\/g, '/');
}

function friendlyActivityDetail(item: string): string {
  const separator = item.indexOf(': ');
  if (separator === -1) {
    return '';
  }
  return item.slice(separator + 2);
}
