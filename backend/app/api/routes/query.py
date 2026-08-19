import json

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.services.rag import RAGService
from app.services.registry import get_conversation_memory


router = APIRouter(
    prefix="/api",
    tags=["RAG"],
)


# ==================================================
# REQUEST
# ==================================================

class QueryRequest(BaseModel):

    question: str

    top_k: int | None = Field(
        default=None,
        gt=0,
    )

    conversation_id: int | None = Field(
        default=None,
        gt=0,
    )


# ==================================================
# USER
# ==================================================

def get_user_id(
    request: Request,
) -> str:

    user = request.session.get(
        "google_user"
    )

    if not user:

        raise HTTPException(
            status_code=401,
            detail="User is not authenticated.",
        )

    user_id = user.get(
        "sub"
    )

    if not user_id:

        raise HTTPException(
            status_code=401,
            detail="Google user ID is missing.",
        )

    return user_id


# ==================================================
# RESOLVE CONVERSATION
# ==================================================

def resolve_conversation(
    request: Request,
    user_id: str,
    conversation_id: int | None,
    question: str,
):
    # --------------------------------------------------
    # NEW CONVERSATION
    # --------------------------------------------------

    if conversation_id is None:

        active_folder_id = request.session.get(
            "active_folder_id"
        )

        if not active_folder_id:

            raise HTTPException(
                status_code=400,
                detail=(
                    "No Drive folder has been analyzed "
                    "for this session."
                ),
            )

        conversation_id = (
            get_conversation_memory().create_conversation(
                user_id=user_id,
                folder_id=active_folder_id,
                title=question[:60],
            )
        )

        return (
            conversation_id,
            active_folder_id,
        )

    # --------------------------------------------------
    # EXISTING CONVERSATION
    # --------------------------------------------------

    if not get_conversation_memory().conversation_belongs_to_user(
        conversation_id,
        user_id,
    ):

        raise HTTPException(
            status_code=404,
            detail="Conversation not found.",
        )

    folder_id = (
        get_conversation_memory().get_conversation_folder(
            conversation_id,
            user_id,
        )
    )

    if not folder_id:

        raise HTTPException(
            status_code=400,
            detail=(
                "This conversation is not associated "
                "with a Drive folder."
            ),
        )

    return (
        conversation_id,
        folder_id,
    )


# ==================================================
# SSE
# ==================================================

def make_sse_event(
    event_name: str,
    payload: dict,
) -> str:

    return (
        f"event: {event_name}\n"
        f"data: {json.dumps(payload)}\n\n"
    )


# ==================================================
# NORMAL QUERY
# ==================================================

@router.post("/query")
def query_documents(
    payload: QueryRequest,
    request: Request,
):

    user_id = get_user_id(
        request
    )

    question = payload.question.strip()

    if not question:

        raise HTTPException(
            status_code=400,
            detail="Question cannot be empty.",
        )

    conversation_id, folder_id = (
        resolve_conversation(
            request=request,
            user_id=user_id,
            conversation_id=payload.conversation_id,
            question=question,
        )
    )

    try:

        # --------------------------------------------------
        # History
        # --------------------------------------------------

        history = get_conversation_memory().get_messages(
            conversation_id=conversation_id,
            limit=20,
        )

        # --------------------------------------------------
        # RAG
        # --------------------------------------------------

        rag = RAGService()

        result = rag.query(
            question=question,
            top_k=payload.top_k,
            history=history,
            user_id=user_id,

            # IMPORTANT:
            # Normal chat searches ALL files owned by
            # this Google user. The active folder is
            # conversation metadata, not a retrieval
            # restriction.
            folder_id=None,
        )

        answer = result.get(
            "answer",
            "",
        )

        sources = result.get(
            "sources",
            [],
        )

        # --------------------------------------------------
        # Save user message
        # --------------------------------------------------

        get_conversation_memory().add_message(
            conversation_id=conversation_id,
            role="user",
            content=question,
        )

        # --------------------------------------------------
        # Save assistant message
        # --------------------------------------------------

        get_conversation_memory().add_message(
            conversation_id=conversation_id,
            role="assistant",
            content=answer,
            sources=sources,
        )

        request.session[
            "active_folder_id"
        ] = folder_id

        return {
            "conversation_id":
                conversation_id,

            "folder_id":
                folder_id,

            "answer":
                answer,

            "sources":
                sources,
        }

    except HTTPException:
        raise

    except Exception as error:

        print(
            f"RAG query error: {error}"
        )

        raise HTTPException(
            status_code=500,
            detail=str(error),
        )


