import { useEffect, useState } from 'react';
import { devoApi } from '../api/client';
import { CommandCopyBox } from '../components/CommandCopyBox';
import { JsonDetails } from '../components/JsonDetails';
import { KeyValueList } from '../components/KeyValueList';
import { ErrorState, LoadingState } from '../components/SectionState';
import { StatusBadge } from '../components/StatusBadge';
import { SummaryCard } from '../components/SummaryCard';
import type { DoctorReport, ProjectActivity, ProjectOverview } from '../types/devo';

interface ProjectOverviewPageProps {
  selectedProject: string | null;
  onSelectRun: (runId: string) => void;
}

export function ProjectOverviewPage({ selectedProject, onSelectRun }: ProjectOverviewPageProps) {
  const [overview, setOverview] = useState<ProjectOverview | null>(null);
  const [activity, setActivity] = useState<ProjectActivity | null>(null);
  const [doctor, setDoctor] = useState<DoctorReport | null>(null);
  const [overviewLoading, setOverviewLoading] = useState(false);
  const [activityLoading, setActivityLoading] = useState(false);
  const [doctorLoading, setDoctorLoading] = useState(false);
  const [overviewError, setOverviewError] = useState<string | null>(null);
  const [activityError, setActivityError] = useState<string | null>(null);
  const [doctorError, setDoctorError] = useState<string | null>(null);

  useEffect(() => {
    if (!selectedProject) {
      setOverview(null);
      setActivity(null);
      setDoctor(null);
      return;
    }

    let active = true;
    setOverview(null);
    setActivity(null);
    setDoctor(null);
    setOverviewError(null);
    setActivityError(null);
    setDoctorError(null);
    setOverviewLoading(true);
    setActivityLoading(true);
    setDoctorLoading(true);

    devoApi
      .getProjectOverview(selectedProject)
      .then((data) => {
        if (active) {
          setOverview(data);
          setOverviewError(null);
        }
      })
      .catch((err: Error) => {
        if (active) {
          setOverviewError(err.message);
        }
      })
      .finally(() => {
        if (active) {
          setOverviewLoading(false);
        }
      });

    devoApi
      .getProjectActivity(selectedProject)
      .then((data) => {
        if (active) {
          setActivity(data);
          setActivityError(null);
        }
      })
      .catch((err: Error) => {
        if (active) {
          setActivityError(err.message);
        }
      })
      .finally(() => {
        if (active) {
          setActivityLoading(false);
        }
      });

    devoApi
      .getProjectDoctor(selectedProject)
      .then((data) => {
        if (active) {
          setDoctor(data);
          setDoctorError(null);
        }
      })
      .catch((err: Error) => {
        if (active) {
          setDoctorError(err.message);
        }
      })
      .finally(() => {
        if (active) {
          setDoctorLoading(false);
        }
      });

    return () => {
      active = false;
    };
  }, [selectedProject]);

  if (!selectedProject) {
    return <p className="muted">Select a project or run `devo use --project &lt;project&gt;`.</p>;
  }

  const settings = overview?.settings_summary;
  const git = overview?.git_summary;
  const validation = overview?.validation_registry_summary;
  const backup = overview?.backup_summary;
  const recentRuns = overview?.recent_runs ?? [];
  const recentWork = overview?.recent_work_packages ?? [];
  const nextAction = friendlyNextAction(overview?.suggested_next_action ?? activity?.suggested_next_action);

  return (
    <section>
      <div className="section-heading">
        <h2>{selectedProject}</h2>
        <p>{overview?.project_path ?? 'Loading project path...'}</p>
      </div>

      <div className="summary-grid">
        <SummaryCard title="Dashboard project" value={selectedProject} />
        <SummaryCard
          title="Onboarding"
          value={overview ? <StatusBadge status={overview.onboarding_status} /> : overviewLoading ? 'Loading' : 'unknown'}
        />
        <SummaryCard
          title="Doctor"
          value={
            doctor ? (
              <StatusBadge status={doctor.overall_status} />
            ) : doctorLoading ? (
              'Loading'
            ) : (
              <StatusBadge status={overview?.doctor_overall_status ?? 'unknown'} />
            )
          }
        />
        <SummaryCard title="CLI current project" value={<StatusBadge status={overview?.is_current_project ?? false} />} />
      </div>

      {overviewLoading ? <LoadingState message="Loading overview sections..." /> : null}
      {overviewError ? <ErrorState message={overviewError} /> : null}

      <div className="dashboard-grid">
        <SummaryCard title="Settings">
          {settings ? (
            <KeyValueList
              items={[
                ['Default lane', settings.default_lane],
                ['Default validation', settings.default_validation_command],
                ['Default branch', settings.default_branch],
                ['Delivery mode', settings.delivery_mode]
              ]}
            />
          ) : (
            overviewLoading ? <LoadingState message="Loading settings summary..." /> : <ErrorState message="Settings summary is unavailable." />
          )}
        </SummaryCard>
        <SummaryCard title="Git">
          {git ? (
            <KeyValueList
              items={[
                ['Status', git.status],
                ['Branch', git.branch],
                ['Clean', git.working_tree_clean],
                ['Ahead', git.ahead],
                ['Behind', git.behind]
              ]}
            />
          ) : (
            overviewLoading ? <LoadingState message="Loading Git summary..." /> : <ErrorState message="Git summary is unavailable." />
          )}
        </SummaryCard>
        <SummaryCard title="Validation registry">
          {validation ? (
            <KeyValueList
              items={[
                ['Status', validation.status],
                ['Commands', validation.command_count],
                ['Categories', validation.categories]
              ]}
            />
          ) : (
            overviewLoading ? <LoadingState message="Loading validation summary..." /> : <ErrorState message="Validation summary is unavailable." />
          )}
        </SummaryCard>
        <SummaryCard title="Backup">
          {backup ? (
            <KeyValueList
              items={[
                ['Status', backup.status],
                ['Normal backups', backup.normal_count],
                ['Protected backups', backup.protected_count],
                ['Incomplete', backup.incomplete_count]
              ]}
            />
          ) : (
            overviewLoading ? <LoadingState message="Loading backup summary..." /> : <ErrorState message="Backup summary is unavailable." />
          )}
        </SummaryCard>
        <SummaryCard title="Planning">
          {overview ? (
            <>
              <KeyValueList
                items={[
                  ['Brief', overview.brief_status],
                  ['Blueprint', overview.blueprint_status],
                  ['Milestones', overview.blueprint_milestone_count],
                  ['Epics', overview.blueprint_epic_count],
                  ['Backlog', overview.backlog_status],
                  ['Tasks', overview.backlog_task_count],
                  ['Ready', overview.backlog_ready_count],
                  ['Blocked', overview.backlog_blocked_count],
                  ['Completed', overview.backlog_completed_count],
                  ['Refinement prompt', overview.backlog_refinement_prompt_exists ? 'available' : 'missing']
                ]}
              />
              <p className="muted compact">{overview.planning_next_action}</p>
              <CommandCopyBox command={`devo project backlog-prompt --project ${selectedProject}`} />
            </>
          ) : (
            overviewLoading ? <LoadingState message="Loading planning summary..." /> : <ErrorState message="Planning summary is unavailable." />
          )}
        </SummaryCard>
      </div>

      <SummaryCard title="Suggested next action">
        <p>{nextAction}</p>
        <CommandCopyBox command={`devo project overview --project ${selectedProject} --json`} />
      </SummaryCard>

      <div className="two-column">
        <section className="panel">
          <h3>Recent runs</h3>
          {recentRuns.length ? (
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
                  {recentRuns.map((run) => (
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
          ) : overviewLoading ? (
            <LoadingState message="Loading recent runs..." />
          ) : (
            <p className="muted compact">No recent runs.</p>
          )}
        </section>

        <section className="panel">
          <h3>Recent work packages</h3>
          {recentWork.length ? (
            <div className="list-stack">
              {recentWork.map((work) => (
                <button className="work-row" key={work.run_id} type="button" onClick={() => onSelectRun(work.run_id)}>
                  <span>{work.goal ?? work.run_id}</span>
                  <StatusBadge status={work.status} />
                  <small>{work.next_phase}</small>
                </button>
              ))}
            </div>
          ) : overviewLoading ? (
            <LoadingState message="Loading recent work packages..." />
          ) : (
            <p className="muted compact">No recent work packages.</p>
          )}
        </section>

        <section className="panel">
          <h3>Doctor detail</h3>
          {doctor ? (
            <p>
              <StatusBadge status={doctor.overall_status} /> {doctor.suggested_next_action}
            </p>
          ) : doctorLoading ? (
            <LoadingState message="Loading doctor checks..." />
          ) : doctorError ? (
            <ErrorState message={doctorError} />
          ) : (
            <p className="muted compact">Doctor detail is not available.</p>
          )}
        </section>

        <section className="panel">
          <h3>Activity preview</h3>
          {activity ? (
            <p>{activity.recent_runs.length} recent runs, {activity.delivered_work_packages.length} delivered packages.</p>
          ) : activityLoading ? (
            <LoadingState message="Loading activity summary..." />
          ) : activityError ? (
            <ErrorState message={activityError} />
          ) : (
            <p className="muted compact">Activity summary is not available.</p>
          )}
        </section>
      </div>

      {overview ? <JsonDetails data={overview} label="View ProjectOverview JSON" /> : null}
    </section>
  );
}

function friendlyNextAction(nextAction: string | null | undefined): string {
  if (!nextAction || /^Continue\s+\S+:\s+Implement approved scope/i.test(nextAction)) {
    return 'Review project activity or start a scoped work package from the CLI.';
  }
  return nextAction;
}
