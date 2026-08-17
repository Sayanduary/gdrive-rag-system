import os

# --------------------------------------------------
# OAuth transport
# --------------------------------------------------
# Allow insecure OAuth only during local development.
# Production Render runs over HTTPS.
if os.getenv(
    "ENVIRONMENT",
    "development",
).lower() != "production":
    os.environ[
        "OAUTHLIB_INSECURE_TRANSPORT"
    ] = "1"


from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from config import settings

from app.api.routes.query import (
    router as query_router,
)

from app.api.routes.auth import (
    router as auth_router,
)

from app.api.routes.drive import (
    router as drive_router,
)

from app.api.routes.conversations import (
    router as conversations_router,
)

from app.api.routes.folders import (
    router as folders_router,
)

# ==================================================
# APPLICATION
# ==================================================

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
)


# ==================================================
# FRONTEND URL
# ==================================================

frontend_url = (
    settings.FRONTEND_URL
    .rstrip("/")
)


# ==================================================
# SESSION MIDDLEWARE
# ==================================================

# Cross-site Vercel -> Render authentication requires:
#
# SameSite=None
# Secure=True
#
# During local development, HTTP is allowed.
# During production, HTTPS is enforced.

same_site = getattr(
    settings,
    "SESSION_COOKIE_SAMESITE",
    "lax",
)

https_only = getattr(
    settings,
    "SESSION_COOKIE_SECURE",
    False,
)

if frontend_url.startswith(
    "https://"
):

    same_site = "none"
    https_only = True


app.add_middleware(
    SessionMiddleware,

    secret_key=settings.SESSION_SECRET,

    session_cookie=(
        "gdrive_rag_session"
    ),

    max_age=60 * 60 * 24 * 14,

    same_site=same_site,

    https_only=https_only,
)


# ==================================================
# CORS
# ==================================================

allowed_origins = [
    "http://localhost:5173",

    "https://gdrive-rag-system.vercel.app",
]


# Add configured frontend URL
# when it is not already present.

if frontend_url:

    if frontend_url not in allowed_origins:

        allowed_origins.append(
            frontend_url
        )


app.add_middleware(
    CORSMiddleware,

    allow_origins=allowed_origins,

    allow_credentials=True,

    allow_methods=["*"],

    allow_headers=["*"],
)


# ==================================================
# ROUTERS
# ==================================================

app.include_router(
    auth_router
)

app.include_router(
    drive_router
)

app.include_router(
    query_router
)

app.include_router(
    conversations_router
)

app.include_router(
    folders_router
)

# ==================================================
# ROOT
# ==================================================

@app.get("/")
def root():

    return {
        "message":
            "Zentra API",

        "status":
            "running",
    }


# ==================================================
# HEALTH
# ==================================================

@app.get("/health")
def health():

    return {
        "status":
            "healthy",
    }