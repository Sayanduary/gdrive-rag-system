# Zentra — Google Drive RAG System

Zentra is a full-stack retrieval-augmented generation application that
connects Google Drive to a searchable knowledge base. It supports Google OAuth,
recursive Drive ingestion, PDF and office-document parsing, OCR, PostgreSQL
with `pgvector`, and streaming RAG chat with source citations.

See the [skills and operations guide](./skills.md) for setup, environment
variables, deployment, testing, troubleshooting, and buyer handoff.

## Stack

- Frontend: React 19, Vite, Tailwind CSS, React Router, Axios
- Backend: FastAPI, Uvicorn, Python 3.11
- Storage: PostgreSQL with `pgvector`
- Parsing: PyMuPDF, python-pptx, Pillow, Tesseract OCR
- AI: FastEmbed embeddings and Groq LLMs
- Deployment: Docker, Vercel, Render-compatible backend

## Quick start

```bash
cp backend/.env.example backend/.env

cd backend
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

In another terminal:

```bash
cd frontend
npm ci
npm run dev
```

Open `http://localhost:5173`. Configure the backend environment before using
Google login, Drive ingestion, database search, or chat.

## Docker

```bash
cp backend/.env.example backend/.env
docker compose up --build
```

The frontend is served on port `5173` and the backend on port `8000`.

## Checks

```bash
cd frontend
npm run lint
npm run build

cd ../backend
python -m pytest
```

Never commit `.env`, API keys, OAuth credentials, database credentials, or
cookie exports. Rotate all secrets when transferring the application.
