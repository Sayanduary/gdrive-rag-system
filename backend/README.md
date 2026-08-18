# Backend — Zentra Google Drive RAG System

FastAPI backend service for document ingestion, multi-format OCR parsing, vector embedding generation, PostgreSQL (`pgvector`) vector search, conversation memory management, and Retrieval-Augmented Generation (RAG) powered by Groq LLMs.

---

## Architecture Overview

```text
backend/
├── app/
│   ├── api/
│   │   └── routes/
│   │       ├── auth.py          # Google OAuth2 login, callback, /me, logout
│   │       ├── drive.py         # Drive folder validation, background analysis worker, status polling
│   │       ├── query.py         # RAG question answering (synchronous & SSE streaming)
│   │       ├── conversations.py # Conversation thread CRUD operations
│   │       └── folders.py       # Dashboard folder & file registry management
│   │
│   ├── services/
│   │   ├── gdrive.py            # Google Drive API v3 recursive file traversal & download
│   │   ├── parser.py            # Text extraction (PyMuPDF, python-pptx, Tesseract OCR fallback)
│   │   ├── chunker.py           # Overlapping text chunking engine
│   │   ├── vectorstore.py       # Singleton VectorStore wrapper for PostgreSQL pgvector & FastEmbed
│   │   ├── ingestion.py         # Multi-format document ingestion pipeline
│   │   ├── rag.py               # Document retrieval, prompt assembly & Groq LLM streaming
│   │   ├── memory.py            # PostgreSQL-backed chat history persistence
│   │   ├── groq.py              # Groq API client integration
│   │   └── analyzed_folders.py  # User dashboard folder registry service
│   │
│   ├── models/                  # Data structures & Pydantic models
│   └── db.py                    # Thread-safe PostgreSQL connection pool (psycopg3)
│
├── config.py                    # Pydantic Settings environment configuration
├── main.py                      # FastAPI application entrypoint & middleware configuration
├── requirements.txt             # Python package dependencies
└── Dockerfile                   # Python 3.11-slim container image specification
```

---

## Key Backend Systems & Architectural Patterns

### 1. Thread-Safe Singleton VectorStore
- Encapsulates `fastembed.TextEmbedding` (`BAAI/bge-small-en-v1.5`) and PostgreSQL `psycopg` connection pool.
- Uses double-checked locking to ensure single instance creation across async worker threads, preventing memory leaks and connection pool starvation.

### 2. Async Background Task Pipeline
- Long-running Google Drive ingestion executes asynchronously via `FastAPI.BackgroundTasks` and worker threads.
- Avoids request timeouts (502 Bad Gateway) on cloud platforms like Render by providing instant response (`job_id`) and polling endpoint (`GET /api/drive/status/{job_id}`).

### 3. Slim Session Cookies (<4KB Limit)
- Restricts session cookies to store only essential OAuth tokens (`token`, `refresh_token`).
- Dynamically reconstructs static client credentials (`client_id`, `client_secret`, `token_uri`) from server configuration at runtime, eliminating cookie truncation and unexpected user logouts.

---

## Environment Variables Configuration

The backend reads configuration from `.env` or system environment variables:

| Variable | Type | Description |
| :--- | :--- | :--- |
| `APP_NAME` | `str` | Application name (`"Zentra"`) |
| `ENVIRONMENT` | `str` | Execution environment (`"development"` / `"production"`) |
| `SESSION_SECRET` | `str` | Cryptographic secret for session cookie signatures |
| `FRONTEND_URL` | `str` | Frontend web origin for CORS and OAuth redirects |
| `GOOGLE_CLIENT_ID` | `str` | Google Cloud OAuth Client ID |
| `GOOGLE_CLIENT_SECRET` | `str` | Google Cloud OAuth Client Secret |
| `GOOGLE_REDIRECT_URI` | `str` | Authorized Google OAuth Redirect URI |
| `DATABASE_URL` | `str` | PostgreSQL database connection string (`postgresql://...`) |
| `GROQ_API_KEY` | `str` | Groq LLM API Key |
| `GROQ_LLM_MODEL` | `str` | Primary RAG LLM model (`openai/gpt-oss-120b`) |
| `GROQ_VISION_MODEL` | `str` | Groq vision model for image OCR |
| `EMBEDDING_MODEL` | `str` | FastEmbed model (`BAAI/bge-small-en-v1.5`) |
| `CHUNK_SIZE` | `int` | Document chunk size in characters (default: `1000`) |
| `CHUNK_OVERLAP` | `int` | Chunk overlap in characters (default: `150`) |

---

## Running the Backend

### Local Setup
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Ensure system dependencies are installed:
# Ubuntu/Debian: sudo apt update && sudo apt install -y tesseract-ocr libtesseract-dev poppler-utils
# macOS: brew install tesseract poppler

uvicorn main:app --reload --port 8000
```

### Docker Execution
```bash
docker build -t zentra-backend .
docker run -p 8000:8000 --env-file .env zentra-backend
```
