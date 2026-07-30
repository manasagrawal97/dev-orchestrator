import { CommandCopyBox } from '../components/CommandCopyBox';
import { SummaryCard } from '../components/SummaryCard';

interface ProjectOverviewPageProps {
  selectedProject: string | null;
}

export function ProjectOverviewPage({ selectedProject }: ProjectOverviewPageProps) {
  return (
    <section>
      <div className="section-heading">
        <h2>Project Overview</h2>
        <p>{selectedProject ?? 'No project selected'}</p>
      </div>
      <div className="summary-grid">
        <SummaryCard title="Read model">ProjectOverview</SummaryCard>
        <SummaryCard title="Planned sections">settings, validation, Git, backup, recent work</SummaryCard>
      </div>
      {selectedProject ? <CommandCopyBox command={`devo project overview --project ${selectedProject} --json`} /> : null}
      <p className="muted">This page will hydrate from the project overview endpoint in TASK-DEVO-067.</p>
    </section>
  );
}
