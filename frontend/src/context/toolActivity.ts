import type { ChatMessage } from "../types/chat";

const TOOL_LABELS: Record<string, string> = {
  run_command: "Ran a command",
  web_search: "Searched the web",
  recall_memory: "Searched past conversations",
};

export function toolLabel(name: string | null | undefined): string {
  if (!name) {
    return "Tool";
  }

  return TOOL_LABELS[name] ?? name;
}

function parseArguments(call: ChatMessage): Record<string, unknown> {
  if (!call.tool_arguments) {
    return {};
  }

  try {
    return JSON.parse(call.tool_arguments) as Record<string, unknown>;
  } catch {
    return {};
  }
}

export function describeToolCall(call: ChatMessage): string {
  const args = parseArguments(call);

  if (call.tool_name === "run_command" && typeof args.command === "string") {
    return `Ran \`${args.command}\``;
  }

  if (call.tool_name === "web_search" && typeof args.query === "string") {
    return `Searched the web for "${args.query}"`;
  }

  if (call.tool_name === "recall_memory" && typeof args.query === "string") {
    return `Searched past conversations for "${args.query}"`;
  }

  return toolLabel(call.tool_name);
}

export function isToolResultFailure(result: ChatMessage | null): boolean {
  if (!result) {
    return false;
  }

  if (result.content.startsWith("Error")) {
    return true;
  }

  const exitCodeMatch = result.content.match(/exit_code:\s*(-?\d+)/);

  if (exitCodeMatch) {
    return exitCodeMatch[1] !== "0";
  }

  return false;
}

export type ChatRenderItem =
  | { kind: "message"; message: ChatMessage }
  | { kind: "tool"; call: ChatMessage; result: ChatMessage | null };

export function groupMessagesForDisplay(
  messages: ChatMessage[],
): ChatRenderItem[] {
  const items: ChatRenderItem[] = [];

  for (let i = 0; i < messages.length; i++) {
    const message = messages[i];

    if (message.role === "tool_call") {
      const next = messages[i + 1];

      if (next && next.role === "tool_result") {
        items.push({ kind: "tool", call: message, result: next });
        i += 1;
        continue;
      }

      items.push({ kind: "tool", call: message, result: null });
      continue;
    }

    if (message.role === "tool_result") {
      continue;
    }

    items.push({ kind: "message", message });
  }

  return items;
}
