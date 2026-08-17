import os


# ==================================================
# ENVIRONMENT
# ==================================================

ENVIRONMENT = os.getenv(
    "ENVIRONMENT",
    "development",
).lower()


# ==================================================
# OAUTH TRANSPORT
# ==================================================

# Only allow insecure OAuth locally.
#
# Production:
# Vercel -> HTTPS
# Render -> HTTPS
#
# Therefore OAuth should NOT use insecure transport
# in production.

if ENVIRONMENT != "production":

    os.environ[
        "OAUTHLIB_INSECURE_TRANSPORT"
    ] = "1"


# ==================================================
# FASTAPI
# ==================================================

from fastapi import FastAPI

from fastapi.middleware.cors import (
    CORSMiddleware,
)

from starlette.middleware.sessions import (
    SessionMiddleware,
)

from config import settings


# ==================================================
# ROUTERS
# ==================================================

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
# FRONTEND
# ==================================================

frontend_url = (
    settings.FRONTEND_URL
    .strip()
    .rstrip("/")
)


print("=" * 70)
print("ZENTRA APPLICATION STARTUP")
print("=" * 70)

print(
    f"Environment: {ENVIRONMENT}"
)

print(
    f"Frontend URL: {frontend_url}"
)

print(
    f"Production: "
    f"{ENVIRONMENT == 'production'}"
)

print("=" * 70)


# ==================================================
# SESSION COOKIE
# ==================================================

# Vercel frontend and Render backend are
# different sites.
#
# Therefore production authentication requires:
#
# SameSite=None
# Secure=True
#
# The browser will then send the session cookie
# with frontend -> backend requests.

if ENVIRONMENT == "production":

    session_same_site = "none"

    session_secure = True

else:

    session_same_site = "lax"

    session_secure = False


# Allow explicit settings to override the
# defaults only during development.

if ENVIRONMENT != "production":

    configured_same_site = getattr(
        settings,
        "SESSION_COOKIE_SAMESITE",
        None,
    )

    configured_secure = getattr(
        settings,
        "SESSION_COOKIE_SECURE",
        None,
    )

    if configured_same_site:

        session_same_site = (
            configured_same_site
        )

    if configured_secure is not None:

        session_secure = (
            configured_secure
        )


print(
    f"Session SameSite: "
    f"{session_same_site}"
)

print(
    f"Session Secure: "
    f"{session_secure}"
)


# ==================================================
# SESSION MIDDLEWARE
# ==================================================

app.add_middleware(
    SessionMiddleware,

    secret_key=settings.SESSION_SECRET,

    session_cookie=(
        "gdrive_rag_session"
    ),

    max_age=60 * 60 * 24 * 14,

    same_site=session_same_site,

    https_only=session_secure,
)


# ==================================================
# CORS
# ==================================================

allowed_origins = [
    "http://localhost:5173",

    "http://localhost:3000",

    "https://gdrive-rag-system.vercel.app",
]


# Add configured frontend URL.

if frontend_url:

    if frontend_url not in allowed_origins:

        allowed_origins.append(
            frontend_url
        )


# Remove duplicates.

allowed_origins = list(
    dict.fromkeys(
        allowed_origins
    )
)


print(
    "Allowed CORS origins:"
)

for origin in allowed_origins:

    print(
        f"  - {origin}"
    )


app.add_middleware(
    CORSMiddleware,

    allow_origins=allowed_origins,

    allow_credentials=True,

    allow_methods=[
        "*"
    ],

    allow_headers=[
        "*"
    ],
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
        "message": "Zentra API",
        "status": "running",
    }


# ==================================================
# HEALTH
# ==================================================

@app.get("/health")
def health():

    return {
        "status": "healthy",
    }


# ==================================================
# DEBUG SESSION
# ==================================================

@app.get("/debug/session")
def debug_session(
    request,
):

    user = request.session.get(
        "google_user"
    )

    credentials = request.session.get(
        "google_credentials"
    )

    return {
        "session_exists": bool(
            request.session
        ),

        "authenticated": bool(
            user
        ),

        "google_user": user,

        "has_google_credentials": bool(
            credentials
        ),

        "active_folder_id":
            request.session.get(
                "active_folder_id"
            ),
    }