# LAD frontend

React + TypeScript + Vite + Tailwind chat UI for LAD, served in production
through nginx (see the [root README](../README.md)) next to the FastAPI backend.

## Stack

- **React 19** + **TypeScript** + **Vite**
- **Tailwind CSS v4**: a cyberpunk-terminal style (monospace, tracked-out
  uppercase labels, magenta/cyan/amber accents)
- **react-markdown** with remark/rehype plugins (GFM, math via KaTeX, line
  breaks) for rendering replies
- **Vitest** + **Testing Library** for unit tests, **MSW** for the mocked
  network layer in integration tests
- **oxlint** + **Prettier**

## Project layout

```
src/
  components/
    chat/      ChatWindow, ChatMessage, ToolActivity, MessageInput,
               ChatModeSelector, ChatList
    layout/    AppLayout, Sidebar
  hooks/       useChatStream (send/stream/retry state machine), useChats
               (sidebar chat list), useFavicon (processing/ready icons)
  services/    api.ts (fetch wrapper), chat.ts (SSE streaming + CRUD calls)
  types/       shared TypeScript types mirroring the backend responses
  lib/         chatEvents.ts (event bus so the sidebar reacts to chats
               created elsewhere), toolActivity.ts (tool-call display
               helpers: descriptions, failure detection, message grouping)
  pages/       ChatPage
tests/
  unit_tests/         component/hook/service tests, mocked at the fetch level
  integration_tests/  full component trees against an MSW-mocked backend
```

## Running it

Normally you don't run the frontend alone: `./start.sh` at the repo root
builds it and serves it through nginx as part of the full stack.

For UI iteration with hot reload, start the stack first, then:

```bash
npm install
npm run dev
```

The Vite dev server proxies `/api` to `http://localhost:8000` (the running
stack's nginx), so it works against the real backend.

## Chat modes and tool-call rendering

A chat's `mode` (`"chat"` or `"agent"`) is fixed for its lifetime. For a new
chat it is tracked locally (`ChatPage`'s `newChatMode`); for an existing chat
it is fetched once with `GET /chat/{chatId}`.

Tool calls stream in as `tool_call` / `tool_result` messages, grouped into one
render item by `lib/toolActivity.ts::groupMessagesForDisplay` (the backend
always writes them as an adjacent pair), and render through `ToolActivity`:

- **chat mode**: one compact line with the tool label and a status
  (running/done/failed). Arguments and result content are never shown.
- **agent mode**: a bordered card with a readable one-line description of the
  call (for example ``Ran `ls -la` `` instead of raw JSON) and a status badge,
  expandable to show the full result.

## File uploads

The file picker in `MessageInput` only renders in agent mode, and the backend
rejects uploads for chat-mode chats. Client-side checks (extension allowlist,
file count, size limit) mirror the backend's `helpers/uploads.py` for fast
feedback, but the backend is the real validation boundary. Selecting a file
with the same name as one already attached replaces it, matching the backend's
overwrite behavior. Messages are sent as `multipart/form-data` (`chat_id`,
`msg`, `files[]`) through `services/chat.ts::streamMessage`.

## Testing

```bash
npm test                  # unit tests
npm run test:integration  # integration tests (MSW-mocked backend)
npm run typecheck
npm run lint
```

Both configs (`vite.config.ts` for unit, `vitest.integration.config.ts` for
integration) are registered as Vitest projects in `vitest.config.ts`;
`npm run test:coverage` runs both with coverage.

Two easy-to-miss details:

- `tests/unit_tests/setup.ts` stubs `Element.prototype.scrollIntoView`, which
  jsdom doesn't implement. Any test that renders `ChatWindow` (which
  auto-scrolls on new messages) needs it.
- Route order in `tests/integration_tests/handlers.ts` matters the same way as
  in the backend: `/api/chat/:chatId` must be registered *after*
  `/api/chat/messages`, or MSW matches the literal path as a `chatId`.