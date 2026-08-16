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
# CORS
# --------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --------------------------------------------------
# Session
# --------------------------------------------------

app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SESSION_SECRET,
    same_site="lax",
    https_only=False,
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