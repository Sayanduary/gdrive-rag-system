---
name: zentra-operations
description: "Use when setting up, running, testing, deploying, or handing off the Zentra Google Drive RAG application."
tags:
  - setup
  - deployment
  - testing
  - operations
---

# Zentra Operations

Zentra is a React/Vite frontend with a FastAPI backend. It connects to Google
Drive through OAuth, extracts supported documents, stores embeddings in
PostgreSQL with `pgvector`, and provides retrieval-augmented chat.

## Setup

1. Copy `backend/.env.example` to `backend/.env`.
2. Fill in the Google OAuth, database, session, and LLM settings.
3. Use Python 3.11 and Node.js 22.
4. For host-based OCR, install Tesseract and Poppler. Docker includes these
   dependencies for the backend image.

## Run locally

Backend:

```bash
cd backend
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Frontend, in a second terminal:

```bash
cd frontend
npm ci
npm run dev -- --host 127.0.0.1 --port 5173
```

Open `http://localhost:5173`. For local HTTP, use `SESSION_COOKIE_SAMESITE=lax`
and `SESSION_COOKIE_SECURE=false`.

## Validate

```bash
cd frontend
npm run lint
npm run build

cd ../backend
python -m pytest
```

For Docker Compose, Google Cloud OAuth, production cookies, and handoff
procedures, read [skills.md](./skills.md).

## Safety

- Never commit `.env`, OAuth secrets, API keys, database credentials, or cookie
  exports.
- Use a secret manager in production.
- Use HTTPS and secure cross-site cookies in production.
- Treat indexed Drive content as private customer data.
