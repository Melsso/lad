import { useState } from "react";
import { Link } from "react-router-dom";

import { updateChatTitle } from "../../services/chat";
import { useChats } from "../../hooks/useChats";

export function ChatList() {
  const { chats, loading, error } = useChats();

  const [editingChatId, setEditingChatId] = useState<number | null>(null);
  const [editTitle, setEditTitle] = useState("");
  const [saving, setSaving] = useState(false);

  function startEditing(chatId: number, title: string) {
    setEditingChatId(chatId);
    setEditTitle(title);
  }

  function cancelEditing() {
    setEditingChatId(null);
    setEditTitle("");
  }

  async function saveTitle(chatId: number) {
    const title = editTitle.trim();

    if (!title || saving) {
      return;
    }

    setSaving(true);

    try {
      await updateChatTitle(chatId, title);
      window.location.reload();
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="chat-list">
      <div className="sidebar-section-header">
        <h2>Chats</h2>

        <button type="button">+</button>
      </div>

      {loading && <p>Loading...</p>}

      {error && <p>Failed to load chats.</p>}

      {!loading && !error && chats.length === 0 && <p>No chats yet.</p>}

      {!loading && !error && chats.length > 0 && (
        <ul>
          {chats.map((chat) => (
            <li key={chat.id}>
              {editingChatId === chat.id ? (
                <div>
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
                  />

                  <button
                    type="button"
                    onClick={() => void saveTitle(chat.id)}
                    disabled={saving || !editTitle.trim()}
                  >
                    ✓
                  </button>

                  <button
                    type="button"
                    onClick={cancelEditing}
                    disabled={saving}
                  >
                    ×
                  </button>
                </div>
              ) : (
                <div>
                  <Link to={`/chat/${chat.id}`}>{chat.title}</Link>

                  <button
                    type="button"
                    onClick={() => startEditing(chat.id, chat.title)}
                    aria-label={`Edit ${chat.title}`}
                  >
                    ✎
                  </button>
                </div>
              )}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
