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

from services.ai_service import (
    generate_response,
    stream_response,
    stream_response_with_image,
    generate_title,
    extract_memories,
    detect_emotion,
)
from services.memory_service import get_memories_as_text, save_memory


router = APIRouter(prefix="/conversations", tags=["Conversations"])


class CreateConversationRequest(BaseModel):
    title: str = "New Chat"


class CreateConversationResponse(BaseModel):
    id: int
    title: str


class SendMessageRequest(BaseModel):
    content: str
    image_base64: str | None = None  # optional base64-encoded image for vision


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
        raise HTTPException(status_code=404, detail="Conversation not found")

    user_message = request.content.strip()

    if not user_message:
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    previous_messages = get_messages(conversation_id)
    is_first_message = len(previous_messages) == 0
    memory_context = get_memories_as_text()
    has_image = bool(request.image_base64)

    ai_messages = [
        {"role": m["role"], "content": m["content"]}
        for m in previous_messages
    ]
    ai_messages.append({"role": "user", "content": user_message})

    # Emotion detection — fast keyword scan only, no extra Ollama call.
    # This keeps the streaming path free for the main response.
    tone = "neutral"
    if not has_image:
        tone = detect_emotion(user_message)
        if tone != "neutral":
            print(f"[TARO Emotion] Detected: {tone}")

    result: dict = {"full_response": ""}

    def generate():
        try:
            if has_image:
                chunks = stream_response_with_image(
                    ai_messages,
                    image_base64=request.image_base64,
                    memory_context=memory_context,
                    tone=tone,
                )
            else:
                chunks = stream_response(
                    ai_messages,
                    memory_context=memory_context,
                    tone=tone,
                )

            for chunk in chunks:
                result["full_response"] += chunk
                yield chunk

            # Persist messages immediately after streaming
            add_message(conversation_id, "user", user_message)
            add_message(conversation_id, "assistant", result["full_response"])

        except Exception:
            raise

    def run_background_tasks():
        full_response = result.get("full_response", "")
        if not full_response:
            return

        # Title generation — only on first message, runs after stream so it
        # doesn't compete with the main Ollama call
        if is_first_message:
            try:
                title = generate_title(user_message)
                update_conversation_title(conversation_id, title)
            except Exception as error:
                print(f"[TARO] Title generation failed: {error}")

        # Memory extraction — skip for image messages and very short exchanges
        # (greetings, one-liners) to avoid unnecessary Ollama calls
        if not has_image and len(user_message) > 20:
            try:
                memories = extract_memories(user_message, full_response)
                for memory in memories:
                    save_memory(
                        key=memory["key"],
                        value=memory["value"],
                        type=memory["type"],
                    )
                if memories:
                    print(f"[TARO Memory] Saved {len(memories)} memory/memories.")
            except Exception as error:
                print(f"[TARO Memory] Extraction failed: {error}")

    background_tasks.add_task(run_background_tasks)

    return StreamingResponse(generate(), media_type="text/plain")

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
