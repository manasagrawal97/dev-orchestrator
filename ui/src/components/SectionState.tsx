import { useEffect, useState } from 'react';
import type { ReactNode } from 'react';

interface SectionStateProps {
  message: string;
  slowMessage?: string;
}

export function LoadingState({ message, slowMessage = 'Still loading this section. Some health checks can take longer.' }: SectionStateProps) {
  const [slow, setSlow] = useState(false);

  useEffect(() => {
    const timer = window.setTimeout(() => setSlow(true), 3200);
    return () => window.clearTimeout(timer);
  }, []);

  return (
    <div className="state-block loading-state">
      <span className="loading-dot" aria-hidden="true" />
      <div>
        <p>{message}</p>
        {slow ? <small>{slowMessage}</small> : null}
      </div>
    </div>
  );
}

export function EmptyState({ message, children }: { message: string; children?: ReactNode }) {
  return (
    <div className="state-block empty-state">
      <p>{message}</p>
      {children}
    </div>
  );
}

export function ErrorState({ message }: { message: string }) {
  return (
    <div className="state-block error-state">
      <p>{message}</p>
    </div>
  );
}
