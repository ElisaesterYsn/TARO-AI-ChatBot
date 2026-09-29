from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from api.deps import get_current_user
from services.conversation_service import (
    create_conversation,
    get_conversations,
    get_conversation,
    get_messages,
    add_message,
    update_conversation_title,
    delete_conversation,
)
from services.ai_service import (
    generate_response,
    stream_response,
    stream_response_with_image,
    generate_title,
    generate_summary,
    extract_memories,
    detect_emotion,
)
from services.memory_service import get_memories_as_text, save_memory
from services.summary_service import save_summary, get_summaries_as_text


router = APIRouter(prefix="/conversations", tags=["Conversations"])


class CreateConversationRequest(BaseModel):
    title: str = "New Chat"


class CreateConversationResponse(BaseModel):
    id: int
    title: str


class SendMessageRequest(BaseModel):
    content: str
    image_base64: str | None = None


@router.post("", response_model=CreateConversationResponse)
def create_new_conversation(
    request: CreateConversationRequest,
    current_user: dict = Depends(get_current_user),
):
    conversation_id = create_conversation(current_user["id"], request.title)
    return {"id": conversation_id, "title": request.title}


@router.get("")
def list_all_conversations(current_user: dict = Depends(get_current_user)):
    return get_conversations(current_user["id"])


@router.get("/{conversation_id}")
def get_single_conversation(
    conversation_id: int,
    current_user: dict = Depends(get_current_user),
):
    conversation = get_conversation(conversation_id, current_user["id"])

    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    messages = get_messages(conversation_id)
    return {"conversation": conversation, "messages": messages}


@router.post("/{conversation_id}/messages/stream")
def stream_message(
    conversation_id: int,
    request: SendMessageRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
):
    user_id = current_user["id"]
    conversation = get_conversation(conversation_id, user_id)

    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    user_message = request.content.strip()

    if not user_message:
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    previous_messages = get_messages(conversation_id)
    is_first_message = len(previous_messages) == 0
    memory_context = get_memories_as_text(user_id)
    print(f"[TARO Memory] Retrieved for user {user_id}: {repr(memory_context)}")
    
    summary_context = get_summaries_as_text(user_id, limit=5)
    has_image = bool(request.image_base64)

    ai_messages = [
        {"role": m["role"], "content": m["content"]}
        for m in previous_messages
    ]
    ai_messages.append({"role": "user", "content": user_message})

    tone = "neutral"
    if not has_image:
        tone = detect_emotion(user_message)
        if tone != "neutral":
            print(f"[TARO Emotion] Detected: {tone}")

    result: dict = {"full_response": ""}

    def generate():
        try:
            chunks = (
                stream_response_with_image(
                    ai_messages,
                    image_base64=request.image_base64,
                    memory_context=memory_context,
                    summary_context=summary_context,
                    tone=tone,
                )
                if has_image
                else stream_response(
                    ai_messages,
                    memory_context=memory_context,
                    summary_context=summary_context,
                    tone=tone,
                )
            )

            for chunk in chunks:
                result["full_response"] += chunk
                yield chunk

            add_message(conversation_id, "user", user_message)
            add_message(conversation_id, "assistant", result["full_response"])

        except Exception:
            raise

    def run_background_tasks():
        import time
        full_response = result.get("full_response", "")
        if not full_response:
            return

        # Small delay so Ollama fully releases from the stream before we call it again
        time.sleep(1)

        if is_first_message:
            try:
                title = generate_title(user_message)
                update_conversation_title(conversation_id, title)
                print(f"[TARO] Title set: {title}")
            except Exception as e:
                print(f"[TARO] Title generation failed: {e}")

            # Extra delay between title gen and memory extraction
            time.sleep(1)

        # Memory extraction — skip for image messages and very short exchanges
        if not has_image and len(user_message) > 8:
            try:
                memories = extract_memories(user_message, full_response)
                for memory in memories:
                    save_memory(
                        user_id=user_id,
                        key=memory["key"],
                        value=memory["value"],
                        type=memory["type"],
                    )
                if memories:
                    print(f"[TARO Memory] Saved {len(memories)} memory/memories for user {user_id}: {[m['key'] for m in memories]}")
                else:
                    print(f"[TARO Memory] No memories extracted from: '{user_message[:60]}'")
            except Exception as e:
                print(f"[TARO Memory] Extraction failed: {e}")

        # Conversation summary — generate after a few exchanges to capture context
        try:
            all_messages = get_messages(conversation_id)
            if len(all_messages) >= 3:  # At least user + assistant + user to be worth summarizing
                summary = generate_summary(all_messages)
                if summary:
                    save_summary(user_id, conversation_id, summary)
                    print(f"[TARO Summary] Updated for conversation {conversation_id}")
        except Exception as e:
            print(f"[TARO Summary] Generation failed: {e}")

    background_tasks.add_task(run_background_tasks)

    return StreamingResponse(generate(), media_type="text/plain")


@router.delete("/{conversation_id}")
def delete_conversation_endpoint(
    conversation_id: int,
    current_user: dict = Depends(get_current_user),
):
    deleted = delete_conversation(conversation_id, current_user["id"])

    if not deleted:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return {"message": "Conversation deleted"}
