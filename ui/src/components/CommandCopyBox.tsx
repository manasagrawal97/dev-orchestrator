interface CommandCopyBoxProps {
  command: string;
}

export function CommandCopyBox({ command }: CommandCopyBoxProps) {
  async function copyCommand() {
    await navigator.clipboard.writeText(command);
  }

  return (
    <div className="command-copy">
      <code>{command}</code>
      <button type="button" onClick={copyCommand}>
        Copy
      </button>
    </div>
  );
}
