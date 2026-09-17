# LAD frontend

React + TypeScript + Vite + Tailwind chat UI for LAD, served in production
through nginx (see the [root README](../README.md)) alongside the FastAPI
backend.

## Stack

- **React 19** + **TypeScript** + **Vite**
- **Tailwind CSS v4** — cyberpunk-terminal visual style (monospace,
  tracked-out uppercase labels, magenta/cyan/amber accents)
- **react-markdown** + remark/rehype plugins (GFM, math via KaTeX, line
  breaks) — for rendering assistant replies
- **Vitest** + **Testing Library** — unit tests; **MSW** — mocked network
  layer for integration tests
- **oxlint** + **Prettier**

## Project layout

```
src/
  components/
    chat/      ChatWindow, ChatMessage, ToolActivity, MessageInput,
               ChatModeSelector, ChatList
    layout/    AppLayout, Sidebar
  hooks/       useChatStream (message send/stream/retry state machine),
               useChats (sidebar chat list), useFavicon
  services/    api.ts (fetch wrapper), chat.ts (SSE streaming + CRUD calls)
  types/       shared TypeScript types mirroring the backend's response
               shapes
  context/     chatEvents.ts — cross-component event bus (e.g. sidebar
               reacting to a chat created elsewhere)
               toolActivity.ts — shared tool-call display helpers
               (pretty descriptions, failure detection, message grouping)
  pages/       ChatPage
tests/
  unit_tests/        component/hook/service tests, mocked at the fetch level
  integration_tests/ full component trees against an MSW-mocked backend
```

## Running it

Normally you don't run the frontend on its own — `./start.sh` at the repo
root builds it and serves it through nginx as part of the full stack. See
the [root README](../README.md).

For local UI iteration:

```bash
npm install
npm run dev
```

`npm run dev` starts Vite's dev server on its own port with no backend
attached — there's no dev-server proxy configured for `/api` (see
`vite.config.ts`). It's useful for fast UI-only iteration, but requests to
the backend won't resolve unless you add a proxy or otherwise point it at
a running API. For anything that needs real data, use the full
`./start.sh` stack instead.

## Chat modes and tool-call rendering

A chat's `mode` (`"chat"` or `"agent"`) is fixed for its lifetime. For a
brand-new chat it's tracked locally (`ChatPage`'s `newChatMode` state); for
an existing chat it's fetched via `GET /chat/{chatId}` once, since the
creation-time value isn't otherwise available after a reload.

Tool calls stream in as paired `tool_call`/`tool_result` messages (grouped
into one render item by `context/toolActivity.ts::groupMessagesForDisplay`,
since the backend always writes them as an adjacent pair) and render via
`ToolActivity`:

- **chat mode** — a single compact line: tool label + status
  (running/done/failed). No arguments or result content are ever shown.
- **agent mode** — a bordered card with a prettified one-line description
  of the call (e.g. `` Ran `ls -la` `` instead of raw JSON args) and a
  status badge, expandable on click to show the full result.

## File uploads

The file-picker in `MessageInput` only renders in agent mode. Client-side
validation there (extension allowlist, file count, size limit) mirrors the
backend's `helpers/uploads.py` limits for fast feedback, but the backend
is the actual source of truth — this is a UX nicety, not the real
validation boundary. Messages are sent as `multipart/form-data`
(`chat_id`, `msg`, `files[]`) via `services/chat.ts::streamMessage`.

## Testing

```bash
npm test                 # unit tests
npm run test:integration # integration tests (MSW-mocked backend)
npm run typecheck
npm run lint
```

Both test configs (`vite.config.ts` for unit, `vitest.integration.config.ts`
for integration) are registered as Vitest "projects" in `vitest.config.ts`;
`npm run test:coverage` runs both with coverage.

A couple of easy-to-miss setup details:

- `tests/unit_tests/setup.ts` stubs `Element.prototype.scrollIntoView`,
  which jsdom doesn't implement — any test that renders `ChatWindow`
  (which auto-scrolls on new messages) needs this or it throws.
- Route ordering in `tests/integration_tests/handlers.ts` matters the same
  way it does in the backend: `/api/chat/:chatId` must be registered
  *after* `/api/chat/messages`, or MSW matches the literal path as a
  `chatId` param and swallows it.

## Known limitations

- No dev-server proxy for `/api` — see [Running it](#running-it) above.