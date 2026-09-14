import { useRef, useState } from "react";
import type { ChangeEvent, FormEvent } from "react";

interface MessageInputProps {
  onSend: (content: string, files: File[]) => void;
  isStreaming: boolean;
  mode?: "chat" | "agent";
}

const MAX_FILES = 10;
const MAX_FILE_SIZE_BYTES = 20 * 1024 * 1024;
const ALLOWED_EXTENSIONS = new Set([
  ".py",
  ".js",
  ".jsx",
  ".ts",
  ".tsx",
  ".json",
  ".txt",
  ".md",
  ".csv",
  ".tsv",
  ".yaml",
  ".yml",
  ".toml",
  ".ini",
  ".cfg",
  ".html",
  ".css",
  ".scss",
  ".sh",
  ".sql",
  ".xml",
  ".go",
  ".rs",
  ".java",
  ".c",
  ".h",
  ".cpp",
  ".hpp",
  ".rb",
  ".php",
  ".pdf",
  ".zip",
]);

function extensionOf(filename: string): string {
  const idx = filename.lastIndexOf(".");
  return idx === -1 ? "" : filename.slice(idx).toLowerCase();
}

export function MessageInput({ onSend, isStreaming, mode }: MessageInputProps) {
  const [message, setMessage] = useState("");
  const [files, setFiles] = useState<File[]>([]);
  const [fileError, setFileError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const canAttachFiles = mode === "agent";

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const content = message.trim();
    if (!content || isStreaming) {
      return;
    }

    onSend(content, files);
    setMessage("");
    setFiles([]);
    setFileError(null);
  }

  function handleFilesSelected(event: ChangeEvent<HTMLInputElement>) {
    const selected = Array.from(event.target.files ?? []);
    event.target.value = "";

    if (selected.length === 0) {
      return;
    }

    const combined = [...files, ...selected];

    if (combined.length > MAX_FILES) {
      setFileError(`You can attach up to ${MAX_FILES} files.`);
      return;
    }

    for (const file of selected) {
      const extension = extensionOf(file.name);

      if (!ALLOWED_EXTENSIONS.has(extension)) {
        setFileError(`File type "${extension}" is not supported: ${file.name}`);
        return;
      }

      if (file.size > MAX_FILE_SIZE_BYTES) {
        setFileError(`"${file.name}" exceeds the 20MB size limit.`);
        return;
      }
    }

    setFiles(combined);
    setFileError(null);
  }

  function removeFile(name: string) {
    setFiles((current) => current.filter((file) => file.name !== name));
    setFileError(null);
  }

  return (
    <div className="mx-auto w-full max-w-3xl px-8 pb-6">
      {files.length > 0 && (
        <div className="mb-2 flex flex-wrap gap-2">
          {files.map((file) => (
            <span
              key={file.name}
              className="flex items-center gap-1.5 rounded-md border border-cyan/40 bg-panel-alt px-2 py-1 font-mono text-[11px] text-text-muted"
            >
              {file.name}
              <button
                type="button"
                onClick={() => removeFile(file.name)}
                aria-label={`Remove ${file.name}`}
                className="text-text-dim hover:text-magenta"
              >
                ×
              </button>
            </span>
          ))}
        </div>
      )}

      {fileError && (
        <p className="mb-2 font-mono text-[11px] text-magenta">{fileError}</p>
      )}

      <form
        onSubmit={handleSubmit}
        className={`flex items-center gap-2 rounded-lg border bg-panel-alt px-3 py-2 transition-colors ${
          isStreaming
            ? "border-amber/50"
            : "border-line focus-within:border-cyan/60"
        }`}
      >
        {isStreaming && (
          <span className="h-2 w-2 shrink-0 animate-pulse-glow rounded-full bg-amber shadow-[0_0_10px_var(--color-amber)]" />
        )}

        {canAttachFiles && (
          <>
            <input
              ref={fileInputRef}
              type="file"
              multiple
              onChange={handleFilesSelected}
              className="hidden"
            />
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              disabled={isStreaming}
              aria-label="Attach files"
              className="shrink-0 rounded-md border border-line px-2 py-2 font-mono text-xs text-text-dim transition hover:border-cyan/50 hover:text-cyan disabled:cursor-not-allowed disabled:opacity-60"
            >
              +
            </button>
          </>
        )}

        <input
          type="text"
          value={message}
          onChange={(event) => setMessage(event.target.value)}
          placeholder="Message LAD..."
          disabled={isStreaming}
          className="min-w-0 flex-1 bg-transparent py-2 text-sm text-text-primary outline-none placeholder:text-text-dim disabled:opacity-60"
        />

        <button
          type="submit"
          disabled={!message.trim() || isStreaming}
          className="shrink-0 rounded-md bg-magenta px-4 py-2 font-mono text-xs tracking-wide text-void uppercase transition hover:shadow-[0_0_14px_rgba(255,61,142,0.5)] disabled:cursor-not-allowed disabled:bg-line disabled:text-text-dim disabled:shadow-none"
        >
          {isStreaming ? "..." : "Send"}
        </button>
      </form>
    </div>
  );
}
