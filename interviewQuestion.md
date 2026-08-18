# Zentra — Technical Interview Questions & Answers

This document covers technical questions and interview-ready answers about the architecture, algorithms, optimizations, security, database design, and real-world production debugging in **Zentra** (Full-Stack Google Drive RAG System).

---

## 🏗️ 1. Architecture & System Design

### Q1: Can you give an architectural overview of Zentra?
**Answer:** Zentra is a full-stack RAG platform built with React 19 (Vite) on the frontend and FastAPI (Python 3.11) on the backend. The frontend is hosted on Vercel and proxies `/api/*` requests to a Render-hosted FastAPI container. Document metadata and vector embeddings (`BAAI/bge-small-en-v1.5`) are stored in PostgreSQL using the `pgvector` extension hosted on Supabase. RAG answers are generated via Groq LLM (`openai/gpt-oss-120b`) and streamed to the UI via Server-Sent Events (SSE).

### Q2: Why did you choose a decoupled architecture with Vercel and Render instead of a single server?
**Answer:** Decoupling allows independent scaling and optimal hosting choices: Vercel provides instant CDN edge deployment and static asset caching for the React frontend, while Render hosts the containerized FastAPI backend with system binaries (`tesseract-ocr`, `poppler-utils`) needed for document parsing and OCR.

### Q3: How do you handle cross-origin cookie restrictions between Vercel and Render?
**Answer:** Browsers block 3rd-party cross-site session cookies by default. To solve this, Vercel's `vercel.json` configures a same-origin reverse proxy rewrite: requests sent to `/api/*` on `gdrive-rag-system.vercel.app` are forwarded under the hood to `gdrive-rag-system-h5sf.onrender.com`. The browser perceives the API as 1st-party, allowing session cookies to be saved and sent securely.

---

## 🔍 2. RAG & Vector Search

### Q4: How is vector similarity search implemented in PostgreSQL?
**Answer:** Vector embeddings are stored in a `vector(384)` column (matching `bge-small-en-v1.5` dimensions) using `pgvector`. Similarity queries use the Cosine Distance operator (`<=>`):
```sql
SELECT id, content, file_name, embedding <=> %s::extensions.vector AS distance
FROM public.document_chunks
WHERE user_id = %s
ORDER BY embedding <=> %s::extensions.vector
LIMIT %s;
```
Multi-tenant scoping (`WHERE user_id = %s`) guarantees strict data isolation between Google users.

### Q5: What text chunking strategy did you use and why?
**Answer:** We use a recursive character text splitter with a **chunk size of 1,000 characters** and a **sliding overlap of 150 characters**. 1,000 characters provides enough contextual density for embeddings without overwhelming the LLM context window, while the 150-character overlap prevents information loss across chunk boundaries (e.g., split sentences or code blocks).

### Q6: How does the SSE streaming RAG pipeline work?
**Answer:** When a user asks a question via `POST /api/query/stream`:
1. The backend retrieves history from PostgreSQL and queries `VectorStore` for top-$K$ context chunks.
2. It sends an initial `metadata` SSE event containing retrieval sources and `conversation_id`.
3. It yields `token` SSE events as tokens arrive from Groq LLM.
4. On completion, it yields a `done` SSE event and persists user/assistant messages to PostgreSQL.

---

## 📄 3. Document Ingestion, Parsing & Google Drive

### Q7: How does Zentra handle different file types during Google Drive ingestion?
**Answer:** `IngestionService` categorizes files by MIME type:
- **PDFs**: Parsed via PyMuPDF (`fitz`). If extracted text is empty or under a threshold, it automatically falls back to `Tesseract OCR` page-by-page.
- **Google Docs/Slides/Sheets**: Exported via Google Drive API `export_media` as PDFs or CSVs before parsing.
- **PowerPoint (`.pptx`)**: Parsed slide-by-slide using `python-pptx`.
- **Images (`.png`, `.jpg`, `.jpeg`, `.webp`)**: OCR-processed directly via PyTesseract and Pillow.

### Q8: How do you handle file updates and deletions when re-syncing a Google Drive folder?
**Answer:** During sync, the ingestion pipeline compares Google Drive's `modifiedTime` against PostgreSQL's stored `modified_time`:
- **Unchanged**: Skipped immediately to save compute.
- **Modified**: Re-parsed and re-embedded; stale chunk IDs from the previous version are purged.
- **Deleted from Drive**: Any file ID present in PostgreSQL but missing from Drive is deleted from `document_chunks`.

