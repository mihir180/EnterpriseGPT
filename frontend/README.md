# EnterpriseGPT — Frontend (Phase 3)

Enterprise UI for the EnterpriseGPT RAG assistant: auth, dashboard, chat,
and document management, built against the Phase 1 + Phase 2 backend API.

## Stack

- Next.js 14 (App Router) + TypeScript
- Tailwind CSS (no component library — hand-styled to match the API's
  actual shape rather than a generic template)
- `react-markdown` + `remark-gfm` + `react-syntax-highlighter` for
  rendering assistant answers (Markdown, tables, code blocks)
- Auth/session state via a small React Context (`lib/auth-context.tsx`)
  — no extra data-fetching library; the API surface is small enough that
  plain `fetch` + `useState`/`useEffect` stays readable. TanStack Query
  would be a reasonable upgrade if Phase 4's analytics dashboard adds
  a lot more cached, cross-page data.

## Folder structure

```
frontend/
  src/
    app/
      login/          # /login
      register/       # /register
      dashboard/       # /dashboard — stats, recent docs, recent Q&A
      chat/            # /chat — ChatGPT-style Q&A UI + history sidebar
      documents/        # /documents — upload (admin), list, status, delete
      layout.tsx        # wraps app in AuthProvider
      page.tsx           # redirects to /dashboard or /login
      globals.css
    components/
      Navbar.tsx
      ProtectedRoute.tsx        # route guard, optional adminOnly
      ChatMessageBubble.tsx     # markdown + code highlighting + citations
      ChatHistorySidebar.tsx
    lib/
      api.ts               # typed fetch client for every backend endpoint
      auth-context.tsx      # login/register/logout/current-user state
    types/
      index.ts               # mirrors backend/app/schemas/*.py exactly
  package.json
  tailwind.config.ts
  next.config.js
  .env.local.example
```

## Why this structure

- **`types/index.ts` mirrors the Pydantic schemas field-for-field**
  (`UserRead`, `DocumentRead`, `AskRequest`/`AskResponse`,
  `ChatQueryRead`, etc.) so the frontend can never silently drift from
  the API contract — if a backend field is renamed, TypeScript breaks
  at compile time instead of failing at runtime.
- **`lib/api.ts` is the only place that knows about HTTP.** Every
  component calls a typed function (`askQuestion`, `listDocuments`,
  ...) — no raw `fetch` scattered around, no duplicated auth-header
  logic, and it's the single place to add retry/refresh logic later.
- **JWT is stored in `localStorage`** and attached via `Authorization:
  Bearer` on every request in `lib/api.ts`. Simple and fine for a
  demo/Phase 3; Phase 5 adds refresh tokens, at which point this is the
  only file that needs to change.
- **`ProtectedRoute`** is a thin client-side guard (redirects to
  `/login` if unauthenticated, or `/dashboard` if a non-admin hits an
  `adminOnly` page like uploading documents). It's intentionally
  simple — real authorization is still enforced server-side by FastAPI
  (`get_current_user` / `get_current_active_admin`); this only avoids
  flashing UI the user can't use.
- **Documents page polls `GET /documents` every 3s** while any document
  is `uploaded`/`processing`, so upload status updates without a manual
  refresh. This matches how Phase 1's background-task pipeline reports
  status (no websocket yet) — noted in the backend README as a Phase 5
  upgrade path, and the polling here is written so it's a one-line
  swap once that exists.

## Known Phase 3 simplifications (by design)

- **Chat is not token-streamed.** `POST /api/v1/chat/ask` returns the
  full answer in one JSON response (see `rag_service.py` /
  `chat.py`), so the UI shows a typing indicator while waiting, then
  renders the complete answer — not a real SSE/token stream. Wiring
  true streaming needs a backend change (a streaming response from
  `llm_service`) before the frontend can do anything with it.
- **Document permissions aren't enforced in the UI** beyond
  admin-vs-employee (upload/delete require admin). Per-document ACLs
  are a Phase 4 feature; once that lands, `documents/page.tsx` and
  `chat/page.tsx` (its optional `document_ids` filter) are the places
  to surface it.
- **No refresh tokens.** A 401 from any request clears the stored
  token and the user is bounced to `/login` — acceptable until Phase 5
  adds refresh-token support server-side.

## Setup

```bash
cd frontend
npm install
cp .env.local.example .env.local
# edit .env.local if your backend isn't on http://localhost:8000

npm run dev
```

Runs on `http://localhost:3000`. Make sure the Phase 1/2 backend is
running first (`docker compose up` in `backend/`, or `uvicorn
app.main:app --reload`) and that `CORS_ORIGINS` in the backend's `.env`
includes `http://localhost:3000` (it does by default).

The first account you register becomes `admin` (backend rule); every
account after that is `employee`.

## Verified

`npm run build` (Next.js production build, TypeScript strict mode) —
compiles clean, all 7 routes statically generated, no type errors.
