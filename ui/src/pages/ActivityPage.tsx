import { useEffect, useState } from 'react';
import { devoApi } from '../api/client';
import { CommandCopyBox } from '../components/CommandCopyBox';
import { JsonDetails } from '../components/JsonDetails';
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
    return <p className="muted">Loading project activity...</p>;
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
        <p>{activity.suggested_next_action}</p>
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
        <ActivityList title="Reports" items={activity.latest_reports} />
        <ActivityList title="Context updates" items={activity.latest_context_updates} />
        <SummaryCard title="Current Git status" value={activity.current_git_status} />
      </div>

      <JsonDetails data={activity} label="View activity JSON" />
    </section>
  );
}

function ActivityList({ title, items }: { title: string; items: string[] }) {
  return (
    <section className="panel">
      <h3>{title}</h3>
      {items.length ? (
        <ul className="plain-list">
          {items.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      ) : (
        <p className="muted compact">None found.</p>
      )}
    </section>
  );
}
