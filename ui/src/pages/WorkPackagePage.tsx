import { useEffect, useMemo, useState } from 'react';
import { devoApi } from '../api/client';
import { CommandCopyBox } from '../components/CommandCopyBox';
import { JsonDetails } from '../components/JsonDetails';
import { KeyValueList } from '../components/KeyValueList';
import { LifecycleStepper } from '../components/LifecycleStepper';
import { StatusBadge } from '../components/StatusBadge';
import { SummaryCard } from '../components/SummaryCard';
import type { ProjectOverview, RunOverview, WorkPackageOverview } from '../types/devo';

interface WorkPackagePageProps {
  selectedProject: string | null;
  selectedRun: string | null;
  onSelectRun: (runId: string | null) => void;
  onOpenRun: (runId: string) => void;
}

export function WorkPackagePage({ selectedProject, selectedRun, onSelectRun, onOpenRun }: WorkPackagePageProps) {
  const [overview, setOverview] = useState<ProjectOverview | null>(null);
  const [run, setRun] = useState<RunOverview | null>(null);
  const [work, setWork] = useState<WorkPackageOverview | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!selectedProject) {
      setOverview(null);
      return;
    }

    let active = true;
    devoApi
      .getProjectOverview(selectedProject)
      .then((data) => {
        if (!active) {
          return;
        }
        setOverview(data);
        if (!selectedRun) {
          onSelectRun(data.current_run_id ?? data.recent_runs[0]?.run_id ?? null);
        }
      })
      .catch(() => {
        if (active) {
          setOverview(null);
        }
      });
    return () => {
      active = false;
    };
  }, [onSelectRun, selectedProject, selectedRun]);

  useEffect(() => {
    if (!selectedProject || !selectedRun) {
      setRun(null);
      setWork(null);
      return;
    }

    let active = true;
    setLoading(true);
    Promise.all([devoApi.getRunOverview(selectedProject, selectedRun), devoApi.getWorkPackageOverview(selectedProject, selectedRun)])
      .then(([runData, workData]) => {
        if (active) {
          setRun(runData);
          setWork(workData);
          setError(null);
        }
      })
      .catch((err: Error) => {
        if (active) {
          setError(err.message);
          setRun(null);
          setWork(null);
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
  }, [selectedProject, selectedRun]);

  const availableRuns = useMemo(() => overview?.recent_runs ?? [], [overview]);

  if (!selectedProject) {
    return <p className="muted">Select a project before viewing work package details.</p>;
  }

  if (!selectedRun && !availableRuns.length) {
    return <p className="muted">No runs found for {selectedProject}.</p>;
  }

  return (
    <section>
      <div className="section-heading">
        <h2>Work Package</h2>
        <p>{selectedProject}</p>
      </div>

      {availableRuns.length ? (
        <label className="field-label">
          Run
          <select value={selectedRun ?? ''} onChange={(event) => onOpenRun(event.target.value)}>
            {availableRuns.map((item) => (
              <option key={item.run_id} value={item.run_id}>
                {item.run_id} - {item.goal}
              </option>
            ))}
          </select>
        </label>
      ) : null}

      {loading ? <p className="muted">Loading run details...</p> : null}
      {error ? <p className="error-text">{error}</p> : null}

      {run && work ? (
        <>
          <div className="summary-grid">
            <SummaryCard title="Run status" value={<StatusBadge status={run.run_status} />} />
            <SummaryCard title="Work package" value={<StatusBadge status={work.status} />} />
            <SummaryCard title="Validation" value={run.latest_validation_status} />
            <SummaryCard title="Commit" value={run.delivery_commit ?? 'none'} />
          </div>

          <SummaryCard title="Lifecycle">
            <LifecycleStepper status={work.status} />
          </SummaryCard>

          <div className="dashboard-grid">
            <SummaryCard title="Run">
              <KeyValueList
                items={[
                  ['Run id', run.run_id],
                  ['Goal', run.goal],
                  ['Lane', run.lane ?? work.lane],
                  ['Approval bundle', run.approval_bundle_status],
                  ['Latest validation id', run.latest_validation_run_id],
                  ['Delivery summary', run.delivery_summary]
                ]}
              />
            </SummaryCard>
            <SummaryCard title="Work package state">
              <KeyValueList
                items={[
                  ['Scope', work.scope_status],
                  ['Approval', work.approval_status],
                  ['Validation', work.validation_status],
                  ['Delivery', work.delivery_status],
                  ['Next phase', work.next_phase],
                  ['Next command', work.next_command]
                ]}
              />
            </SummaryCard>
          </div>

          {work.next_command ? <CommandCopyBox command={work.next_command} /> : null}

          <section className="panel">
            <h3>Stop conditions</h3>
            {work.stop_conditions_summary.length ? (
              <ul className="plain-list">
                {work.stop_conditions_summary.map((condition) => (
                  <li key={condition}>{condition}</li>
                ))}
              </ul>
            ) : (
              <p className="muted compact">No stop conditions recorded in this read model.</p>
            )}
          </section>

          <section className="panel">
            <h3>Final report expectations</h3>
            <p>
              Keep final delivery in CLI/Codex. Include changed files, validation result, commit hash, push result, final status,
              and any skipped checks.
            </p>
          </section>

          <JsonDetails data={{ run, work }} label="View run/work-package JSON" />
        </>
      ) : null}
    </section>
  );
}
