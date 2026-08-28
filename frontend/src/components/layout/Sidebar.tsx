import { ChatList } from "../chat/ChatList";
import { TranscriptionList } from "../transcription/TranscriptionList";

export function Sidebar() {
  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <h1>LAD</h1>
      </div>

      <div className="sidebar-section">
        <ChatList />
      </div>

      <div className="sidebar-section">
        <TranscriptionList />
      </div>
    </aside>
  );
}
