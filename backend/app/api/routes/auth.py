from fastapi import APIRouter, Request, HTTPException, Response
from fastapi.responses import RedirectResponse

from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

from config import settings


router = APIRouter(
    prefix="/api/auth",
    tags=["Authentication"],
)


# ==================================================
# GOOGLE SCOPES
# ==================================================

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
                "client_id": settings.GOOGLE_CLIENT_ID,

                "client_secret": settings.GOOGLE_CLIENT_SECRET,

                "auth_uri": (
                    "https://accounts.google.com/"
                    "o/oauth2/auth"
                ),

                "token_uri": (
                    "https://oauth2.googleapis.com/token"
                ),

                "redirect_uris": [
                    settings.GOOGLE_REDIRECT_URI
                ],
            }
        },

        scopes=GOOGLE_SCOPES,

        redirect_uri=settings.GOOGLE_REDIRECT_URI,
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

    # ==================================================
    # IMPORTANT:
    # CLEAR OLD ZENTRA SESSION
    # ==================================================

    request.session.clear()

    print(
        "Previous Zentra session cleared."
    )

    # ==================================================
    # CREATE GOOGLE FLOW
    # ==================================================

    flow = create_google_flow()

    # ==================================================
    # FORCE GOOGLE ACCOUNT SELECTOR
    # ==================================================

    authorization_url, state = (
        flow.authorization_url(
            access_type="offline",

            # Force Google to show account selection.
            #
            # This is important when switching between
            # multiple Google accounts.
            prompt="select_account consent",

            include_granted_scopes="true",
        )
    )

    # ==================================================
    # STORE OAUTH STATE
    # ==================================================

    request.session[
        "oauth_state"
    ] = state

    # ==================================================
    # STORE PKCE VERIFIER
    # ==================================================

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

    print("=" * 70)

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
        str(request.url)
    )

    print(
        "CONFIGURED REDIRECT:",
        settings.GOOGLE_REDIRECT_URI
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
    # BUILD AUTHORIZATION RESPONSE URL
    #
    # IMPORTANT FOR:
    # VERCEL -> RENDER PROXY
    # ==================================================

    query_string = (
        str(request.url.query)
        if request.url.query
        else ""
    )

    if query_string:

        auth_response_url = (
            f"{settings.GOOGLE_REDIRECT_URI}"
            f"?{query_string}"
        )

    else:

        auth_response_url = (
            settings.GOOGLE_REDIRECT_URI
        )

    print(
        "AUTHORIZATION RESPONSE URL:",
        auth_response_url
    )

    # ==================================================
    # EXCHANGE CODE FOR TOKEN
    # ==================================================

    try:

        flow.fetch_token(
            authorization_response=
                auth_response_url
        )

    except Exception as error:

        print()
        print("=" * 70)
        print("GOOGLE TOKEN EXCHANGE FAILED")
        print("=" * 70)

        print(
            "Error type:",
            type(error).__name__
        )

        print(
            "Error:",
            str(error)
        )

        print("=" * 70)

        raise HTTPException(
            status_code=400,
            detail=(
                "Google OAuth token exchange failed: "
                f"{error}"
            ),
        )

    credentials = (
        flow.credentials
    )

    # ==================================================
    # FETCH GOOGLE USER
    # ==================================================

    try:

        user_response = (
            flow.oauth2session.get(
                "https://www.googleapis.com/"
                "oauth2/v3/userinfo"
            )
        )

        user_response.raise_for_status()

        user_info = (
            user_response.json()
        )

    except Exception as error:

        print()
        print("=" * 70)
        print("GOOGLE USERINFO FAILED")
        print("=" * 70)

        print(
            "Error type:",
            type(error).__name__
        )

        print(
            "Error:",
            str(error)
        )

        print("=" * 70)

        raise HTTPException(
            status_code=400,
            detail=(
                "Unable to retrieve Google user "
                f"information: {error}"
            ),
        )

    # ==================================================
    # BUILD GOOGLE USER
    # ==================================================

    google_user = {
        "sub": user_info.get(
            "sub"
        ),

        "email": user_info.get(
            "email"
        ),

        "name": user_info.get(
            "name"
        ),

        "picture": user_info.get(
            "picture"
        ),
    }

    # ==================================================
    # VALIDATE GOOGLE IDENTITY
    # ==================================================

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
    # DEBUG:
    # VERIFY GOOGLE DRIVE TOKEN IDENTITY
    # ==================================================

    print()
    print("=" * 70)
    print("GOOGLE DRIVE TOKEN IDENTITY")
    print("=" * 70)

    print(
        "OAuth user email:",
        google_user.get("email")
    )

    print(
        "OAuth user name:",
        google_user.get("name")
    )

    print(
        "OAuth user sub:",
        google_user.get("sub")
    )

    print(
        "Has access token:",
        bool(credentials.token)
    )

    print(
        "Has refresh token:",
        bool(credentials.refresh_token)
    )

    print(
        "Credential scopes:",
        credentials.scopes
    )

    try:

        debug_drive = build(
            "drive",
            "v3",
            credentials=credentials,
            cache_discovery=False,
        )

        drive_about = (
            debug_drive.about()
            .get(
                fields="user"
            )
            .execute()
        )

        drive_user = (
            drive_about.get(
                "user",
                {}
            )
        )

        print()
        print(
            "DRIVE ACCOUNT:"
        )

        print(
            "Drive email:",
            drive_user.get(
                "emailAddress"
            )
        )

        print(
            "Drive name:",
            drive_user.get(
                "displayName"
            )
        )

        print(
            "Drive permission ID:",
            drive_user.get(
                "permissionId"
            )
        )

        # ==================================================
        # IMPORTANT ACCOUNT COMPARISON
        # ==================================================

        oauth_email = (
            google_user.get(
                "email"
            )
        )

        drive_email = (
            drive_user.get(
                "emailAddress"
            )
        )

        if (
            oauth_email
            and drive_email
            and oauth_email.lower()
            != drive_email.lower()
        ):

            print()
            print(
                "WARNING:"
            )

            print(
                "OAuth account and "
                "Drive account are different!"
            )

            print(
                "OAuth:",
                oauth_email
            )

            print(
                "Drive:",
                drive_email
            )

        else:

            print()
            print(
                "OAuth account and "
                "Drive account MATCH."
            )

    except Exception as error:

        print()
        print(
            "GOOGLE DRIVE TOKEN "
            "IDENTITY CHECK FAILED"
        )

        print(
            "Error type:",
            type(error).__name__
        )

        print(
            "Error:",
            str(error)
        )

    print("=" * 70)

    # ==================================================
    # STORE GOOGLE CREDENTIALS
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
    # STORE CURRENT GOOGLE USER
    # ==================================================

    request.session[
        "google_user"
    ] = google_user

    # ==================================================
    # REMOVE TEMPORARY OAUTH VALUES
    # ==================================================

    request.session.pop(
        "oauth_state",
        None,
    )

    request.session.pop(
        "oauth_code_verifier",
        None,
    )

    # ==================================================
    # REMOVE OLD DRIVE/FOLDER STATE
    #
    # IMPORTANT WHEN SWITCHING USERS
    # ==================================================

    request.session.pop(
        "active_folder_id",
        None,
    )

    request.session.pop(
        "active_folder_url",
        None,
    )

    request.session.pop(
        "active_folder_name",
        None,
    )

    # ==================================================
    # FINAL AUTH DEBUG
    # ==================================================

    print()
    print("=" * 70)
    print("AUTHENTICATED USER")
    print("=" * 70)

    print(
        request.session.get(
            "google_user"
        )
    )

    print(
        "Session has Google credentials:",
        bool(
            request.session.get(
                "google_credentials"
            )
        )
    )

    print("=" * 70)

    # ==================================================
    # FRONTEND REDIRECT
    # ==================================================

    frontend_url = (
        settings.FRONTEND_URL
        .rstrip("/")
    )

    print(
        "REDIRECTING TO:",
        frontend_url
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
    response: Response,
):

    # ==================================================
    # NEVER CACHE AUTH STATE
    # ==================================================

    response.headers[
        "Cache-Control"
    ] = (
        "no-store, "
        "no-cache, "
        "must-revalidate, "
        "private"
    )

    response.headers[
        "Pragma"
    ] = "no-cache"

    response.headers[
        "Expires"
    ] = "0"

    # ==================================================
    # GET CURRENT SESSION USER
    # ==================================================

    user = (
        request.session.get(
            "google_user"
        )
    )

    print()
    print(
        "AUTH /ME USER:",
        user
    )

    # ==================================================
    # NOT AUTHENTICATED
    # ==================================================

    if not user:

        return {
            "authenticated": False
        }

    # ==================================================
    # AUTHENTICATED
    # ==================================================

    return {
        "authenticated": True,

        "user": user,
    }


# ==================================================
# LOGOUT
# ==================================================

@router.post("/logout")
def logout(
    request: Request,
):

    current_user = (
        request.session.get(
            "google_user"
        )
    )

    print()
    print("=" * 70)
    print("LOGGING OUT")
    print("=" * 70)

    print(
        "USER:",
        current_user
    )

    # ==================================================
    # COMPLETELY CLEAR SESSION
    # ==================================================

    request.session.clear()

    print(
        "Session cleared."
    )

    print("=" * 70)

    return {
        "success": True
    }