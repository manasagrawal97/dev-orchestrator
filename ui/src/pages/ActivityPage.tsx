import { CommandCopyBox } from '../components/CommandCopyBox';
import { SummaryCard } from '../components/SummaryCard';

interface ActivityPageProps {
  selectedProject: string | null;
}

export function ActivityPage({ selectedProject }: ActivityPageProps) {
  return (
    <section>
      <div className="section-heading">
        <h2>Activity</h2>
        <p>{selectedProject ?? 'No project selected'}</p>
      </div>
      <div className="summary-grid">
        <SummaryCard title="Read model">Project activity summary</SummaryCard>
        <SummaryCard title="Planned sections">runs, delivered work, validations, reports, visuals, context updates</SummaryCard>
      </div>
      {selectedProject ? <CommandCopyBox command={`devo project activity --project ${selectedProject} --json`} /> : null}
      <p className="muted">This page will consume the activity endpoint in TASK-DEVO-067.</p>
    </section>
  );
}
