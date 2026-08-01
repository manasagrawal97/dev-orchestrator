import { useEffect, useMemo, useState } from 'react';
import { devoApi } from '../api/client';
import { CommandCopyBox } from '../components/CommandCopyBox';
import { KeyValueList } from '../components/KeyValueList';
import { EmptyState, ErrorState, LoadingState } from '../components/SectionState';
import { StatusBadge } from '../components/StatusBadge';
import { SummaryCard } from '../components/SummaryCard';
import type { PlanningProgressGroup, ProjectBlueprint, ProjectProgress } from '../types/devo';

interface BlueprintPageProps {
  selectedProject: string | null;
}

interface OptionalState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
}

const emptyOptional = <T,>(): OptionalState<T> => ({ data: null, loading: false, error: null });

export function BlueprintPage({ selectedProject }: BlueprintPageProps) {
  const [blueprint, setBlueprint] = useState<OptionalState<ProjectBlueprint>>(emptyOptional);
  const [progress, setProgress] = useState<OptionalState<ProjectProgress>>(emptyOptional);

  useEffect(() => {
    if (!selectedProject) {
      setBlueprint(emptyOptional<ProjectBlueprint>());
      setProgress(emptyOptional<ProjectProgress>());
      return;
    }

    let active = true;
    setBlueprint({ data: null, loading: true, error: null });
    setProgress({ data: null, loading: true, error: null });

    loadOptional(devoApi.getProjectBlueprint(selectedProject)).then((state) => active && setBlueprint(state));
    loadOptional(devoApi.getProjectProgress(selectedProject)).then((state) => active && setProgress(state));

    return () => {
      active = false;
    };
  }, [selectedProject]);

  const milestoneProgress = useMemo(() => progressMap(progress.data?.milestone_progress ?? []), [progress.data]);
  const epicProgress = useMemo(() => progressMap(progress.data?.epic_progress ?? []), [progress.data]);

  if (!selectedProject) {
    return <p className="muted">Select a project to view its blueprint.</p>;
  }

  if (blueprint.loading) {
    return <LoadingState message="Loading blueprint..." />;
  }

  if (blueprint.error) {
    return <ErrorState message={blueprint.error} />;
  }

  if (!blueprint.data) {
    return (
      <section>
        <div className="section-heading">
          <h2>Blueprint</h2>
          <p>{selectedProject}</p>
        </div>
        <EmptyState message="No Blueprint artifact is available yet.">
          <CommandCopyBox command={`devo project blueprint-create --project ${selectedProject}`} />
        </EmptyState>
      </section>
    );
  }

  return (
    <section>
      <div className="section-heading">
        <h2>Blueprint</h2>
        <p>{selectedProject}</p>
      </div>

      <div className="summary-grid">
        <SummaryCard title="Status" value={<StatusBadge status={blueprint.data.status} />} />
        <SummaryCard title="Milestones" value={blueprint.data.milestones.length} />
        <SummaryCard title="Epics" value={blueprint.data.epics.length} />
        <SummaryCard title="Artifact" value={blueprint.data.artifact_paths?.markdown ?? 'none'} />
      </div>

      <SummaryCard title={blueprint.data.title}>
        <p>{blueprint.data.vision_summary || 'No vision summary recorded.'}</p>
        <CommandCopyBox command={`devo project blueprint-show --project ${selectedProject}`} />
        <CommandCopyBox command={`devo project blueprint-approve --project ${selectedProject}`} />
        <CommandCopyBox command={`devo project backlog-create --project ${selectedProject}`} />
      </SummaryCard>

      <div className="planning-section-grid">
        <ListCard title="Architecture Notes" items={blueprint.data.architecture_notes} />
        <ListCard title="Risk Summary" items={blueprint.data.risk_summary} />
        <ListCard title="Validation Strategy" items={blueprint.data.validation_strategy} />
        <ListCard title="Open Questions" items={blueprint.data.open_questions} />
      </div>

      <section className="panel detail-panel">
        <h3>Milestones</h3>
        {blueprint.data.milestones.length ? (
          <div className="detail-card-grid">
            {blueprint.data.milestones.map((milestone) => {
              const linkedEpics = blueprint.data?.epics.filter((epic) => epic.milestone_id === milestone.id) ?? [];
              return (
                <article className="detail-card" key={milestone.id}>
                  <div className="detail-card-title">
                    <strong>
                      {milestone.id}: {milestone.title}
                    </strong>
                    <StatusBadge status={milestone.status} />
                  </div>
                  <p>{milestone.summary}</p>
                  <KeyValueList
                    items={[
                      ['Target outcome', milestone.target_outcome],
                      ['Linked epics', linkedEpics.map((epic) => epic.id)],
                      ['Tasks', milestoneProgress[milestone.id]?.task_count ?? 0],
                      ['Completed', milestoneProgress[milestone.id]?.completed_task_count ?? 0],
                      ['Completion', `${(milestoneProgress[milestone.id]?.completion_percent ?? 0).toFixed(1)}%`]
                    ]}
                  />
                </article>
              );
            })}
          </div>
        ) : (
          <p className="muted compact">No milestones recorded.</p>
        )}
      </section>

      <section className="panel detail-panel">
        <h3>Epics</h3>
        {blueprint.data.epics.length ? (
          <div className="detail-card-grid">
            {blueprint.data.epics.map((epic) => (
              <article className="detail-card" key={epic.id}>
                <div className="detail-card-title">
                  <strong>
                    {epic.id}: {epic.title}
                  </strong>
                  <StatusBadge status={epic.status} />
                </div>
                <p>{epic.summary}</p>
                <KeyValueList
                  items={[
                    ['Milestone', epic.milestone_id ?? 'none'],
                    ['Tasks', epicProgress[epic.id]?.task_count ?? 0],
                    ['Completed', epicProgress[epic.id]?.completed_task_count ?? 0],
                    ['Blocked', epicProgress[epic.id]?.blocked_task_count ?? 0],
                    ['Completion', `${(epicProgress[epic.id]?.completion_percent ?? 0).toFixed(1)}%`]
                  ]}
                />
              </article>
            ))}
          </div>
        ) : (
          <p className="muted compact">No epics recorded.</p>
        )}
      </section>

      {progress.loading ? <LoadingState message="Loading blueprint progress rollups..." /> : null}
      {progress.error ? <ErrorState message={progress.error} /> : null}
    </section>
  );
}

function ListCard({ title, items }: { title: string; items: string[] }) {
  return (
    <SummaryCard title={title}>
      {items.length ? (
        <ul className="plain-list compact-list">
          {items.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      ) : (
        <p className="muted compact">No items recorded.</p>
      )}
    </SummaryCard>
  );
}

async function loadOptional<T>(request: Promise<T>): Promise<OptionalState<T>> {
  try {
    return { data: await request, loading: false, error: null };
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    if (message.includes('404')) {
      return { data: null, loading: false, error: null };
    }
    return { data: null, loading: false, error: message };
  }
}

function progressMap(groups: PlanningProgressGroup[]): Record<string, PlanningProgressGroup> {
  return Object.fromEntries(groups.map((group) => [group.id, group]));
}
