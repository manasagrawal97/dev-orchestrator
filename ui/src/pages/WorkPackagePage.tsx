import { CommandCopyBox } from '../components/CommandCopyBox';
import { SummaryCard } from '../components/SummaryCard';

interface WorkPackagePageProps {
  selectedProject: string | null;
}

export function WorkPackagePage({ selectedProject }: WorkPackagePageProps) {
  const project = selectedProject ?? '<project>';

  return (
    <section>
      <div className="section-heading">
        <h2>Work Package</h2>
        <p>Run detail scaffold</p>
      </div>
      <div className="summary-grid">
        <SummaryCard title="Read models">RunOverview and WorkPackageOverview</SummaryCard>
        <SummaryCard title="Planned sections">phase, scope, approval, validation, delivery, lifecycle</SummaryCard>
      </div>
      <CommandCopyBox command={`devo work status --project ${project} --run <runId> --json`} />
      <p className="muted">This scaffold intentionally has no approval, validation, commit, push, or restore actions.</p>
    </section>
  );
}
