import { useEffect, useState } from 'react';
import { devoApi } from '../api/client';
import { CommandCopyBox } from '../components/CommandCopyBox';
import { JsonDetails } from '../components/JsonDetails';
import { KeyValueList } from '../components/KeyValueList';
import { StatusBadge } from '../components/StatusBadge';
import { SummaryCard } from '../components/SummaryCard';
import type { ProjectOverview } from '../types/devo';

interface ProjectOverviewPageProps {
  selectedProject: string | null;
  onSelectRun: (runId: string) => void;
}

export function ProjectOverviewPage({ selectedProject, onSelectRun }: ProjectOverviewPageProps) {
  const [overview, setOverview] = useState<ProjectOverview | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!selectedProject) {
      setOverview(null);
      return;
    }

    let active = true;
    setLoading(true);
    devoApi
      .getProjectOverview(selectedProject)
      .then((data) => {
        if (active) {
          setOverview(data);
          setError(null);
        }
      })
      .catch((err: Error) => {
        if (active) {
          setError(err.message);
          setOverview(null);
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
    return <p className="muted">Select a project or run `devo use --project &lt;project&gt;`.</p>;
  }

  if (loading) {
    return <p className="muted">Loading project overview...</p>;
  }

  if (error) {
    return <p className="error-text">{error}</p>;
  }

  if (!overview) {
    return <p className="muted">No project overview is available.</p>;
  }

  const settings = overview.settings_summary;
  const git = overview.git_summary;
  const validation = overview.validation_registry_summary;
  const backup = overview.backup_summary;

  return (
    <section>
      <div className="section-heading">
        <h2>{overview.project_name}</h2>
        <p>{overview.project_path ?? 'unknown path'}</p>
      </div>

      <div className="summary-grid">
        <SummaryCard title="Onboarding" value={<StatusBadge status={overview.onboarding_status} />} />
        <SummaryCard title="Doctor" value={<StatusBadge status={overview.doctor_overall_status} />} />
        <SummaryCard title="Current project" value={<StatusBadge status={overview.is_current_project} />} />
        <SummaryCard title="Current run" value={overview.current_run_id ?? 'none'} />
      </div>

      <div className="dashboard-grid">
        <SummaryCard title="Settings">
          <KeyValueList
            items={[
              ['Default lane', settings.default_lane],
              ['Default validation', settings.default_validation_command],
              ['Default branch', settings.default_branch],
              ['Delivery mode', settings.delivery_mode]
            ]}
          />
        </SummaryCard>
        <SummaryCard title="Git">
          <KeyValueList
            items={[
              ['Status', git.status],
              ['Branch', git.branch],
              ['Clean', git.working_tree_clean],
              ['Ahead', git.ahead],
              ['Behind', git.behind]
            ]}
          />
        </SummaryCard>
        <SummaryCard title="Validation registry">
          <KeyValueList
            items={[
              ['Status', validation.status],
              ['Commands', validation.command_count],
              ['Categories', validation.categories]
            ]}
          />
        </SummaryCard>
        <SummaryCard title="Backup">
          <KeyValueList
            items={[
              ['Status', backup.status],
              ['Normal backups', backup.normal_count],
              ['Protected backups', backup.protected_count],
              ['Incomplete', backup.incomplete_count]
            ]}
          />
        </SummaryCard>
      </div>

      <SummaryCard title="Suggested next action">
        <p>{overview.suggested_next_action}</p>
        <CommandCopyBox command={`devo project overview --project ${overview.project_name} --json`} />
      </SummaryCard>

      <div className="two-column">
        <section className="panel">
          <h3>Recent runs</h3>
          {overview.recent_runs.length ? (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Run</th>
                    <th>Status</th>
                    <th>Goal</th>
                    <th>Validation</th>
                  </tr>
                </thead>
                <tbody>
                  {overview.recent_runs.map((run) => (
                    <tr key={run.run_id}>
                      <td>
                        <button className="link-button" type="button" onClick={() => onSelectRun(run.run_id)}>
                          {run.run_id}
                        </button>
                      </td>
                      <td>{run.run_status}</td>
                      <td>{run.goal}</td>
                      <td>{run.latest_validation_status}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="muted compact">No recent runs.</p>
          )}
        </section>

        <section className="panel">
          <h3>Recent work packages</h3>
          {overview.recent_work_packages.length ? (
            <div className="list-stack">
              {overview.recent_work_packages.map((work) => (
                <button className="work-row" key={work.run_id} type="button" onClick={() => onSelectRun(work.run_id)}>
                  <span>{work.goal ?? work.run_id}</span>
                  <StatusBadge status={work.status} />
                  <small>{work.next_phase}</small>
                </button>
              ))}
            </div>
          ) : (
            <p className="muted compact">No recent work packages.</p>
          )}
        </section>
      </div>

      <JsonDetails data={overview} label="View ProjectOverview JSON" />
    </section>
  );
}
