import type { StatusTone } from '../types/devo';

interface StatusBadgeProps {
  status: string | boolean | null | undefined;
}

const KNOWN_TONES = new Set(['OK', 'WARN', 'FAIL', 'SKIP', 'PENDING', 'READY']);

export function StatusBadge({ status }: StatusBadgeProps) {
  const label = typeof status === 'boolean' ? (status ? 'OK' : 'WARN') : status || 'unknown';
  const normalized = label.toString().toUpperCase();
  const tone: StatusTone = KNOWN_TONES.has(normalized) ? (normalized as StatusTone) : normalized.includes('FAIL') ? 'FAIL' : 'unknown';

  return <span className={`status-badge status-${tone.toLowerCase()}`}>{label}</span>;
}
