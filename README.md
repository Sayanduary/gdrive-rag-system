# Zentra — Google Drive RAG System

A full-stack, enterprise-grade Retrieval-Augmented Generation (RAG) platform that connects directly to **Google Drive**, recursively ingests and parses documents (PDFs, Google Docs, Slides, Sheets, images, presentations), generates vector embeddings stored in **PostgreSQL (`pgvector`)**, and delivers real-time streaming answers backed by source citations using **Groq LLM**.

---

## Architecture Overview

```mermaid
graph TD
    User([User Browser]) -->|HTTPS / UI| Vercel[Vercel Frontend - React 19 + Vite]
    Vercel -->|Same-Origin Proxy /api/*| Render[Render Backend - FastAPI]
    
    subgraph Authentication & Storage
        Render -->|Session State & Chunks| Supabase[(PostgreSQL + pgvector)]
    end
    
    subgraph Data Processing Pipeline
        Render -->|OAuth2 / API v3| GDrive[Google Drive API]
        GDrive -->|Raw Documents| Parser[Document Parser PyMuPDF / Tesseract OCR / pptx]
        Parser -->|Text Chunks| Embedder[FastEmbed BAAI/bge-small-en-v1.5]
        Embedder -->|Vector Embeddings| Supabase
    end
    
    subgraph RAG & Generation
        Render -->|Vector Similarity Search| Supabase
        Render -->|Prompt + Context| Groq[Groq API LLM / Vision]
        Groq -->|SSE Token Stream| Render
        Render -->|SSE Stream + Sources| Vercel
    end
```

---

## Key Features

- 🔐 **Google OAuth 2.0 Integration**: Secure Google single sign-on with automatic token refresh and multi-tenant isolation.
- 📁 **Recursive Drive Syncing**: Automatically traverses folders and nested subfolders to discover and index supported document types.
- 📄 **Multi-Format Extraction & OCR**:
  - **PDFs**: Fast text extraction via `PyMuPDF` (`fitz`), with automatic fallback to `Tesseract OCR` for scanned PDF pages.
  - **Google Workspace Docs**: Automatic PDF/CSV conversion for Google Docs, Slides, and Sheets.
  - **PowerPoint**: Slide-by-slide text extraction using `python-pptx`.
  - **Images**: Optical Character Recognition (`.png`, `.jpg`, `.jpeg`, `.webp`) powered by Tesseract.
- ⚡ **High-Performance Vector Search**: Cosine distance similarity search (`<=>` operator) in PostgreSQL using `pgvector`.
- 💬 **Streaming RAG Chat**: Real-time Server-Sent Events (SSE) streaming answers powered by **Groq** with file-level source citations.
- 📊 **Knowledge Dashboard**: View analyzed folders, total indexed chunks, file metadata, and perform targeted file/folder deletions.
- 🔄 **Async Processing**: Long-running drive sync operations execute in background workers with status polling, eliminating HTTP timeouts.

---

## Core Technical Optimizations & Architectural Highlights

### 1. Async Background Ingestion & Polling (502 Timeout Prevention)
Drive ingestion (downloading, OCR, embedding) is decoupled from the HTTP request cycle. `POST /api/drive/analyze` validates requests and spawns a background thread worker immediately, returning a `job_id`. The client polls `GET /api/drive/status/{job_id}` for real-time progress updates, bypassing serverless proxy timeouts.

### 2. Thread-Safe Singleton VectorStore (Memory Leak Prevention)
`VectorStore` uses a double-checked locking singleton pattern (`__new__` + `threading.Lock()`). This guarantees that the `FastEmbed` model and `psycopg` connection pool are instantiated exactly once per worker process, preventing RAM bloat and PostgreSQL connection exhaustion.

### 3. Slim Session Payloads (Logout Prevention)
Starlette session cookies are constrained to under 4 KB. The backend stores *only* `token` and `refresh_token` in session cookies. Static configuration parameters (`client_id`, `client_secret`, `token_uri`) are reconstructed from server settings at runtime, preventing cookie truncation and unexpected session logouts.

### 4. Zero-FOUC Font Preloading
Google Fonts (`Rubik`) are preconnected and linked in `index.html` head rather than imported inside CSS stylesheets, avoiding blocking render shifts and flash of unstyled content.

---

## Tech Stack

| Layer | Technologies |
| :--- | :--- |
| **Frontend** | React 19, Vite, Tailwind CSS v4, React Router v7, Axios, React Icons |
| **Backend** | FastAPI, Python 3.11, Uvicorn, Pydantic Settings, PyMuPDF, python-pptx, Tesseract OCR |
| **Vector Store & Database** | PostgreSQL + `pgvector` (Supabase / psycopg3 connection pool) |
| **Embeddings & LLM** | FastEmbed (`BAAI/bge-small-en-v1.5`), Groq API (`openai/gpt-oss-120b`, `qwen/qwen3.6-27b`) |
| **Hosting & Proxy** | Vercel (Frontend + Proxy), Render (Backend Container), Docker |

