import { useEffect, useMemo, useState } from 'react';
import type { ReactNode } from 'react';
import { devoApi } from '../api/client';
import { CommandCopyBox } from '../components/CommandCopyBox';
import { KeyValueList } from '../components/KeyValueList';
import { EmptyState, ErrorState, LoadingState } from '../components/SectionState';
import { StatusBadge } from '../components/StatusBadge';
import { SummaryCard } from '../components/SummaryCard';
import type {
  ProjectBacklog,
  ProjectBatchesResponse,
  ProjectBlueprint,
  ProjectBrief,
  ProjectHandoffsResponse,
  ProjectOverview,
  ProjectProgress,
  ProjectQueuesResponse
} from '../types/devo';

interface PlanningIntakePageProps {
  selectedProject: string | null;
  onOpenPage?: (page: 'blueprint' | 'backlog' | 'batches' | 'queues' | 'handoffs' | 'worker-runs' | 'progress') => void;
}

interface OptionalState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
}

type StageState = 'complete' | 'current' | 'upcoming';

const emptyOptional = <T,>(): OptionalState<T> => ({ data: null, loading: false, error: null });

export function PlanningIntakePage({ selectedProject, onOpenPage }: PlanningIntakePageProps) {
  const [overview, setOverview] = useState<OptionalState<ProjectOverview>>(emptyOptional);
  const [brief, setBrief] = useState<OptionalState<ProjectBrief>>(emptyOptional);
  const [blueprint, setBlueprint] = useState<OptionalState<ProjectBlueprint>>(emptyOptional);
  const [backlog, setBacklog] = useState<OptionalState<ProjectBacklog>>(emptyOptional);
  const [batches, setBatches] = useState<OptionalState<ProjectBatchesResponse>>(emptyOptional);
  const [queues, setQueues] = useState<OptionalState<ProjectQueuesResponse>>(emptyOptional);
  const [handoffs, setHandoffs] = useState<OptionalState<ProjectHandoffsResponse>>(emptyOptional);
  const [progress, setProgress] = useState<OptionalState<ProjectProgress>>(emptyOptional);

  useEffect(() => {
    if (!selectedProject) {
      resetAll();
      return;
    }

    let active = true;
    setLoadingAll();

    loadOptional(devoApi.getProjectOverview(selectedProject)).then((state) => active && setOverview(state));
    loadOptional(devoApi.getProjectBrief(selectedProject)).then((state) => active && setBrief(state));
    loadOptional(devoApi.getProjectBlueprint(selectedProject)).then((state) => active && setBlueprint(state));
    loadOptional(devoApi.getProjectBacklog(selectedProject)).then((state) => active && setBacklog(state));
    loadOptional(devoApi.getProjectBatches(selectedProject)).then((state) => active && setBatches(state));
    loadOptional(devoApi.getProjectQueues(selectedProject)).then((state) => active && setQueues(state));
    loadOptional(devoApi.getProjectHandoffs(selectedProject)).then((state) => active && setHandoffs(state));
    loadOptional(devoApi.getProjectProgress(selectedProject)).then((state) => active && setProgress(state));

    return () => {
      active = false;
    };
  }, [selectedProject]);

  const latestBatch = useMemo(() => batches.data?.batches[0] ?? null, [batches.data]);
  const latestQueue = useMemo(() => queues.data?.queues[0] ?? null, [queues.data]);
  const latestHandoff = useMemo(() => handoffs.data?.handoffs[0] ?? null, [handoffs.data]);

  if (!selectedProject) {
    return <p className="muted">Select a project to view planning intake.</p>;
  }

  return (
    <section>
      <div className="section-heading">
        <h2>Planning Intake</h2>
        <p>{selectedProject}</p>
      </div>

      <section className="planning-pipeline" aria-label="Planning workflow">
        {pipelineStages(overview.data).map((stage, index) => (
          <div className={`planning-stage ${stage.state}`} key={stage.label}>
            <span>{index + 1}</span>
            <strong>{stage.label}</strong>
            <StatusBadge status={stage.status} />
            <small>{stage.summary}</small>
            <code>{stage.command}</code>
          </div>
        ))}
      </section>

      <SummaryCard title="Read-only operator guidance">
        <p className="compact">
          This page shows planning state and CLI commands only. It does not create briefs, approve plans, run Codex, execute target commands,
          run validation, commit, push, restore backups, or modify schedulers.
        </p>
      </SummaryCard>

      <div className="planning-section-grid">
        <PlanningSection title="Project Brief" state={brief}>
          {brief.data ? (
            <>
              <KeyValueList
                items={[
                  ['Status', brief.data.status],
                  ['Title', brief.data.title],
                  ['Summary', excerpt(brief.data.summary)],
                  ['Markdown', brief.data.artifact_paths?.markdown ?? 'none']
                ]}
              />
            </>
          ) : (
            <EmptyState message="No Project Brief artifact is available yet." />
          )}
          <CommandCopyBox command={`devo project brief-create --project ${selectedProject} --title "<title>" --file <brief.md>`} />
          <CommandCopyBox command={`devo project brief-approve --project ${selectedProject}`} />
        </PlanningSection>

        <PlanningSection title="Blueprint" state={blueprint}>
          {blueprint.data ? (
            <KeyValueList
              items={[
                ['Status', blueprint.data.status],
                ['Title', blueprint.data.title],
                ['Milestones', blueprint.data.milestones.length],
                ['Epics', blueprint.data.epics.length],
                ['Markdown', blueprint.data.artifact_paths?.markdown ?? 'none']
              ]}
            />
          ) : (
            <EmptyState message="No Blueprint artifact is available yet." />
          )}
          <CommandCopyBox command={`devo project blueprint-create --project ${selectedProject}`} />
          <CommandCopyBox command={`devo project blueprint-approve --project ${selectedProject}`} />
          {onOpenPage ? (
            <button className="link-button detail-link" type="button" onClick={() => onOpenPage('blueprint')}>
              Open Blueprint detail
            </button>
          ) : null}
        </PlanningSection>

        <PlanningSection title="Backlog" state={backlog}>
          {backlog.data ? (
            <KeyValueList
              items={[
                ['Status', backlog.data.status],
                ['Tasks', backlog.data.task_count],
                ['Ready', backlog.data.ready_task_count],
                ['Blocked', backlog.data.blocked_task_count],
                ['Completed', backlog.data.completed_task_count],
                ['Refinement prompt', overview.data?.backlog_refinement_prompt_exists ? 'available' : 'missing']
              ]}
            />
          ) : (
            <EmptyState message="No Backlog artifact is available yet." />
          )}
          <CommandCopyBox command={`devo project backlog-create --project ${selectedProject}`} />
          <CommandCopyBox command={`devo project backlog-prompt --project ${selectedProject}`} />
          <CommandCopyBox command={`devo project backlog-import --project ${selectedProject} --file <file>`} />
          <CommandCopyBox command={`devo project backlog-approve --project ${selectedProject}`} />
          {onOpenPage ? (
            <button className="link-button detail-link" type="button" onClick={() => onOpenPage('backlog')}>
              Open Backlog detail
            </button>
          ) : null}
        </PlanningSection>

        <PlanningSection title="Batch" state={batches}>
          <KeyValueList
            items={[
              ['Batches', batches.data?.count ?? 0],
              ['Approved', overview.data?.approved_batch_count ?? 0],
              ['Latest batch', latestBatch?.batch_id ?? 'none'],
              ['Latest status', latestBatch?.status ?? 'none'],
              ['Latest approval', latestBatch?.approval_status ?? 'none']
            ]}
          />
          <CommandCopyBox command={`devo project batch-suggest --project ${selectedProject} --limit 10`} />
          <CommandCopyBox command={`devo project batch-suggest --project ${selectedProject} --limit 10 --write`} />
          <CommandCopyBox command={`devo project batch-approve --project ${selectedProject} --batch ${latestBatch?.batch_id ?? '<batchId>'}`} />
          {onOpenPage ? (
            <button className="link-button detail-link" type="button" onClick={() => onOpenPage('batches')}>
              Open Batch detail
            </button>
          ) : null}
        </PlanningSection>

        <PlanningSection title="Queue" state={queues}>
          <KeyValueList
            items={[
              ['Queues', queues.data?.count ?? 0],
              ['Latest queue', latestQueue?.queue_id ?? 'none'],
              ['Latest status', latestQueue?.status ?? 'none'],
              ['Current item', latestQueue?.current_item_id ?? 'none'],
              ['Pending', latestQueue?.pending_count ?? 0],
              ['Completed', latestQueue?.completed_count ?? 0],
              ['Blocked', latestQueue?.blocked_count ?? 0]
            ]}
          />
          <CommandCopyBox command={`devo project queue-create --project ${selectedProject} --batch ${latestBatch?.batch_id ?? '<batchId>'}`} />
          <CommandCopyBox command={`devo project queue-start --project ${selectedProject} --queue ${latestQueue?.queue_id ?? '<queueId>'}`} />
          <CommandCopyBox command={`devo project queue-next --project ${selectedProject} --queue ${latestQueue?.queue_id ?? '<queueId>'}`} />
          {onOpenPage ? (
            <button className="link-button detail-link" type="button" onClick={() => onOpenPage('queues')}>
              Open Queue detail
            </button>
          ) : null}
        </PlanningSection>

        <PlanningSection title="Handoff" state={handoffs}>
          <KeyValueList
            items={[
              ['Handoffs', handoffs.data?.count ?? 0],
              ['Latest handoff', latestHandoff?.handoff_id ?? 'none'],
              ['Latest type', latestHandoff?.handoff_type ?? 'none'],
              ['Latest status', latestHandoff?.status ?? 'none'],
              ['Prompt path', latestHandoff?.prompt_path ?? 'none']
            ]}
          />
          <CommandCopyBox command={`devo project handoff-next --project ${selectedProject} --queue ${latestQueue?.queue_id ?? '<queueId>'}`} />
          <CommandCopyBox command={`devo project handoff-task --project ${selectedProject} --task <taskId>`} />
          <CommandCopyBox command={`devo project handoff-batch --project ${selectedProject} --batch ${latestBatch?.batch_id ?? '<batchId>'}`} />
          {onOpenPage ? (
            <button className="link-button detail-link" type="button" onClick={() => onOpenPage('handoffs')}>
              Open Handoff detail
            </button>
          ) : null}
          {onOpenPage ? (
            <button className="link-button detail-link" type="button" onClick={() => onOpenPage('worker-runs')}>
              Open Worker Runs
            </button>
          ) : null}
        </PlanningSection>

        <PlanningSection title="Progress" state={progress}>
          {progress.data ? (
            <>
              <KeyValueList
                items={[
                  ['Project completion', `${progress.data.project_completion_percent.toFixed(1)}%`],
                  ['Backlog readiness', `${progress.data.backlog_readiness_percent.toFixed(1)}%`],
                  ['Blocked', `${progress.data.blocked_percent.toFixed(1)}%`],
                  ['Batch completion', `${progress.data.batch_completion_percent.toFixed(1)}%`],
                  ['Next action', progress.data.next_action]
                ]}
              />
              {progress.data.warnings.length ? (
                <ul className="plain-list compact-list">
                  {progress.data.warnings.map((warning) => (
                    <li key={warning}>{warning}</li>
                  ))}
                </ul>
              ) : null}
            </>
          ) : (
            <EmptyState message="No Progress summary is available yet." />
          )}
          <CommandCopyBox command={`devo project progress --project ${selectedProject}`} />
          {onOpenPage ? (
            <button className="link-button detail-link" type="button" onClick={() => onOpenPage('progress')}>
              Open Progress dashboard
            </button>
          ) : null}
        </PlanningSection>
      </div>
    </section>
  );

  function resetAll() {
    setOverview(emptyOptional<ProjectOverview>());
    setBrief(emptyOptional<ProjectBrief>());
    setBlueprint(emptyOptional<ProjectBlueprint>());
    setBacklog(emptyOptional<ProjectBacklog>());
    setBatches(emptyOptional<ProjectBatchesResponse>());
    setQueues(emptyOptional<ProjectQueuesResponse>());
    setHandoffs(emptyOptional<ProjectHandoffsResponse>());
    setProgress(emptyOptional<ProjectProgress>());
  }

  function setLoadingAll() {
    setOverview({ data: null, loading: true, error: null });
    setBrief({ data: null, loading: true, error: null });
    setBlueprint({ data: null, loading: true, error: null });
    setBacklog({ data: null, loading: true, error: null });
    setBatches({ data: null, loading: true, error: null });
    setQueues({ data: null, loading: true, error: null });
    setHandoffs({ data: null, loading: true, error: null });
    setProgress({ data: null, loading: true, error: null });
  }
}

