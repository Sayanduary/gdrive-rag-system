# Zentra Skills and Operations Guide

Zentra is a Google Drive knowledge-base application. It authenticates users with
Google OAuth, recursively indexes documents from Drive, stores embeddings and
conversation data in PostgreSQL with `pgvector`, and answers questions with
retrieval-augmented generation (RAG).

This guide is intended for a buyer, agency, or developer taking over the
application.

## What is included

- React/Vite frontend in `frontend/`
- FastAPI backend in `backend/`
- Google Drive OAuth and document ingestion
- PDF, Google Workspace, PowerPoint, and image parsing/OCR
- PostgreSQL/`pgvector` vector search
- Groq-powered chat and streaming responses
- Dockerfiles and a local `docker-compose.yml`

## Requirements

### Local development

- Python 3.11
- Node.js 22
- npm
- PostgreSQL with the `vector` extension, or a hosted provider such as Supabase
- Tesseract OCR and Poppler for non-Docker backend development

### Production services

The recommended deployment is:

- Frontend: Vercel or a static hosting provider
- Backend: Render, Railway, Fly.io, or a comparable Docker/Python host
- Database: managed PostgreSQL with `pgvector`
- LLM: Groq API
- Identity and source documents: Google Cloud OAuth and Google Drive

The embedding model downloads on first use. Make sure the backend has enough
disk space and memory for the model and document-processing workload.

## Configuration

Create `backend/.env` from `backend/.env.example`. Never commit this file or
share the values in it.

At minimum, configure:

```env
APP_NAME=Zentra
APP_VERSION=1.0.0
ENVIRONMENT=development
SESSION_SECRET=replace-with-a-long-random-secret
FRONTEND_URL=http://localhost:5173

GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
GOOGLE_REDIRECT_URI=http://localhost:8000/api/auth/google/callback

DATABASE_URL=postgresql://user:password@host:5432/database
GROQ_API_KEY=gsk_your_key
GROQ_LLM_MODEL=openai/gpt-oss-120b
GROQ_VISION_MODEL=qwen/qwen3.6-27b

EMBEDDING_MODEL=BAAI/bge-small-en-v1.5
CHUNK_SIZE=1000
CHUNK_OVERLAP=150
TOP_K=5
RETRIEVAL_CANDIDATES=100
```

For local HTTP development, also set:

```env
SESSION_COOKIE_SAMESITE=lax
SESSION_COOKIE_SECURE=false
```

For production, use HTTPS and set:

```env
ENVIRONMENT=production
FRONTEND_URL=https://your-frontend-domain.example
GOOGLE_REDIRECT_URI=https://your-frontend-domain.example/api/auth/google/callback
SESSION_COOKIE_SAMESITE=none
SESSION_COOKIE_SECURE=true
```

Use the real public frontend URL consistently in the frontend host, backend
`FRONTEND_URL`, Google OAuth settings, and the frontend API proxy configuration.

## Google Cloud setup

1. Create or select a Google Cloud project.
2. Enable Google Drive API.
3. Configure the OAuth consent screen and add the intended test or production
   users.
4. Create a Web application OAuth client.
5. Add the exact callback URL from `GOOGLE_REDIRECT_URI` to **Authorized
   redirect URIs**.
6. Add the frontend origin to **Authorized JavaScript origins** when required.
7. Copy the client ID and secret into the backend environment only.

The callback URL must match exactly, including scheme, hostname, path, and
trailing slash behavior.

## Run locally

### 1. Start the backend

```bash
cd backend
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Install OCR dependencies if running outside Docker:

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install -y tesseract-ocr libtesseract-dev poppler-utils

# macOS
brew install tesseract poppler
```

### 2. Start the frontend

In another terminal:

```bash
cd frontend
npm ci
npm run dev -- --host 127.0.0.1 --port 5173
```

Open `http://localhost:5173`.

Without Google, PostgreSQL, or Groq credentials, the backend can still be
started and the unauthenticated route behavior can be smoke-tested. Full login,
Drive ingestion, indexing, and chat require all production credentials.

