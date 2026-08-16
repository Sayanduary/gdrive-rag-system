from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.services.memory import ConversationMemory


router = APIRouter(
    prefix="/api/conversations",
    tags=["Conversations"]
)


memory = ConversationMemory()


class RenameConversationRequest(BaseModel):
    title: str


def get_user_id(
    request: Request
) -> str:

    user = request.session.get(
        "google_user"
    )

    if not user:
        raise HTTPException(
            status_code=401,
            detail="User is not authenticated."
        )

    user_id = user.get("sub")

    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="Google user ID is missing."
        )

    return user_id


# ==================================================
# CREATE CONVERSATION
# ==================================================

@router.post("")
def create_conversation(
    request: Request
):

    user_id = get_user_id(request)

    # New conversations created explicitly from
    # the UI should use the currently active folder.
    folder_id = request.session.get(
        "active_folder_id"
    )

    if not folder_id:
        raise HTTPException(
            status_code=400,
            detail=(
                "No Drive folder has been analyzed "
                "for this session."
            )
        )

    conversation_id = (
        memory.create_conversation(
            user_id=user_id,
            folder_id=folder_id,
            title="New Chat"
        )
    )

    return {
        "conversation_id": conversation_id,
        "folder_id": folder_id,
    }


# ==================================================
# LIST CONVERSATIONS
# ==================================================

@router.get("")
def list_conversations(
    request: Request
):

    user_id = get_user_id(request)

    conversations = (
        memory.get_user_conversations(
            user_id
        )
    )

    return {
        "conversations": conversations
    }


# ==================================================
# GET CONVERSATION
# ==================================================

@router.get("/{conversation_id}")
def get_conversation(
    conversation_id: int,
    request: Request
):

    user_id = get_user_id(request)

    if not memory.conversation_belongs_to_user(
        conversation_id,
        user_id
    ):
        raise HTTPException(
            status_code=404,
            detail="Conversation not found."
        )

    messages = memory.get_messages(
        conversation_id=conversation_id
    )

    folder_id = (
        memory.get_conversation_folder(
            conversation_id,
            user_id
        )
    )

    # Restore the folder associated with this chat
    # into the current session.
    if folder_id:
        request.session[
            "active_folder_id"
        ] = folder_id

    return {
        "conversation_id": conversation_id,
        "folder_id": folder_id,
        "messages": messages
    }


# ==================================================
# RENAME CONVERSATION
# ==================================================

@router.patch("/{conversation_id}")
def rename_conversation(
    conversation_id: int,
    payload: RenameConversationRequest,
    request: Request
):

    user_id = get_user_id(request)

    title = payload.title.strip()

    if not title:
        raise HTTPException(
            status_code=400,
            detail="Conversation title cannot be empty."
        )

    if not memory.conversation_belongs_to_user(
        conversation_id,
        user_id
    ):
        raise HTTPException(
            status_code=404,
            detail="Conversation not found."
        )

    memory.rename_conversation(
        conversation_id,
        user_id,
        title
    )

    return {
        "success": True
    }


# ==================================================
# DELETE CONVERSATION
# ==================================================

@router.delete("/{conversation_id}")
def delete_conversation(
    conversation_id: int,
    request: Request
):

    user_id = get_user_id(request)

    if not memory.conversation_belongs_to_user(
        conversation_id,
        user_id
    ):
        raise HTTPException(
            status_code=404,
            detail="Conversation not found."
        )

    memory.delete_conversation(
        conversation_id,
        user_id
    )

    return {
        "success": True
    }