import { useEffect, useState } from 'react';
import { devoApi } from '../api/client';
import { CommandCopyBox } from '../components/CommandCopyBox';
import { JsonDetails } from '../components/JsonDetails';
import { StatusBadge } from '../components/StatusBadge';
import { SummaryCard } from '../components/SummaryCard';
import type { ApiHealth, DoctorReport } from '../types/devo';

interface HealthPageProps {
  selectedProject: string | null;
}

export function HealthPage({ selectedProject }: HealthPageProps) {
  const [health, setHealth] = useState<ApiHealth | null>(null);
  const [doctor, setDoctor] = useState<DoctorReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [doctorError, setDoctorError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    devoApi
      .getHealth()
      .then((data) => {
        if (active) {
          setHealth(data);
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
    if (!selectedProject) {
      setDoctor(null);
      setDoctorError(null);
      return;
    }

    let active = true;
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
          setDoctor(null);
        }
      });
    return () => {
      active = false;
    };
  }, [selectedProject]);

  return (
    <section>
      <div className="section-heading">
        <h2>Health</h2>
        <p>{selectedProject ?? 'API only'}</p>
      </div>

      {error ? <p className="error-text">{error}</p> : null}

      <div className="summary-grid">
        <SummaryCard title="API status" value={health ? <StatusBadge status={health.status} /> : 'Loading'} />
        <SummaryCard title="Application" value={health?.app ?? 'Loading'} />
        <SummaryCard title="Read-only" value={health ? <StatusBadge status={health.read_only} /> : 'Loading'} />
        <SummaryCard title="Selected project" value={selectedProject ?? 'none'} />
      </div>

      {!selectedProject ? <p className="muted">Select a project to load project doctor checks.</p> : null}
      {doctorError ? <p className="error-text">{doctorError}</p> : null}

      {doctor ? (
        <>
          <SummaryCard title="Doctor summary">
            <p>
              <StatusBadge status={doctor.overall_status} /> {doctor.suggested_next_action}
            </p>
            <CommandCopyBox command={`devo doctor --project ${selectedProject} --json`} />
          </SummaryCard>

          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Status</th>
                  <th>Check</th>
                  <th>Detail</th>
                </tr>
              </thead>
              <tbody>
                {doctor.checks.map((check) => (
                  <tr key={`${check.name}-${check.detail}`}>
                    <td>
                      <StatusBadge status={check.status} />
                    </td>
                    <td>{check.name}</td>
                    <td>{check.detail}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <JsonDetails data={doctor} label="View doctor JSON" />
        </>
      ) : null}
    </section>
  );
}