---

## ⚡ 4. Backend & Microservices Optimization

### Q9: Why did you implement a Singleton pattern for the `VectorStore`?
**Answer:** `VectorStore` initializes the `FastEmbed` model (which loads weights into RAM) and a PostgreSQL connection pool (`psycopg_pool`). Creating `VectorStore` per request leaked RAM and exhausted Supabase database connection limits (`EMAXCONNSESSION`). Using a thread-safe singleton (`__new__` + `threading.Lock()`) ensures the embedding model and connection pool are initialized exactly once per backend process.

### Q10: How did you solve HTTP 502 Bad Gateway timeouts on long-running Drive analysis?
**Answer:** Cloud platforms like Render enforce a 30-second proxy timeout. Syncing large folders took longer, causing 502 errors. We refactored `/api/drive/analyze` to use **FastAPI `BackgroundTasks`**:
1. The POST endpoint synchronously validates folder access (< 1s) and returns a unique `job_id`.
2. Document downloading, OCR, chunking, and embedding run asynchronously in a background thread worker.
3. The frontend polls `GET /api/drive/status/{job_id}` every 2 seconds for real-time progress updates until completed.

---

## 🔐 5. Security & Authentication

### Q11: How is user identity and data authorization managed?
**Answer:** User identity is verified via Google OAuth 2.0 (`openid`, `email`, `profile`, `drive.readonly`). Every vector chunk, document metadata entry, and chat conversation is tagged with the user's immutable Google `sub` ID (`user_id`). Every database query enforces `WHERE user_id = %s`, preventing cross-tenant data leaks.

### Q12: How did you fix the issue where users were randomly getting logged out?
**Answer:** Starlette `SessionMiddleware` stores session data inside signed browser cookies, which have a strict 4 KB limit. Storing complete Google OAuth credential objects (`access_token`, `refresh_token`, `client_id`, `client_secret`, `scopes`) caused cookie payloads to exceed 4 KB, leading to silent browser cookie truncation and signature failures.
**Fix:** We slimmed session storage to contain *only* `token` and `refresh_token` (~300 bytes), reconstructing static client configuration (`client_id`, `client_secret`, `token_uri`) from server settings at runtime.

---

## 💻 6. Frontend & UI Optimizations

### Q13: How did you eliminate Flash of Unstyled Content (FOUC) on the frontend?
**Answer:** The Google Font `Rubik` was originally imported via CSS `@import`, which blocks parsing and delays font fetching. We moved font preconnecting (`<link rel="preconnect" href="https://fonts.gstatic.com">`) and stylesheet loading directly into `index.html` head, allowing instant parallel font fetching.

### Q14: How does the chat sidebar state stay synchronized across devices and sessions?
**Answer:** Active conversation IDs are persisted in `localStorage` keyed by the user's Google `sub` ID (`gdrive_rag_active_conversation_{userId}`). On initial mount, `App.jsx` verifies authentication via `GET /api/auth/me`, then fetches thread history from `/api/conversations`, restoring state seamlessly without leaking state across account switches.

---

## 🐛 7. Top 4 Real-World Production Bugs Solved

| Bug | Symptom | Root Cause | Solution |
| :--- | :--- | :--- | :--- |
| **Session Drop** | App randomly logged users out on page refresh. | Session cookie exceeded 4 KB limit due to storing full OAuth credentials, causing cookie truncation. | Slimmed session cookie payload to store only `token` + `refresh_token` (~300B). |
| **Memory Leak** | RAM consumption kept rising until backend container crashed. | `VectorStore` (and FastEmbed model + DB pool) was re-instantiated on every request. | Converted `VectorStore` into a thread-safe Singleton pattern using `threading.Lock()`. |
| **502 Bad Gateway** | Folder analysis failed on large Drive folders. | Sync execution was synchronous, exceeding Render's 30s HTTP proxy timeout limit. | Converted `/analyze` to an async background job with a status polling endpoint (`/status/{job_id}`). |
| **FOUC** | Flash of unstyled text layout shift on initial load. | Google Fonts loaded via `@import` in `index.css`. | Preconnected and loaded font stylesheet directly in `index.html` head. |
