import { useEffect, useState } from 'react';
import { devoApi } from '../api/client';
import { StatusBadge } from '../components/StatusBadge';
import { SummaryCard } from '../components/SummaryCard';
import type { ApiHealth } from '../types/devo';

export function HealthPage() {
  const [health, setHealth] = useState<ApiHealth | null>(null);
  const [error, setError] = useState<string | null>(null);

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

  if (error) {
    return <p className="error-text">{error}</p>;
  }

  return (
    <section>
      <div className="section-heading">
        <h2>Health</h2>
        <p>Local API status</p>
      </div>
      <div className="summary-grid">
        <SummaryCard title="API status" value={health ? <StatusBadge status={health.status} /> : 'Loading'} />
        <SummaryCard title="Application" value={health?.app ?? 'Loading'} />
        <SummaryCard title="Read-only" value={health ? <StatusBadge status={health.read_only} /> : 'Loading'} />
      </div>
    </section>
  );
}
