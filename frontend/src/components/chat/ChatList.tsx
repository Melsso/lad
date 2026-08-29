import { useState } from "react";
import { Link, useParams } from "react-router-dom";

import { updateChatTitle } from "../../services/chat";
import { useChats } from "../../hooks/useChats";

export function ChatList() {
  const { chatId } = useParams();
  const activeChatId = chatId ? Number(chatId) : null;

  const { chats, loading, error, updateLocalChat } = useChats();

  const [editingChatId, setEditingChatId] = useState<number | null>(null);
  const [editTitle, setEditTitle] = useState("");
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState(false);

  function startEditing(id: number, title: string) {
    setEditingChatId(id);
    setEditTitle(title);
    setSaveError(false);
  }

  function cancelEditing() {
    setEditingChatId(null);
    setEditTitle("");
    setSaveError(false);
  }

  async function saveTitle(id: number) {
    const title = editTitle.trim();

    if (!title || saving) {
      return;
    }

    setSaving(true);
    setSaveError(false);

    try {
      await updateChatTitle(id, title);
      updateLocalChat(id, { title });
      setEditingChatId(null);
      setEditTitle("");
    } catch {
      setSaveError(true);
    } finally {
      setSaving(false);
    }
  }

  return (
    <section>
      <div className="mb-3 flex items-center justify-between">
        <h2 className="font-mono text-xs tracking-[0.2em] text-text-dim uppercase">
          Chats
        </h2>

        <Link
          to="/chat"
          aria-label="New chat"
          className="flex h-6 w-6 items-center justify-center rounded border border-line text-text-muted transition hover:border-cyan/60 hover:text-cyan"
        >
          +
        </Link>
      </div>

      {loading && (
        <p className="font-mono text-xs text-text-dim">loading_chats...</p>
      )}

      {error && (
        <p className="font-mono text-xs text-magenta">failed to load chats.</p>
      )}

      {!loading && !error && chats.length === 0 && (
        <p className="font-mono text-xs text-text-dim">no chats yet.</p>
      )}

      {!loading && !error && chats.length > 0 && (
        <ul className="flex flex-col gap-0.5">
          {chats.map((chat) => {
            const isActive = chat.id === activeChatId;
            const isEditing = editingChatId === chat.id;

            return (
              <li key={chat.id} className="group relative">
                <span
                  className={`absolute top-1 bottom-1 left-0 w-0.5 rounded-full transition-colors ${
                    isActive
                      ? "bg-magenta shadow-[0_0_8px_var(--color-magenta)]"
                      : "bg-transparent"
                  }`}
                />

                {isEditing ? (
                  <div className="flex items-center gap-1 py-1 pl-3">
                    <input
                      type="text"
                      value={editTitle}
                      onChange={(event) => setEditTitle(event.target.value)}
                      onKeyDown={(event) => {
                        if (event.key === "Enter") {
                          void saveTitle(chat.id);
                        }

                        if (event.key === "Escape") {
                          cancelEditing();
                        }
                      }}
                      disabled={saving}
                      autoFocus
                      className="min-w-0 flex-1 rounded border border-cyan/50 bg-panel-alt px-2 py-1 text-sm text-text-primary outline-none focus:border-cyan"
                    />

                    <button
                      type="button"
                      onClick={() => void saveTitle(chat.id)}
                      disabled={saving || !editTitle.trim()}
                      className="rounded px-1.5 py-1 text-xs text-cyan transition hover:bg-cyan/10 disabled:opacity-40"
                    >
                      ✓
                    </button>

                    <button
                      type="button"
                      onClick={cancelEditing}
                      disabled={saving}
                      className="rounded px-1.5 py-1 text-xs text-text-muted transition hover:bg-line disabled:opacity-40"
                    >
                      ×
                    </button>
                  </div>
                ) : (
                  <div className="flex items-center gap-1 pl-3">
                    <Link
                      to={`/chat/${chat.id}`}
                      className={`min-w-0 flex-1 truncate rounded py-1.5 text-sm transition-colors ${
                        isActive
                          ? "text-text-primary"
                          : "text-text-muted hover:text-text-primary"
                      }`}
                    >
                      {chat.title}
                    </Link>

                    <button
                      type="button"
                      onClick={() => startEditing(chat.id, chat.title)}
                      aria-label={`Rename ${chat.title}`}
                      className="shrink-0 rounded px-1.5 py-1 text-xs text-text-dim opacity-0 transition group-hover:opacity-100 hover:text-cyan"
                    >
                      ✎
                    </button>
                  </div>
                )}

                {isEditing && saveError && (
                  <p className="pl-3 font-mono text-[10px] text-magenta">
                    rename failed — try again.
                  </p>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