function PlanningSection<T>({ title, state, children }: { title: string; state: OptionalState<T>; children: ReactNode }) {
  return (
    <SummaryCard title={title}>
      {state.loading ? <LoadingState message={`Loading ${title.toLowerCase()}...`} /> : null}
      {!state.loading && state.error ? <ErrorState message={friendlyOptionalError(state.error)} /> : null}
      {!state.loading && !state.error ? children : null}
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

function pipelineStages(overview: ProjectOverview | null): Array<{ label: string; status: string; summary: string; command: string; state: StageState }> {
  const project = overview?.project_name ?? '<project>';
  return [
    {
      label: 'Project Brief',
      status: overview?.brief_status ?? 'missing',
      summary: 'Distilled project intent and constraints',
      command: `devo project brief-create --project ${project} --title "<title>" --file <brief.md>`
    },
    {
      label: 'Blueprint',
      status: overview?.blueprint_status ?? 'missing',
      summary: `${overview?.blueprint_milestone_count ?? 0} milestones, ${overview?.blueprint_epic_count ?? 0} epics`,
      command: `devo project blueprint-create --project ${project}`
    },
    {
      label: 'Backlog',
      status: overview?.backlog_status ?? 'missing',
      summary: `${overview?.backlog_task_count ?? 0} tasks, ${overview?.backlog_ready_count ?? 0} ready`,
      command: `devo project backlog-create --project ${project}`
    },
    {
      label: 'Batch',
      status: overview?.latest_batch_status ?? 'missing',
      summary: `${overview?.batch_count ?? 0} batches, ${overview?.approved_batch_count ?? 0} approved`,
      command: `devo project batch-suggest --project ${project} --limit 10`
    },
    {
      label: 'Queue',
      status: overview?.latest_queue_status ?? 'missing',
      summary: `${overview?.queue_count ?? 0} queues, current ${overview?.current_queue_item ?? 'none'}`,
      command: `devo project queue-next --project ${project} --queue ${overview?.latest_queue_id ?? '<queueId>'}`
    },
    {
      label: 'Handoff',
      status: overview?.latest_handoff_status ?? 'missing',
      summary: `${overview?.handoff_count ?? 0} handoffs, latest ${overview?.latest_handoff_id ?? 'none'}`,
      command: `devo project handoff-next --project ${project} --queue ${overview?.latest_queue_id ?? '<queueId>'}`
    },
    {
      label: 'Progress',
      status: overview ? 'available' : 'missing',
      summary: `${(overview?.project_completion_percent ?? 0).toFixed(1)}% complete`,
      command: `devo project progress --project ${project}`
    }
  ].map((stage) => ({ ...stage, state: stageState(stage.status) }));
}

function stageState(status: string): StageState {
  if (['approved', 'completed', 'available', 'used'].includes(status)) {
    return 'complete';
  }
  if (['draft', 'ready', 'running', 'in_progress', 'reviewed'].includes(status)) {
    return 'current';
  }
  return 'upcoming';
}

function friendlyOptionalError(error: string): string {
  return error || 'This section is unavailable.';
}

function excerpt(value: string): string {
  const cleaned = value.replace(/\s+/g, ' ').trim();
  if (cleaned.length <= 220) {
    return cleaned || 'none';
  }
  return `${cleaned.slice(0, 220)}...`;
}
