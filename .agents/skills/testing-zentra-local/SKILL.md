---
name: testing-zentra-local
description: How to run and test the Zentra (gdrive-rag-system) FastAPI backend + React/Vite frontend locally, including auth-check / cold-start scenarios without Google, Postgres or Groq credentials.
---

# Testing Zentra locally

## Services

Backend (works with NO DATABASE_URL / GROQ_API_KEY — heavy services are lazy, the warmup
thread just logs `Warmup failed (ValueError): DATABASE_URL is not configured.`):

```bash
cd backend
env -u DATABASE_URL -u GROQ_API_KEY \
  SESSION_SECRET=testsecret ENVIRONMENT=development \
  SESSION_COOKIE_SAMESITE=lax SESSION_COOKIE_SECURE=false \
  FRONTEND_URL=http://localhost:5173 \
  ~/venv-zentra/bin/python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

`SESSION_COOKIE_SAMESITE=lax` / `SESSION_COOKIE_SECURE=false` matter: `config.py` defaults to
`none`/`true`, which prevents the session cookie from being stored over plain http://localhost.

Frontend (Node 22 is required; Node 20.18 breaks the vite build):

```bash
cd frontend
PATH=$HOME/.nvm/versions/node/v22.12.0/bin:$PATH npm run dev -- --host 127.0.0.1 --port 5173
```

`src/services/api.js` targets `http://localhost:8000` automatically when the page host is
localhost/127.0.0.1, so no frontend .env is needed for local testing.

Tip: when starting servers from an agent shell tool, use `(setsid ... > /tmp/log 2>&1 < /dev/null &)`
— plain `nohup cmd &` frequently gets killed when the tool call returns.

## Unauthenticated flows you can test without Google OAuth

- `GET /api/auth/me` returns `{"authenticated": false}` (200) with no session.
- `/`, `/dashboard`, `/analyze`, `/chat` all redirect to `/login` when unauthenticated
  (`ProtectedRoute` in `frontend/src/App.jsx`).
- Real Google login / Drive ingestion cannot be tested without GOOGLE_CLIENT_ID,
  GOOGLE_CLIENT_SECRET, DATABASE_URL and GROQ_API_KEY.

## Simulating a cold-start / sleeping backend (App.jsx retry + "waking up" hint)

`App.jsx` retries `/api/auth/me` up to 4 times, only on timeout (15s, `ECONNABORTED`) or network
error, and shows "The server is waking up after being idle." after 4s.

Do NOT simply stop the backend: a closed port gives an instant `ECONNREFUSED`, so all 4 attempts
burn within milliseconds and the app falls through the error path — this does not exercise the
timeout/retry-success path.

Instead, put a TCP proxy on :8000 that accepts connections and holds them open with no response
while a flag file is absent, and forwards to the real backend (started on :8001) once the flag
exists. Load the page, screenshot at ~2s (no hint) and ~6s (hint visible), then `touch` the flag;
attempt 1 times out at 15s and attempt 2 succeeds, landing on `/login` with no manual reload.
Verify with the browser console: `Auth check attempt 1 failed (ECONNABORTED)...` followed by a
successful `API RESPONSE`.

## Devin Secrets Needed

None for auth-check/redirect testing. For full functionality: `DATABASE_URL`, `GROQ_API_KEY`,
`GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`.
