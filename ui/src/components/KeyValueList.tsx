interface KeyValueListProps {
  items: Array<[string, unknown]>;
}

export function KeyValueList({ items }: KeyValueListProps) {
  return (
    <dl className="key-value-list">
      {items.map(([label, value]) => (
        <div key={label}>
          <dt>{label}</dt>
          <dd>{formatValue(value)}</dd>
        </div>
      ))}
    </dl>
  );
}

function formatValue(value: unknown): string {
  if (value === null || value === undefined || value === '') {
    return 'none';
  }
  if (typeof value === 'boolean') {
    return value ? 'yes' : 'no';
  }
  if (Array.isArray(value)) {
    return value.length ? value.join(', ') : 'none';
  }
  if (typeof value === 'object') {
    return JSON.stringify(value);
  }
  return String(value);
}
