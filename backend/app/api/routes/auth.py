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

    print()
    print("=" * 70)
    print("GOOGLE OAUTH LOGIN")
    print("=" * 70)

    print(
        "GOOGLE_CLIENT_ID:",
        settings.GOOGLE_CLIENT_ID,
    )

    print(
        "GOOGLE_REDIRECT_URI:",
        settings.GOOGLE_REDIRECT_URI,
    )

    print(
        "FRONTEND_URL:",
        settings.FRONTEND_URL,
    )

    # --------------------------------------------------
    # IMPORTANT
    #
    # Remove the currently authenticated Zentra user
    # before starting another Google OAuth flow.
    #
    # This prevents the previous application's session
    # from surviving an account switch.
    # --------------------------------------------------

    request.session.clear()

    print(
        "Previous Zentra session cleared."
    )

    # --------------------------------------------------
    # Create OAuth flow
    # --------------------------------------------------

    flow = create_google_flow()

    # --------------------------------------------------
    # Force Google account chooser
    # --------------------------------------------------

    authorization_url, state = (
        flow.authorization_url(
            access_type="offline",

            # IMPORTANT:
            # select_account forces Google to ask
            # which account should be used.
            prompt="select_account consent",

            include_granted_scopes="true",
        )
    )

    # --------------------------------------------------
    # Store OAuth state
    # --------------------------------------------------

    request.session[
        "oauth_state"
    ] = state

    # --------------------------------------------------
    # Store PKCE verifier if generated
    # --------------------------------------------------

    code_verifier = getattr(
        flow,
        "code_verifier",
        None,
    )

    if code_verifier:

        request.session[
            "oauth_code_verifier"
        ] = code_verifier

    print(
        "OAuth state stored."
    )

    print(
        "Redirecting to Google..."
    )

    print(
        "=" * 70
    )

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

    print()
    print("=" * 70)
    print("GOOGLE OAUTH CALLBACK")
    print("=" * 70)

    print(
        "REQUEST URL:",
        str(request.url),
    )

    print(
        "CONFIGURED REDIRECT:",
        settings.GOOGLE_REDIRECT_URI,
    )

    print("=" * 70)

    # ==================================================
    # AUTHORIZATION CODE
    # ==================================================

    code = request.query_params.get(
        "code"
    )

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

    # ==================================================
    # CREATE FLOW
    # ==================================================

    flow = create_google_flow()

    # ==================================================
    # RESTORE PKCE VERIFIER
    # ==================================================

    code_verifier = (
        request.session.get(
            "oauth_code_verifier"
        )
    )

    if code_verifier:

        flow.code_verifier = (
            code_verifier
        )

    # ==================================================
    # RESTORE STATE
    # ==================================================

    state = (
        request.session.get(
            "oauth_state"
        )
    )

    if state:

        flow.state = state

    # ==================================================
    # CORRECT RENDER HTTPS PROXY
    # ==================================================

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
        auth_response_url,
    )

    # ==================================================
    # EXCHANGE CODE FOR TOKEN
    # ==================================================

    flow.fetch_token(
        authorization_response=
            auth_response_url
    )

    credentials = (
        flow.credentials
    )

    # ==================================================
    # GOOGLE CREDENTIALS
    # ==================================================

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

    # ==================================================
    # FETCH GOOGLE USER
    # ==================================================

    user_response = (
        flow.oauth2session.get(
            "https://www.googleapis.com/oauth2/v3/userinfo"
        )
    )

    user_response.raise_for_status()

    user_info = (
        user_response.json()
    )

    # ==================================================
    # BUILD USER
    # ==================================================

    google_user = {
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

    # --------------------------------------------------
    # Validate Google identity
    # --------------------------------------------------

    if not google_user["sub"]:

        raise HTTPException(
            status_code=500,
            detail=(
                "Google did not return "
                "a user ID."
            ),
        )

    if not google_user["email"]:

        raise HTTPException(
            status_code=500,
            detail=(
                "Google did not return "
                "an email address."
            ),
        )

    # ==================================================
    # STORE USER IN SESSION
    # ==================================================

    request.session[
        "google_user"
    ] = google_user

    # ==================================================
    # CLEAN TEMPORARY OAUTH VALUES
    # ==================================================

    request.session.pop(
        "oauth_state",
        None,
    )

    request.session.pop(
        "oauth_code_verifier",
        None,
    )

    # --------------------------------------------------
    # IMPORTANT:
    # Do not carry the previous folder session forward.
    # The new user must start without an old folder.
    # --------------------------------------------------

    request.session.pop(
        "active_folder_id",
        None,
    )

    # ==================================================
    # DEBUG
    # ==================================================

    print()
    print("=" * 70)
    print("AUTHENTICATED USER")
    print("=" * 70)

    print(
        "SUB:",
        google_user["sub"],
    )

    print(
        "EMAIL:",
        google_user["email"],
    )

    print(
        "NAME:",
        google_user["name"],
    )

    print("=" * 70)

    print(
        "SESSION USER:",
        request.session.get(
            "google_user"
        ),
    )

    # ==================================================
    # FRONTEND REDIRECT
    # ==================================================

    frontend_url = (
        settings.FRONTEND_URL
        .rstrip("/")
    )

    print(
        "REDIRECTING TO:",
        frontend_url,
    )

    print("=" * 70)

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

    user = (
        request.session.get(
            "google_user"
        )
    )

    print(
        "AUTH /ME USER:",
        user,
    )

    if not user:

        return {
            "authenticated":
                False,
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

    print(
        "LOGGING OUT USER:",
        request.session.get(
            "google_user"
        ),
    )

    request.session.clear()

    return {
        "success":
            True,
    }