interface ChatModeSelectorProps {
  mode: "chat" | "agent";
  onChange: (mode: "chat" | "agent") => void;
  disabled?: boolean;
}

export function ChatModeSelector({
  mode,
  onChange,
  disabled,
}: ChatModeSelectorProps) {
  return (
    <div className="mx-auto flex w-full max-w-3xl items-center justify-center gap-2 px-8 pb-3">
      <button
        type="button"
        disabled={disabled}
        onClick={() => onChange("chat")}
        aria-pressed={mode === "chat"}
        className={`rounded-md border px-3 py-1.5 font-mono text-xs uppercase tracking-wide transition disabled:cursor-not-allowed disabled:opacity-50 ${
          mode === "chat"
            ? "border-cyan/60 text-cyan"
            : "border-line text-text-dim hover:text-text-muted"
        }`}
      >
        Chat
      </button>
      <button
        type="button"
        disabled={disabled}
        onClick={() => onChange("agent")}
        aria-pressed={mode === "agent"}
        className={`rounded-md border px-3 py-1.5 font-mono text-xs uppercase tracking-wide transition disabled:cursor-not-allowed disabled:opacity-50 ${
          mode === "agent"
            ? "border-amber/60 text-amber"
            : "border-line text-text-dim hover:text-text-muted"
        }`}
      >
        Agent
      </button>
    </div>
  );
}
