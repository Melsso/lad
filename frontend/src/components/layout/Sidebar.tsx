import { Link } from "react-router-dom";

import { ChatList } from "../chat/ChatList";
import { TranscriptionList } from "../transcription/TranscriptionList";

export function Sidebar() {
  return (
    <aside className="relative flex h-full w-72 shrink-0 flex-col overflow-y-auto border-r border-line bg-panel px-5 py-6">
      <div className="pointer-events-none absolute top-0 right-0 left-0 h-px overflow-hidden">
        <div className="h-px w-1/3 animate-scan bg-gradient-to-r from-transparent via-magenta to-transparent" />
      </div>

      <div className="mb-8">
        <Link to="/chat" className="group inline-block">
          <h1 className="font-display text-xl font-semibold tracking-[0.15em] text-text-primary transition-colors group-hover:text-cyan">
            LAD<span className="text-magenta group-hover:text-cyan">_</span>
          </h1>
          <p className="mt-1 font-mono text-[10px] tracking-[0.25em] text-text-dim uppercase transition-colors group-hover:text-text-muted">
            local ai daemon
          </p>
        </Link>
      </div>

      <div className="mb-8">
        <ChatList />
      </div>

      <div>
        <TranscriptionList />
      </div>
    </aside>
  );
}
