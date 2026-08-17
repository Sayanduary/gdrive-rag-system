import os

os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from config import settings

from app.api.routes.query import router as query_router
from app.api.routes.auth import router as auth_router
from app.api.routes.drive import router as drive_router
from app.api.routes.conversations import (
    router as conversations_router
)


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION
)


# --------------------------------------------------
# Middleware Configuration
# --------------------------------------------------

# 1. Session Middleware
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SESSION_SECRET,
    same_site=settings.SESSION_COOKIE_SAMESITE,
    https_only=settings.SESSION_COOKIE_SECURE,
)

# 2. CORS Middleware
origins = [
    "http://localhost:5173",
    "https://gdrive-rag-system.vercel.app",
]
if settings.FRONTEND_URL and settings.FRONTEND_URL not in origins:
    origins.append(settings.FRONTEND_URL)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



# --------------------------------------------------
# Routers
# --------------------------------------------------

app.include_router(
    query_router
)

app.include_router(
    auth_router
)

app.include_router(
    drive_router
)

app.include_router(
    conversations_router
)
# --------------------------------------------------
# Root
# --------------------------------------------------

@app.get("/")
def root():

    return {
        "message": "Google Drive RAG API",
        "status": "running"
    }


@app.get("/health")
def health():

    return {
        "status": "healthy"
    }