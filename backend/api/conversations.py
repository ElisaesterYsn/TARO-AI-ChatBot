from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from services.conversation_service import (
    create_conversation,
    get_conversations,
    get_conversation,
    get_messages,
    add_message,
    update_conversation_title,
)

from services.ai_service import generate_response, stream_response, generate_title, extract_memories
from services.memory_service import get_memories_as_text, save_memory


router = APIRouter(prefix="/conversations", tags=["Conversations"])


class CreateConversationRequest(BaseModel):
    title: str = "New Chat"


class CreateConversationResponse(BaseModel):
    id: int
    title: str


class SendMessageRequest(BaseModel):
    content: str


@router.post("", response_model=CreateConversationResponse)
def create_new_conversation(request: CreateConversationRequest):
    conversation_id = create_conversation(request.title)

    return {
        "id": conversation_id,
        "title": request.title,
    }


@router.get("")
def list_all_conversations():
    return get_conversations()


@router.get("/{conversation_id}")
def get_single_conversation(conversation_id: int):
    conversation = get_conversation(conversation_id)

    if conversation is None:
        raise HTTPException(
            status_code=404,
            detail="Conversation not found"
        )

    messages = get_messages(conversation_id)

    return {
        "conversation": conversation,
        "messages": messages,
    }


@router.post("/{conversation_id}/messages")
def send_message(
    conversation_id: int,
    request: SendMessageRequest
):
    conversation = get_conversation(conversation_id)

    if conversation is None:
        raise HTTPException(
            status_code=404,
            detail="Conversation not found"
        )

    user_message = request.content.strip()

    if not user_message:
        raise HTTPException(
            status_code=400,
            detail="Message cannot be empty"
        )

    # Get previous conversation history
    previous_messages = get_messages(conversation_id)

    # Check whether this is the first message
    is_first_message = len(previous_messages) == 0

    # Build messages for the AI
    ai_messages = [
        {
            "role": message["role"],
            "content": message["content"],
        }
        for message in previous_messages
    ]

    # Add the new user message
    ai_messages.append({
        "role": "user",
        "content": user_message,
    })

    # Generate TARO's response
    response = generate_response(ai_messages)

    # Save user's message
    add_message(
        conversation_id,
        "user",
        user_message
    )

    # Save TARO's response
    add_message(
        conversation_id,
        "assistant",
        response
    )

    # Generate a title only for the first message
    title = conversation["title"]

    if is_first_message:
        try:
            title = generate_title(user_message)

            update_conversation_title(
                conversation_id,
                title
            )

        except Exception as error:
            print(f"Title generation failed: {error}")

    return {
        "response": response,
        "title": title,
    }

@router.post("/{conversation_id}/messages/stream")
def stream_message(
    conversation_id: int,
    request: SendMessageRequest,
    background_tasks: BackgroundTasks,
):
    conversation = get_conversation(conversation_id)

    if conversation is None:
        raise HTTPException(
            status_code=404,
            detail="Conversation not found"
        )

    user_message = request.content.strip()

    if not user_message:
        raise HTTPException(
            status_code=400,
            detail="Message cannot be empty"
        )

    previous_messages = get_messages(conversation_id)

    is_first_message = len(previous_messages) == 0

    # Load all memories and inject into the system prompt
    memory_context = get_memories_as_text()

    ai_messages = [
        {
            "role": message["role"],
            "content": message["content"],
        }
        for message in previous_messages
    ]

    ai_messages.append({
        "role": "user",
        "content": user_message,
    })

    # Mutable container so the generator can pass the full response
    # back to the background task after streaming completes
    result: dict = {"full_response": ""}

    def generate():
        try:
            for chunk in stream_response(ai_messages, memory_context=memory_context):
                result["full_response"] += chunk
                yield chunk

            # Persist messages as soon as streaming finishes
            add_message(conversation_id, "user", user_message)
            add_message(conversation_id, "assistant", result["full_response"])

            # Generate title on the first message
            if is_first_message:
                try:
                    title = generate_title(user_message)
                    update_conversation_title(conversation_id, title)
                except Exception as error:
                    print(f"[TARO] Title generation failed: {error}")

        except Exception:
            raise

    def run_memory_extraction():
        """
        Runs after the StreamingResponse is fully sent to the client.
        At this point result["full_response"] is complete.
        """
        full_response = result.get("full_response", "")

        if not full_response:
            return

        try:
            memories = extract_memories(user_message, full_response)

            for memory in memories:
                save_memory(
                    key=memory["key"],
                    value=memory["value"],
                    type=memory["type"],
                )

            if memories:
                print(f"[TARO Memory] Saved {len(memories)} new memory/memories.")

        except Exception as error:
            print(f"[TARO Memory] Extraction failed: {error}")

    # Schedule extraction to run after the response is fully sent
    background_tasks.add_task(run_memory_extraction)

    return StreamingResponse(
        generate(),
        media_type="text/plain"
    )

@router.delete("/{conversation_id}")
def delete_conversation(conversation_id: int):
    conversation = get_conversation(conversation_id)

    if conversation is None:
        raise HTTPException(
            status_code=404,
            detail="Conversation not found"
        )

    # Delete messages first
    from database.db import get_connection

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        DELETE FROM messages
        WHERE conversation_id = ?
        """,
        (conversation_id,)
    )

    cursor.execute(
        """
        DELETE FROM conversations
        WHERE id = ?
        """,
        (conversation_id,)
    )

    connection.commit()
    connection.close()

    return {
        "message": "Conversation deleted"
    }
