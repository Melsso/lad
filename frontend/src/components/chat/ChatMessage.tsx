import ReactMarkdown from "react-markdown";
import type { Components } from "react-markdown";
import rehypeKatex from "rehype-katex";
import remarkBreaks from "remark-breaks";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";

import type { ChatMessage as ChatMessageType } from "../../types/chat";

interface ChatMessageProps {
  message: ChatMessageType;
  pending?: boolean;
}

const markdownComponents: Components = {
  h1: ({ children }) => (
    <h1 className="mt-4 mb-2 border-b border-line pb-1 font-display text-lg font-semibold tracking-wide text-text-primary first:mt-0">
      {children}
    </h1>
  ),
  h2: ({ children }) => (
    <h2 className="mt-4 mb-2 font-display text-base font-semibold tracking-wide text-text-primary first:mt-0">
      {children}
    </h2>
  ),
  h3: ({ children }) => (
    <h3 className="mt-3 mb-1.5 font-display text-sm font-semibold tracking-wide text-text-primary first:mt-0">
      {children}
    </h3>
  ),
  p: ({ children }) => (
    <p className="mb-3 leading-relaxed last:mb-0">{children}</p>
  ),
  strong: ({ children }) => (
    <strong className="font-semibold text-text-primary">{children}</strong>
  ),
  em: ({ children }) => (
    <em className="italic text-text-primary">{children}</em>
  ),
  a: ({ children, href }) => (
    <a
      href={href}
      target="_blank"
      rel="noreferrer"
      className="text-cyan underline decoration-cyan/40 underline-offset-2 hover:decoration-cyan"
    >
      {children}
    </a>
  ),
  ul: ({ children }) => (
    <ul className="mb-3 list-disc space-y-1 pl-5 last:mb-0">{children}</ul>
  ),
  ol: ({ children }) => (
    <ol className="mb-3 list-decimal space-y-1 pl-5 last:mb-0">{children}</ol>
  ),
  li: ({ children }) => <li className="leading-relaxed">{children}</li>,
  blockquote: ({ children }) => (
    <blockquote className="mb-3 border-l-2 border-magenta/50 pl-3 text-text-muted italic last:mb-0">
      {children}
    </blockquote>
  ),
  hr: () => <hr className="my-4 border-line" />,
  code: ({ className, children }) => {
    const isBlock = /language-/.test(className ?? "");

    if (isBlock) {
      return (
        <code className={`font-mono text-xs ${className ?? ""}`}>
          {children}
        </code>
      );
    }

    return (
      <code className="rounded bg-panel px-1.5 py-0.5 font-mono text-xs text-amber">
        {children}
      </code>
    );
  },
  pre: ({ children }) => (
    <pre className="mb-3 overflow-x-auto rounded-md border border-line bg-panel p-3 last:mb-0">
      {children}
    </pre>
  ),
  table: ({ children }) => (
    <div className="mb-3 overflow-x-auto last:mb-0">
      <table className="w-full border-collapse text-xs">{children}</table>
    </div>
  ),
  th: ({ children }) => (
    <th className="border-b border-line px-2 py-1.5 text-left font-mono text-[10px] tracking-[0.15em] text-text-dim uppercase">
      {children}
    </th>
  ),
  td: ({ children }) => (
    <td className="border-b border-line/50 px-2 py-1.5 align-top">
      {children}
    </td>
  ),
};

export function ChatMessage({ message, pending }: ChatMessageProps) {
  const isUser = message.role === "user";

  if (message.role === "tool_call" || message.role === "tool_result") {
    const isCall = message.role === "tool_call";

    let detail = "";
    if (isCall && message.tool_arguments) {
      try {
        detail = JSON.stringify(JSON.parse(message.tool_arguments));
      } catch {
        detail = message.tool_arguments;
      }
    } else if (!isCall) {
      detail = message.content;
    }

    return (
      <div className="flex items-center gap-2 font-mono text-[11px] text-text-dim">
        <span className="text-cyan">{isCall ? "→" : "←"}</span>
        <span className="text-amber">{message.tool_name}</span>
        {detail && <span className="truncate text-text-dim">{detail}</span>}
      </div>
    );
  }

  return (
    <article
      className={`flex flex-col ${isUser ? "items-end" : "items-start"}`}
    >
      <div className="mb-1 font-mono text-[10px] tracking-[0.2em] text-text-dim uppercase">
        {message.role}
      </div>

      <div
        className={`max-w-[75ch] min-w-0 rounded-lg px-4 py-3 text-sm ${
          isUser
            ? "border border-magenta/30 bg-panel-alt text-text-primary"
            : "border-l-2 border-cyan/40 bg-panel-alt/60 text-text-primary"
        }`}
      >
        {pending && !message.content ? (
          <span className="inline-flex h-4 items-center">
            <span className="h-2 w-2 animate-pulse-glow rounded-full bg-amber shadow-[0_0_10px_var(--color-amber)]" />
          </span>
        ) : (
          <>
            <ReactMarkdown
              remarkPlugins={[remarkGfm, remarkMath, remarkBreaks]}
              rehypePlugins={[rehypeKatex]}
              components={markdownComponents}
            >
              {message.content}
            </ReactMarkdown>

            {pending && (
              <span className="ml-0.5 inline-block h-3.5 w-1.5 translate-y-0.5 animate-blink bg-amber" />
            )}
          </>
        )}

        {message.attached_files && message.attached_files.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-1.5 border-t border-line/50 pt-2">
            {message.attached_files.map((filename) => (
              <span
                key={filename}
                className="rounded-md border border-cyan/30 bg-panel px-2 py-0.5 font-mono text-[10px] text-text-dim"
              >
                {filename}
              </span>
            ))}
          </div>
        )}
      </div>
    </article>
  );
}