# ==================================================
# STREAMING QUERY
# ==================================================

@router.post("/query/stream")
def query_documents_stream(
    payload: QueryRequest,
    request: Request,
):

    user_id = get_user_id(
        request
    )

    question = payload.question.strip()

    if not question:

        raise HTTPException(
            status_code=400,
            detail="Question cannot be empty.",
        )

    conversation_id, folder_id = (
        resolve_conversation(
            request=request,
            user_id=user_id,
            conversation_id=payload.conversation_id,
            question=question,
        )
    )

    # ==================================================
    # RETRIEVAL
    # ==================================================

    try:

        history = get_conversation_memory().get_messages(
            conversation_id=conversation_id,
            limit=20,
        )

        rag = RAGService()

        results = (
            rag.retrieve_with_history(
                question=question,
                history=history,
                top_k=payload.top_k,
                user_id=user_id,

                # IMPORTANT:
                # Search ALL files for this user.
                folder_id=None,
            )
        )

        context = rag.build_context(
            results
        )

        # Use RAG's own source builder so normal and
        # streaming endpoints return the same unique
        # file-level source structure.
        sources = rag.build_sources(
            results
        )

    except HTTPException:
        raise

    except Exception as error:

        print(
            f"Streaming retrieval error: {error}"
        )

        raise HTTPException(
            status_code=500,
            detail=str(error),
        )

    # ==================================================
    # STREAM GENERATOR
    # ==================================================

    def event_generator():

        full_answer = ""

        try:

            # --------------------------------------------------
            # Metadata
            # --------------------------------------------------

            metadata_payload = {
                "conversation_id":
                    conversation_id,

                "folder_id":
                    folder_id,

                "sources":
                    sources,
            }

            yield make_sse_event(
                "metadata",
                metadata_payload,
            )

            # --------------------------------------------------
            # GROQ STREAM
            # --------------------------------------------------

            for event in rag.stream_answer(
                query=question,
                context=context,
                history=history,
            ):

                event_type = event.get(
                    "type"
                )

                # ==========================================
                # TOKEN
                # ==========================================

                if event_type == "token":

                    token = event.get(
                        "content",
                        "",
                    )

                    if not token:
                        continue

                    full_answer += token

                    yield make_sse_event(
                        "token",
                        {
                            "content": token,
                        },
                    )

                # ==========================================
                # ERROR
                # ==========================================

                elif event_type == "error":

                    yield make_sse_event(
                        "error",
                        {
                            "message":
                                event.get(
                                    "content",
                                    "Generation error.",
                                ),
                        },
                    )

                    return

                # ==========================================
                # DONE
                # ==========================================

                elif event_type == "done":

                    # --------------------------------------
                    # Save user message
                    # --------------------------------------

                    get_conversation_memory().add_message(
                        conversation_id=
                            conversation_id,

                        role="user",

                        content=
                            question,
                    )

                    # --------------------------------------
                    # Save assistant message
                    # --------------------------------------

                    get_conversation_memory().add_message(
                        conversation_id=
                            conversation_id,

                        role="assistant",

                        content=
                            full_answer,

                        sources=
                            sources,
                    )

                    request.session[
                        "active_folder_id"
                    ] = folder_id

                    yield make_sse_event(
                        "done",
                        {
                            "conversation_id":
                                conversation_id,

                            "folder_id":
                                folder_id,

                            "sources":
                                sources,
                        },
                    )

                    return

        except Exception as error:

            print(
                f"Streaming generation error: "
                f"{error}"
            )

            yield make_sse_event(
                "error",
                {
                    "message":
                        str(error),
                },
            )

    # ==================================================
    # RESPONSE
    # ==================================================

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control":
                "no-cache",

            "Connection":
                "keep-alive",

            "X-Accel-Buffering":
                "no",

            "Access-Control-Allow-Origin":
                request.headers.get("origin") or settings.FRONTEND_URL,


            "Access-Control-Allow-Credentials":
                "true",
        },
    )