---

## Directory Structure

```text
gdrive-rag-system/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── routes/   # FastAPI router endpoints (auth, drive, query, conversations, folders)
│   │   ├── models/       # Database & API schemas
│   │   ├── services/     # Core logic (gdrive, parser, chunker, vectorstore, ingestion, rag, memory)
│   │   └── db.py         # Shared PostgreSQL connection pool setup
│   ├── config.py         # Application configuration & env settings
│   ├── main.py           # FastAPI entrypoint & middleware setup
│   ├── requirements.txt  # Python package requirements
│   └── Dockerfile        # Backend Docker container configuration
├── frontend/
│   ├── src/
│   │   ├── components/   # UI components (Navbar, etc.)
│   │   ├── pages/        # Route pages (Login, Dashboard, Analyze, Chat)
│   │   ├── services/     # Axios client configuration (api.js)
│   │   ├── App.jsx       # Root router component
│   │   └── index.css     # Base design system & Tailwind styling
│   ├── public/           # Static web assets
│   ├── vercel.json       # Vercel reverse proxy rewrite rules
│   ├── vite.config.js    # Vite bundler configuration
│   └── package.json      # Node.js dependencies
├── docker-compose.yml    # Local container orchestration
└── README.md             # Project documentation
```

---

## Environment Configuration

Create a `.env` file in the `backend/` directory:

```env
# Application
APP_NAME="Zentra"
APP_VERSION="1.0.0"
ENVIRONMENT="development"  # development | production
SESSION_SECRET="your-secure-random-session-secret"

# Frontend Integration
FRONTEND_URL="http://localhost:5173"

# Google OAuth 2.0 Credentials
GOOGLE_CLIENT_ID="your-google-client-id.apps.googleusercontent.com"
GOOGLE_CLIENT_SECRET="your-google-client-secret"
GOOGLE_REDIRECT_URI="http://localhost:8000/api/auth/google/callback"

# Database (PostgreSQL + pgvector)
DATABASE_URL="postgresql://user:password@host:5432/dbname"

# Groq LLM API
GROQ_API_KEY="gsk_your_groq_api_key"
GROQ_LLM_MODEL="openai/gpt-oss-120b"
GROQ_VISION_MODEL="qwen/qwen3.6-27b"

# Vector Search & Chunking Settings
EMBEDDING_MODEL="BAAI/bge-small-en-v1.5"
CHUNK_SIZE=1000
CHUNK_OVERLAP=150
TOP_K=5
RETRIEVAL_CANDIDATES=100
```

---

## Development Setup

### Option 1: Manual Local Execution

#### 1. Backend Setup
```bash
cd backend

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install Python packages
pip install -r requirements.txt

# Ensure system OCR dependencies are installed:
# Ubuntu/Debian: sudo apt update && sudo apt install -y tesseract-ocr libtesseract-dev poppler-utils
# macOS: brew install tesseract poppler

# Start FastAPI dev server
uvicorn main:app --reload --port 8000
```

#### 2. Frontend Setup
```bash
cd frontend

# Install Node dependencies
npm install

# Start Vite dev server
npm run dev
```

The frontend will run at `http://localhost:5173` and backend API at `http://localhost:8000`.

---

### Option 2: Docker Compose

```bash
docker compose up --build
```

---

## API Endpoints Reference

### Authentication (`/api/auth`)
- `GET /api/auth/google`: Redirects to Google OAuth authorization page.
- `GET /api/auth/google/callback`: Processes OAuth callback and stores session.
- `GET /api/auth/me`: Checks current session authentication status.
- `POST /api/auth/logout`: Clears authentication session.

### Google Drive Sync (`/api/drive`)
- `POST /api/drive/analyze`: Validates folder URL, initializes background sync job.
- `GET /api/drive/status/{job_id}`: Polls progress and results of background sync job.
- `GET /api/drive/debug/access/{folder_id}`: Debugs Google Drive folder permissions.

### RAG & Chat (`/api`)
- `POST /api/query`: Returns non-streaming RAG answer with document source citations.
- `POST /api/query/stream`: Server-Sent Events (SSE) streaming RAG answer with metadata and sources.

### Dashboard & Folders (`/api/folders`)
- `GET /api/folders`: Lists all analyzed Google Drive folders for the current user.
- `GET /api/folders/{folder_id}`: Gets indexed files in a specific folder.
- `DELETE /api/folders/{folder_id}`: Deletes a folder and all its indexed vector chunks.
- `DELETE /api/folders/{folder_id}/files/{file_id}`: Removes an individual indexed file.

### Conversations (`/api/conversations`)
- `GET /api/conversations`: Fetches user conversation history.
- `POST /api/conversations`: Starts a new conversation context.
- `GET /api/conversations/{id}`: Retrieves messages for a conversation.
- `PATCH /api/conversations/{id}`: Renames conversation title.
- `DELETE /api/conversations/{id}`: Deletes conversation thread.

---

## License

This project is licensed under the [MIT License](LICENSE).
