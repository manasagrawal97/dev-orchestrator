import type { ReactNode } from 'react';

interface SummaryCardProps {
  title: string;
  value?: ReactNode;
  children?: ReactNode;
}

export function SummaryCard({ title, value, children }: SummaryCardProps) {
  return (
    <section className="summary-card">
      <h3>{title}</h3>
      {value !== undefined ? <div className="summary-value">{value}</div> : null}
      {children}
    </section>
  );
}
