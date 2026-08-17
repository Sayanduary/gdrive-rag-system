from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import RedirectResponse
from google_auth_oauthlib.flow import Flow

from config import settings


router = APIRouter(
    prefix="/api/auth",
    tags=["Authentication"],
)


GOOGLE_SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/drive.readonly",
]


# ==================================================
# GOOGLE FLOW
# ==================================================

def create_google_flow():

    return Flow.from_client_config(
        {
            "web": {
                "client_id":
                    settings.GOOGLE_CLIENT_ID,

                "client_secret":
                    settings.GOOGLE_CLIENT_SECRET,

                "auth_uri":
                    "https://accounts.google.com/o/oauth2/auth",

                "token_uri":
                    "https://oauth2.googleapis.com/token",

                "redirect_uris": [
                    settings.GOOGLE_REDIRECT_URI
                ],
            }
        },

        scopes=GOOGLE_SCOPES,

        redirect_uri=
            settings.GOOGLE_REDIRECT_URI,
    )


# ==================================================
# GOOGLE LOGIN
# ==================================================

@router.get("/google")
def google_login(
    request: Request,
):

    print(
        "========================================"
    )

    print(
        "GOOGLE OAUTH LOGIN"
    )

    print(
        "GOOGLE_CLIENT_ID:",
        settings.GOOGLE_CLIENT_ID
    )

    print(
        "GOOGLE_REDIRECT_URI:",
        settings.GOOGLE_REDIRECT_URI
    )

    print(
        "FRONTEND_URL:",
        settings.FRONTEND_URL
    )

    print(
        "========================================"
    )

    flow = create_google_flow()

    authorization_url, state = (
        flow.authorization_url(
            access_type="offline",
            prompt="consent",
            include_granted_scopes="true",
        )
    )

    request.session[
        "oauth_state"
    ] = state

    code_verifier = getattr(
        flow,
        "code_verifier",
        None,
    )

    if code_verifier:

        request.session[
            "oauth_code_verifier"
        ] = code_verifier

    return RedirectResponse(
        authorization_url
    )


# ==================================================
# GOOGLE CALLBACK
# ==================================================

@router.get("/google/callback")
def google_callback(
    request: Request,
):

    print(
        "========================================"
    )

    print(
        "GOOGLE OAUTH CALLBACK"
    )

    print(
        "REQUEST URL:",
        str(request.url)
    )

    print(
        "CONFIGURED REDIRECT:",
        settings.GOOGLE_REDIRECT_URI
    )

    print(
        "========================================"
    )

    code = request.query_params.get(
        "code"
    )

    # ------------------------------------------
    # OAuth error
    # ------------------------------------------

    if not code:

        error = request.query_params.get(
            "error"
        )

        if error:

            raise HTTPException(
                status_code=400,
                detail=(
                    "Google OAuth error: "
                    f"{error}"
                ),
            )

        raise HTTPException(
            status_code=400,
            detail=(
                "Missing Google authorization "
                "code."
            ),
        )

    # ------------------------------------------
    # Create OAuth flow
    # ------------------------------------------

    flow = create_google_flow()

    # ------------------------------------------
    # Restore PKCE verifier
    # ------------------------------------------

    code_verifier = request.session.get(
        "oauth_code_verifier"
    )

    if code_verifier:

        flow.code_verifier = (
            code_verifier
        )

    # ------------------------------------------
    # Restore state
    # ------------------------------------------

    state = request.session.get(
        "oauth_state"
    )

    if state:

        flow.state = state

    # ------------------------------------------
    # Correct proxy HTTPS
    # ------------------------------------------

    auth_response_url = str(
        request.url
    )

    if (
        settings.GOOGLE_REDIRECT_URI.startswith(
            "https://"
        )
        and auth_response_url.startswith(
            "http://"
        )
    ):

        auth_response_url = (
            "https://"
            + auth_response_url[
                len("http://"):
            ]
        )

    print(
        "AUTHORIZATION RESPONSE URL:",
        auth_response_url
    )

    # ------------------------------------------
    # Exchange authorization code
    # ------------------------------------------

    flow.fetch_token(
        authorization_response=
            auth_response_url
    )

    credentials = (
        flow.credentials
    )

    # ------------------------------------------
    # Store Google credentials
    # ------------------------------------------

    request.session[
        "google_credentials"
    ] = {
        "token":
            credentials.token,

        "refresh_token":
            credentials.refresh_token,

        "token_uri":
            credentials.token_uri,

        "client_id":
            credentials.client_id,

        "client_secret":
            credentials.client_secret,

        "scopes":
            credentials.scopes,
    }

    # ------------------------------------------
    # Fetch Google user
    # ------------------------------------------

    user_response = (
        flow.oauth2session.get(
            "https://www.googleapis.com/oauth2/v3/userinfo"
        )
    )

    user_response.raise_for_status()

    user_info = (
        user_response.json()
    )

    request.session[
        "google_user"
    ] = {
        "sub":
            user_info.get(
                "sub"
            ),

        "email":
            user_info.get(
                "email"
            ),

        "name":
            user_info.get(
                "name"
            ),

        "picture":
            user_info.get(
                "picture"
            ),
    }

    # ------------------------------------------
    # Remove temporary OAuth values
    # ------------------------------------------

    request.session.pop(
        "oauth_state",
        None,
    )

    request.session.pop(
        "oauth_code_verifier",
        None,
    )

    print(
        "AUTHENTICATED USER:",
        request.session.get(
            "google_user"
        )
    )

    # ------------------------------------------
    # Redirect to frontend
    # ------------------------------------------

    frontend_url = (
        settings.FRONTEND_URL
        .rstrip("/")
    )

    print(
        "REDIRECTING TO:",
        frontend_url
    )

    return RedirectResponse(
        url=frontend_url
    )


# ==================================================
# CURRENT USER
# ==================================================

@router.get("/me")
def get_current_user(
    request: Request,
):

    user = request.session.get(
        "google_user"
    )

    print(
        "AUTH /ME USER:",
        user
    )

    if not user:

        return {
            "authenticated":
                False
        }

    return {
        "authenticated":
            True,

        "user":
            user,
    }


# ==================================================
# LOGOUT
# ==================================================

@router.post("/logout")
def logout(
    request: Request,
):

    request.session.clear()

    return {
        "success":
            True
    }