import { useState } from "react";

import type { ChatMessage } from "../../types/chat";
import {
  describeToolCall,
  isToolResultFailure,
  toolLabel,
} from "../../context/toolActivity";

interface ToolActivityProps {
  call: ChatMessage;
  result: ChatMessage | null;
  mode: "chat" | "agent";
}

export function ToolActivity({ call, result, mode }: ToolActivityProps) {
  const [expanded, setExpanded] = useState(false);

  const running = result === null;
  const failed = isToolResultFailure(result);
  const statusLabel = running ? "running" : failed ? "failed" : "done";
  const dotColor = running ? "bg-amber" : failed ? "bg-magenta" : "bg-cyan";

  if (mode !== "agent") {
    return (
      <div className="flex items-center gap-2 font-mono text-[11px] text-text-dim">
        <span
          className={`h-1.5 w-1.5 shrink-0 rounded-full ${dotColor} ${
            running ? "animate-pulse-glow" : ""
          }`}
        />
        <span>{toolLabel(call.tool_name)}</span>
        <span className="text-text-dim/70">— {statusLabel}</span>
      </div>
    );
  }

  return (
    <div className="max-w-[75ch]">
      <button
        type="button"
        onClick={() => result && setExpanded((current) => !current)}
        disabled={!result}
        className="flex w-full items-center gap-2 rounded-md border border-line bg-panel-alt/60 px-3 py-2 text-left font-mono text-[11px] transition hover:border-cyan/40 disabled:cursor-default disabled:hover:border-line"
      >
        <span
          className={`h-1.5 w-1.5 shrink-0 rounded-full ${dotColor} ${
            running ? "animate-pulse-glow" : ""
          }`}
        />
        <span className="flex-1 truncate text-text-muted">
          {describeToolCall(call)}
        </span>
        <span className={failed ? "text-magenta" : "text-text-dim"}>
          {statusLabel}
        </span>
        {result && (
          <span
            className={`text-text-dim transition-transform ${
              expanded ? "rotate-90" : ""
            }`}
          >
            ›
          </span>
        )}
      </button>

      {expanded && result && (
        <pre className="mt-1 max-h-64 overflow-auto rounded-md border border-line bg-panel px-3 py-2 font-mono text-[11px] whitespace-pre-wrap text-text-dim">
          {result.content}
        </pre>
      )}
    </div>
  );
}
