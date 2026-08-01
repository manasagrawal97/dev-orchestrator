import { useEffect, useMemo, useState } from 'react';
import { devoApi } from '../api/client';
import { CommandCopyBox } from '../components/CommandCopyBox';
import { KeyValueList } from '../components/KeyValueList';
import { EmptyState, ErrorState, LoadingState } from '../components/SectionState';
import { StatusBadge } from '../components/StatusBadge';
import { SummaryCard } from '../components/SummaryCard';
import type { ExecutionQueue, ProjectProgress, ProjectQueuesResponse, QueueItem } from '../types/devo';

interface QueuesPageProps {
  selectedProject: string | null;
}

interface OptionalState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
}

const emptyOptional = <T,>(): OptionalState<T> => ({ data: null, loading: false, error: null });

export function QueuesPage({ selectedProject }: QueuesPageProps) {
  const [queues, setQueues] = useState<OptionalState<ProjectQueuesResponse>>(emptyOptional);
  const [progress, setProgress] = useState<OptionalState<ProjectProgress>>(emptyOptional);
  const [selectedQueueId, setSelectedQueueId] = useState<string | null>(null);
  const [selectedQueue, setSelectedQueue] = useState<OptionalState<ExecutionQueue>>(emptyOptional);

  useEffect(() => {
    if (!selectedProject) {
      setQueues(emptyOptional<ProjectQueuesResponse>());
      setProgress(emptyOptional<ProjectProgress>());
      setSelectedQueueId(null);
      setSelectedQueue(emptyOptional<ExecutionQueue>());
      return;
    }

    let active = true;
    setQueues({ data: null, loading: true, error: null });
    setProgress({ data: null, loading: true, error: null });
    setSelectedQueue(emptyOptional<ExecutionQueue>());

    loadOptional(devoApi.getProjectQueues(selectedProject)).then((state) => {
      if (!active) {
        return;
      }
      setQueues(state);
      setSelectedQueueId((current) => current ?? state.data?.queues[0]?.queue_id ?? null);
    });
    loadOptional(devoApi.getProjectProgress(selectedProject)).then((state) => active && setProgress(state));

    return () => {
      active = false;
    };
  }, [selectedProject]);

  useEffect(() => {
    if (!selectedProject || !selectedQueueId) {
      setSelectedQueue(emptyOptional<ExecutionQueue>());
      return;
    }

    let active = true;
    setSelectedQueue({ data: null, loading: true, error: null });
    loadOptional(devoApi.getProjectQueue(selectedProject, selectedQueueId)).then((state) => active && setSelectedQueue(state));
    return () => {
      active = false;
    };
  }, [selectedProject, selectedQueueId]);

  const queueList = queues.data?.queues ?? [];
  const latestQueue = queueList[0] ?? null;
  const selected = selectedQueue.data ?? queueList.find((queue) => queue.queue_id === selectedQueueId) ?? null;
  const totals = useMemo(
    () =>
      queueList.reduce(
        (acc, queue) => ({
          pending: acc.pending + (queue.pending_count ?? 0),
          completed: acc.completed + (queue.completed_count ?? 0),
          blocked: acc.blocked + (queue.blocked_count ?? 0),
          failed: acc.failed + (queue.failed_count ?? 0)
        }),
        { pending: 0, completed: 0, blocked: 0, failed: 0 }
      ),
    [queueList]
  );

  if (!selectedProject) {
    return <p className="muted">Select a project to view execution queues.</p>;
  }

  return (
    <section>
      <div className="section-heading">
        <h2>Queues</h2>
        <p>{selectedProject}</p>
      </div>

      <div className="summary-grid">
        <SummaryCard title="Queues" value={queues.loading ? 'Loading' : queues.data?.count ?? 0} />
        <SummaryCard title="Latest queue" value={latestQueue?.queue_id ?? 'none'} />
        <SummaryCard title="Latest status" value={latestQueue ? <StatusBadge status={latestQueue.status} /> : 'none'} />
        <SummaryCard title="Current item" value={latestQueue?.current_item_id ?? 'none'} />
      </div>

      <div className="summary-grid detail-panel">
        <SummaryCard title="Pending" value={totals.pending} />
        <SummaryCard title="Completed" value={totals.completed} />
        <SummaryCard title="Blocked" value={totals.blocked} />
        <SummaryCard title="Failed" value={totals.failed} />
      </div>

      {queues.loading ? <LoadingState message="Loading queues..." /> : null}
      {queues.error ? <ErrorState message={queues.error} /> : null}
      {!queues.loading && !queues.error && !queueList.length ? (
        <EmptyState message="No execution queue artifacts are available yet.">
          <CommandCopyBox command={`devo project queue-create --project ${selectedProject} --batch <batchId>`} />
        </EmptyState>
      ) : null}

      {queueList.length ? (
        <>
          <div className="two-column">
            <section className="panel">
              <h3>Queue List</h3>
              <div className="list-stack">
                {queueList.map((queue) => (
                  <button
                    className={queue.queue_id === selectedQueueId ? 'work-row selected-row' : 'work-row'}
                    key={queue.queue_id}
                    type="button"
                    onClick={() => setSelectedQueueId(queue.queue_id)}
                  >
                    <span>
                      {queue.queue_id}: {queue.title}
                    </span>
                    <small>
                      batch {queue.source_batch_id} | {queue.status} | {queue.item_count} items
                    </small>
                    <small>
                      {queue.pending_count} pending, {queue.running_count ?? 0} running, {queue.completed_count} completed, {queue.blocked_count} blocked
                    </small>
                    <small>{queue.pause_reason ? `Paused: ${queue.pause_reason}` : queue.resume_hint ?? 'No pause reason recorded.'}</small>
                  </button>
                ))}
              </div>
            </section>

            <section className="panel">
              <h3>Selected Queue</h3>
              {selectedQueue.loading ? <LoadingState message="Loading queue detail..." /> : null}
              {selectedQueue.error ? <ErrorState message={selectedQueue.error} /> : null}
              {selected ? <QueueDetail queue={selected} /> : <p className="muted compact">Select a queue to inspect details.</p>}
            </section>
          </div>

          <SummaryCard title="CLI Guidance">
            <CommandCopyBox command={`devo project queue-list --project ${selectedProject}`} />
            <CommandCopyBox command={`devo project queue-show --project ${selectedProject} --queue ${selectedQueueId ?? '<queueId>'}`} />
            <CommandCopyBox command={`devo project queue-create --project ${selectedProject} --batch ${selected?.source_batch_id ?? '<batchId>'}`} />
            <CommandCopyBox command={`devo project queue-start --project ${selectedProject} --queue ${selectedQueueId ?? '<queueId>'}`} />
            <CommandCopyBox command={`devo project queue-next --project ${selectedProject} --queue ${selectedQueueId ?? '<queueId>'}`} />
            <CommandCopyBox command={`devo project queue-pause --project ${selectedProject} --queue ${selectedQueueId ?? '<queueId>'} --reason usage_limit --note "<note>"`} />
            <CommandCopyBox command={`devo project queue-resume --project ${selectedProject} --queue ${selectedQueueId ?? '<queueId>'}`} />
          </SummaryCard>
        </>
      ) : null}

      {progress.loading ? <LoadingState message="Loading queue progress..." /> : null}
      {progress.error ? <ErrorState message={progress.error} /> : null}
    </section>
  );
}

