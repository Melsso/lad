import { Link } from "react-router-dom";

import { useChats } from "../../hooks/useChats";

export function ChatList() {
  const { chats, loading, error } = useChats();

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
              <Link to={`/chat/${chat.id}`}>{chat.title}</Link>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
