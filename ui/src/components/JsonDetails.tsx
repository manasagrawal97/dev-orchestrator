interface JsonDetailsProps {
  data: unknown;
  label?: string;
}

export function JsonDetails({ data, label = 'View JSON' }: JsonDetailsProps) {
  return (
    <details className="json-details">
      <summary>{label}</summary>
      <pre>{JSON.stringify(data, null, 2)}</pre>
    </details>
  );
}
