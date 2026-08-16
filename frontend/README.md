# Frontend — Google Drive RAG System

React 19 single-page application (SPA) built with Vite for interacting with the Google Drive RAG system.

## Features

- **Google OAuth Login**: Authenticate with Google to connect Drive permissions.
- **Drive Ingestion UI**: Enter a Google Drive folder ID to initiate recursive document processing and indexing.
- **Interactive RAG Chat**: Ask questions based on ingested documents and view citations and source file metadata.

## Scripts

- `npm run dev`: Start Vite development server on `http://localhost:5173`.
- `npm run build`: Build production assets into the `dist/` directory.
- `npm run preview`: Preview the production build locally.
- `npm run lint`: Run ESLint checks.

## Docker Setup

The frontend uses a multi-stage Docker build:
1. **Build stage**: `node:20-alpine` runs `npm run build`.
2. **Production stage**: `nginx:alpine` serves static files with client-side SPA routing (`nginx.conf`).

To build and run with Docker:
```bash
docker build -t gdrive-rag-frontend .
docker run -p 5173:80 gdrive-rag-frontend
```
