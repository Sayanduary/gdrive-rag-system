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
# LOGIN
# ==================================================

@router.get("/google")
def google_login(
    request: Request,
):

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
# CALLBACK
# ==================================================

@router.get("/google/callback")
def google_callback(
    request: Request,
):

    code = request.query_params.get(
        "code"
    )

    # ------------------------------------------
    # Google returned an OAuth error
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
    # Recreate flow
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
    # Restore OAuth state
    # ------------------------------------------

    state = request.session.get(
        "oauth_state"
    )

    if state:

        flow.state = state

    # ------------------------------------------
    # Render's proxy terminates HTTPS.
    #
    # Make sure Google's callback URL is
    # interpreted as HTTPS.
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
                len("http://"):]
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
    # Get Google user
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
    # Cleanup temporary OAuth state
    # ------------------------------------------

    request.session.pop(
        "oauth_state",
        None,
    )

    request.session.pop(
        "oauth_code_verifier",
        None,
    )

    # ------------------------------------------
    # Redirect to frontend
    # ------------------------------------------

    frontend_url = (
        settings.FRONTEND_URL
        .rstrip("/")
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