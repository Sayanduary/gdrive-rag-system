# Frontend — Zentra Google Drive RAG System

React 19 Single Page Application (SPA) built with Vite and Tailwind CSS v4, delivering a modern, dark-mode glassmorphism interface for indexing Google Drive folders and interacting with RAG knowledge bases.

---

## Key Features & Pages

- 🔑 **Google Login (`/login`)**: Direct authentication flow linking Google permissions to the backend.
- 📁 **Analyze Folder (`/analyze`)**: Enter any Google Drive folder URL to initiate non-blocking background document parsing. Displays real-time status updates via polling.
- 📊 **Dashboard (`/dashboard`)**: Overview of analyzed folders, file counts, and chunk statistics. Supports viewing indexed files and deleting individual files or entire folders.
- 💬 **Interactive Chat (`/chat`)**: Multi-conversation RAG interface supporting real-time Server-Sent Events (SSE) streaming answers, markdown formatting, mobile drawer navigation, and clickable document source badges.

---

## Technical Highlights

- **Vercel Same-Origin Proxy**: Uses `vercel.json` rewrite rules to route `/api/*` requests to the Render backend, guaranteeing session cookies are treated as first-party cookies across browsers.
- **Background Task Polling**: Listens to `/api/drive/status/{job_id}` background progress updates so long-running folder parsing operations never timeout or freeze the user interface.
- **Zero-FOUC Font Optimization**: Preconnects Google Fonts directly in `index.html` to eliminate render blocking and typography layout shifts.

---

## Available Scripts

- `npm run dev`: Starts local Vite development server at `http://localhost:5173`.
- `npm run build`: Bundles production assets into the `dist/` directory.
- `npm run preview`: Previews the production build locally.
- `npm run lint`: Runs ESLint checks across code files.

---

## Deployment & Docker

### Vercel Deployment
The frontend is pre-configured for Vercel deployment. `vercel.json` handles client-side routing and API proxying:

```json
{
  "rewrites": [
    {
      "source": "/api/:path*",
      "destination": "https://gdrive-rag-system-h5sf.onrender.com/api/:path*"
    },
    {
      "source": "/(.*)",
      "destination": "/index.html"
    }
  ]
}
```

### Docker Execution
```bash
docker build -t zentra-frontend .
docker run -p 5173:80 zentra-frontend
```