function QueueDetail({ queue }: { queue: ExecutionQueue }) {
  return (
    <div className="task-detail">
      <div className="detail-card-title">
        <strong>
          {queue.queue_id}: {queue.title}
        </strong>
        <StatusBadge status={queue.status} />
      </div>
      <KeyValueList
        items={[
          ['Source batch', queue.source_batch_id],
          ['Items', queue.item_count],
          ['Pending', queue.pending_count],
          ['Running', queue.running_count],
          ['Completed', queue.completed_count],
          ['Blocked', queue.blocked_count],
          ['Failed', queue.failed_count],
          ['Current item', queue.current_item_id ?? 'none'],
          ['Pause reason', queue.pause_reason ?? 'none'],
          ['Resume hint', queue.resume_hint ?? 'none']
        ]}
      />
      <div className="detail-list">
        <strong>Items</strong>
        {queue.items.length ? (
          <div className="detail-card-grid">
            {queue.items.map((item) => (
              <QueueItemCard key={item.item_id} item={item} />
            ))}
          </div>
        ) : (
          <p className="muted compact">No queue items recorded.</p>
        )}
      </div>
    </div>
  );
}

function QueueItemCard({ item }: { item: QueueItem }) {
  return (
    <div className="detail-card">
      <div className="detail-card-title">
        <strong>
          {item.item_id}: {item.title}
        </strong>
        <StatusBadge status={item.status} />
      </div>
      <KeyValueList
        items={[
          ['Task', item.task_id],
          ['Lane', item.lane],
          ['Risk', item.risk_level],
          ['Batch', item.batch_id],
          ['Dependencies', item.dependencies],
          ['Started', item.started_at ?? 'none'],
          ['Completed', item.completed_at ?? 'none']
        ]}
      />
      <DetailList title="Acceptance Criteria" items={item.acceptance_criteria} />
      <DetailList title="Validation Expectations" items={item.validation_expectations} />
      <DetailList title="Notes" items={item.notes} />
    </div>
  );
}

function DetailList({ title, items }: { title: string; items: string[] }) {
  return (
    <div className="detail-list">
      <strong>{title}</strong>
      {items.length ? (
        <ul className="plain-list compact-list">
          {items.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      ) : (
        <p className="muted compact">No items recorded.</p>
      )}
    </div>
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
