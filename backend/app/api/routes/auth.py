from urllib.parse import urlparse
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import RedirectResponse
from google_auth_oauthlib.flow import Flow

from config import settings


router = APIRouter(
    prefix="/api/auth",
    tags=["Authentication"]
)


GOOGLE_SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/drive.readonly",
]


def create_google_flow():

    return Flow.from_client_config(
        {
            "web": {
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [
                    settings.GOOGLE_REDIRECT_URI
                ],
            }
        },
        scopes=GOOGLE_SCOPES,
        redirect_uri=settings.GOOGLE_REDIRECT_URI,
    )


@router.get("/google")
def google_login(request: Request):

    referer = request.query_params.get("redirect_url") or request.headers.get("referer")
    if referer:
        parsed = urlparse(referer)
        if parsed.scheme and parsed.netloc:
            request.session["frontend_url"] = f"{parsed.scheme}://{parsed.netloc}"

    flow = create_google_flow()

    authorization_url, state = flow.authorization_url(
        access_type="offline",
        prompt="consent",
    )

    request.session["oauth_state"] = state

    code_verifier = getattr(
        flow,
        "code_verifier",
        None
    )

    if code_verifier:
        request.session["oauth_code_verifier"] = (
            code_verifier
        )

    return RedirectResponse(
        authorization_url
    )



@router.get("/google/callback")
def google_callback(request: Request):

    code = request.query_params.get("code")

    if not code:

        error = request.query_params.get("error")

        if error:
            raise HTTPException(
                status_code=400,
                detail=f"Google OAuth error: {error}"
            )

        raise HTTPException(
            status_code=400,
            detail=(
                "Missing Google authorization code. "
                "Start login from /api/auth/google."
            )
        )

    flow = create_google_flow()

    code_verifier = request.session.get(
        "oauth_code_verifier"
    )

    if code_verifier:
        flow.code_verifier = code_verifier

    state = request.session.get(
        "oauth_state"
    )

    if state:
        flow.state = state

    auth_response_url = str(request.url)
    if settings.GOOGLE_REDIRECT_URI.startswith("https://") and auth_response_url.startswith("http://"):
        auth_response_url = auth_response_url.replace("http://", "https://", 1)

    flow.fetch_token(
        authorization_response=auth_response_url
    )


    credentials = flow.credentials

    request.session["google_credentials"] = {
        "token": credentials.token,
        "refresh_token": credentials.refresh_token,
        "token_uri": credentials.token_uri,
        "client_id": credentials.client_id,
        "client_secret": credentials.client_secret,
        "scopes": credentials.scopes,
    }

    user_response = flow.oauth2session.get(
        "https://www.googleapis.com/oauth2/v3/userinfo"
    )

    user_response.raise_for_status()

    user_info = user_response.json()

    request.session["google_user"] = {
        "sub": user_info.get("sub"),
        "email": user_info.get("email"),
        "name": user_info.get("name"),
        "picture": user_info.get("picture"),
    }

    request.session.pop(
        "oauth_state",
        None
    )

    request.session.pop(
        "oauth_code_verifier",
        None
    )

    frontend_url = request.session.pop(
        "frontend_url",
        None
    ) or settings.FRONTEND_URL

    return RedirectResponse(
        f"{frontend_url.rstrip('/')}/"
    )




@router.get("/me")
def get_current_user(request: Request):

    user = request.session.get(
        "google_user"
    )

    if not user:

        return {
            "authenticated": False
        }

    return {
        "authenticated": True,
        "user": user
    }


@router.post("/logout")
def logout(request: Request):

    request.session.clear()

    return {
        "success": True
    }