### 3. Run checks

```bash
cd frontend
npm run lint
npm run build

cd ../backend
python -m pytest
```

The backend tests that exercise Google Drive, database, or LLM services require
their corresponding credentials and may need a configured test environment.

## Run with Docker Compose

From the repository root:

```bash
cp backend/.env.example backend/.env
# Edit backend/.env with real values.
docker compose up --build
```

Services:

- Frontend: `http://localhost:5173`
- Backend: `http://localhost:8000`
- LM Studio container: `http://localhost:1234`

The compose file persists LM Studio models and backend data in Docker volumes
or the repository's `backend/data` directory. Back up these locations before
moving or deleting the deployment.

## Production deployment checklist

1. Provision PostgreSQL and enable `pgvector`.
2. Deploy the backend using `backend/Dockerfile`.
3. Set every backend environment variable in the hosting provider's secret
   manager; do not upload `.env`.
4. Deploy the frontend using the `frontend/` directory.
5. Set the frontend API proxy destination to the deployed backend URL. Review
   `frontend/vercel.json`; it currently contains a project-specific Render URL.
6. Update `FRONTEND_URL`, `GOOGLE_REDIRECT_URI`, and Google Cloud OAuth settings.
7. Use a unique random `SESSION_SECRET` in production.
8. Configure HTTPS, CORS, cookie settings, health monitoring, and log retention.
9. Test Google login, a small Drive folder, ingestion progress, citations,
   chat streaming, logout, and deletion before accepting customer traffic.
10. Set database backups, retention, alerting, and a rollback plan.

Do not expose the database, Groq key, Google client secret, or session secret to
the browser. The frontend only needs public build-time configuration and API
routing.

## Customer handoff and agency delivery

Before selling or transferring the app, provide:

- Repository access and the exact deployed commit
- Hosting and database ownership details
- A secret inventory naming each required secret without revealing values
- Google Cloud project and OAuth ownership transfer instructions
- Groq organization/API-key ownership and billing information
- Database backup/export and restore instructions
- Domain, DNS, SSL, and email ownership details
- A short demo account or test Google account with non-sensitive documents
- Support boundaries, usage limits, and expected ingestion/LLM costs

The buyer should rotate every credential after transfer, especially
`SESSION_SECRET`, Google OAuth secrets, database credentials, and Groq keys.

## Troubleshooting

### Login redirects or cookies fail

- Confirm `GOOGLE_REDIRECT_URI` exactly matches Google Cloud.
- Confirm `FRONTEND_URL` is the browser's real origin.
- Local HTTP requires `SESSION_COOKIE_SECURE=false` and `SameSite=lax`.
- Production cross-site frontend/backend deployments require HTTPS,
  `SESSION_COOKIE_SECURE=true`, and `SameSite=none`.

### Chat or ingestion fails

- Verify `DATABASE_URL` points to PostgreSQL with `pgvector` enabled.
- Verify `GROQ_API_KEY` and the selected model names.
- Check backend logs for embedding model download, database, or OAuth errors.
- Confirm the Google account can access the Drive folder being analyzed.

### Scanned documents are empty

- Confirm Tesseract and Poppler are installed in the host or container.
- Allow enough CPU, memory, and processing time for OCR-heavy folders.

### Frontend API calls target the wrong server

- Local development automatically uses the local backend for localhost.
- For production, update `frontend/vercel.json` or the hosting proxy to the
  current backend URL and redeploy the frontend.

## Operating principles

- Keep secrets in the hosting provider's secret manager.
- Limit Google OAuth scopes and Drive access to what the product requires.
- Use managed database backups and test restoration periodically.
- Monitor ingestion job duration, failed jobs, database storage, embedding
  downloads, and Groq usage.
- Review dependencies and rebuild Docker images regularly.
- Treat user Drive content as private customer data and define deletion and
  retention policies before onboarding customers.
