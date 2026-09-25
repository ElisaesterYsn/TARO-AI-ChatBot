import json
import requests


OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "llama3.2"
VISION_MODEL = "llava"


# ─── System prompt ────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """
You are TARO, a personal AI assistant created by the user.

Your name is TARO.
The underlying language model is Llama 3.2, but your identity is TARO.
Never introduce yourself as Llama.

Personality:
- Friendly
- Helpful
- Smart but down-to-earth
- Conversational
- Concise unless the user asks for detail

Behavior:
- Answer the user's question directly.
- Do not unnecessarily repeat the question.
- Use the conversation history to understand context.
- Do not claim to remember something unless it appears in the conversation.
- Do not claim to be constantly learning.
- Do not invent capabilities you do not have.
- For simple questions, give a simple answer.

Reasoning behavior:
- For complex questions (math, logic, multi-step problems, analysis, comparisons),
  think through the problem step by step before giving your final answer.
- For simple questions or greetings, answer directly without steps.
- Never show your internal reasoning process in your reply unless the user asks
  you to explain your thinking. Just use it internally to arrive at a better answer.
"""

# Tone instructions injected based on detected emotion
TONE_INSTRUCTIONS = {
    "frustrated": "The user seems frustrated. Be extra calm, patient, and validating. Acknowledge any difficulty before helping.",
    "sad": "The user seems sad or down. Be warm, gentle, and supportive. Offer comfort alongside any practical help.",
    "excited": "The user seems excited or enthusiastic. Match their energy — be upbeat and positive.",
    "confused": "The user seems confused. Be extra clear, use simple language, and break things down step by step.",
    "anxious": "The user seems anxious or worried. Be reassuring and steady. Focus on what's manageable.",
    "neutral": "",  # No tone injection needed
}


# ─── Core generation ──────────────────────────────────────────────────────────

def generate_response(messages: list[dict]) -> str:
    ollama_messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        *messages,
    ]

    response = requests.post(
        OLLAMA_URL,
        json={"model": MODEL, "messages": ollama_messages, "stream": False},
        timeout=120,
    )

    response.raise_for_status()

    return response.json()["message"]["content"]


def stream_response(messages, memory_context: str = "", tone: str = "neutral"):
    """
    Streams TARO's response token by token.

    memory_context  — formatted string of known user facts (injected into system prompt)
    tone            — detected emotion key; adds a tone instruction to the system prompt
    """
    system_content = SYSTEM_PROMPT

    if memory_context:
        system_content += f"\n\nWhat you remember about the user:\n{memory_context}"

    tone_instruction = TONE_INSTRUCTIONS.get(tone, "")
    if tone_instruction:
        system_content += f"\n\nTone guidance for this reply:\n{tone_instruction}"

    response = requests.post(
        OLLAMA_URL,
        json={
            "model": MODEL,
            "messages": [
                {"role": "system", "content": system_content},
                *messages,
            ],
            "stream": True,
        },
        stream=True,
        timeout=120,
    )

    response.raise_for_status()

    for line in response.iter_lines():
        if not line:
            continue

        chunk = json.loads(line.decode("utf-8"))

        if chunk.get("done"):
            break

        content = chunk.get("message", {}).get("content", "")

        if content:
            yield content


def stream_response_with_image(messages, image_base64: str, memory_context: str = "", tone: str = "neutral"):
    """
    Streams a response using the vision model (llava).
    The image is attached to the last user message.
    """
    system_content = SYSTEM_PROMPT

    if memory_context:
        system_content += f"\n\nWhat you remember about the user:\n{memory_context}"

    tone_instruction = TONE_INSTRUCTIONS.get(tone, "")
    if tone_instruction:
        system_content += f"\n\nTone guidance for this reply:\n{tone_instruction}"

    # Attach the image to the last user message
    ollama_messages = [{"role": "system", "content": system_content}]

    for i, msg in enumerate(messages):
        if i == len(messages) - 1 and msg["role"] == "user":
            ollama_messages.append({
                "role": "user",
                "content": msg["content"],
                "images": [image_base64],
            })
        else:
            ollama_messages.append(msg)

    response = requests.post(
        OLLAMA_URL,
        json={
            "model": VISION_MODEL,
            "messages": ollama_messages,
            "stream": True,
        },
        stream=True,
        timeout=180,
    )

    response.raise_for_status()

    for line in response.iter_lines():
        if not line:
            continue

        chunk = json.loads(line.decode("utf-8"))

        if chunk.get("done"):
            break

        content = chunk.get("message", {}).get("content", "")

        if content:
            yield content


# ─── Emotion detection ────────────────────────────────────────────────────────

# Keyword-based emotion detection — no model call, instant, safe to run
# synchronously before streaming begins.
_EMOTION_KEYWORDS: dict[str, list[str]] = {
    "frustrated": [
        "frustrated", "annoying", "annoyed", "ugh", "why won't", "why doesn't",
        "doesn't work", "not working", "keeps failing", "so stupid", "hate this",
        "this is broken", "still not", "again", "always fails",
    ],
    "sad": [
        "sad", "unhappy", "depressed", "lonely", "miss", "grief", "lost",
        "heartbroken", "crying", "upset", "hurt", "pain", "suffering",
        "don't feel good", "feeling down", "can't cope",
    ],
    "excited": [
        "excited", "amazing", "awesome", "can't wait", "love this", "fantastic",
        "incredible", "so cool", "thrilled", "pumped", "stoked", "great news",
        "finally", "yay", "woah", "omg", "this is great",
    ],
    "confused": [
        "confused", "don't understand", "what does", "what is", "how do",
        "i don't get", "not sure", "unclear", "lost", "makes no sense",
        "what does this mean", "can you explain", "help me understand",
    ],
    "anxious": [
        "anxious", "worried", "nervous", "scared", "afraid", "panic",
        "stress", "stressed", "overwhelmed", "can't stop thinking",
        "what if", "going wrong", "will it work", "i'm scared",
    ],
}


def detect_emotion(user_message: str) -> str:
    """
    Classifies the emotional tone of the user's message using keyword matching.
    Fast, synchronous, no model call — safe to run before streaming.

    Returns one of: frustrated, sad, excited, confused, anxious, neutral
    """
    lower = user_message.lower()

    scores: dict[str, int] = {emotion: 0 for emotion in _EMOTION_KEYWORDS}

    for emotion, keywords in _EMOTION_KEYWORDS.items():
        for kw in keywords:
            if kw in lower:
                scores[emotion] += 1

    best = max(scores, key=lambda e: scores[e])

    return best if scores[best] > 0 else "neutral"


# ─── Safety filtering ─────────────────────────────────────────────────────────

# Hard-coded patterns that don't need a model call — fast first pass
_UNSAFE_PATTERNS = [
    "i cannot", "i can't assist", "i can't help with that",
    "i'm not able to", "as an ai, i", "i must refuse",
    "this is harmful", "i won't help",
]

_SAFE_FALLBACK = (
    "I want to be genuinely helpful here, but I'm not sure how to answer that "
    "safely. Could you rephrase or give me more context?"
)


def is_output_safe(text: str) -> bool:
    """
    Two-stage safety check on TARO's completed response.

    Stage 1 — fast keyword scan for obvious refusal/harm markers.
    Stage 2 — ask the model to flag genuinely harmful content.

    Returns True if the output is safe to show, False if it should be replaced.
    """
    lower = text.lower()

    # Stage 1: known refusal phrases that indicate the model broke character
    # or produced an unhelpful canned response
    for pattern in _UNSAFE_PATTERNS:
        if pattern in lower:
            return False

    # Stage 2: ask the model to evaluate its own output
    # Only run this for longer responses (short ones are almost always fine)
    if len(text) < 120:
        return True

    prompt = (
        f'Does the following AI response contain harmful, dangerous, or deeply '
        f'inappropriate content that should not be shown to a user?\n'
        f'Answer with exactly one word: yes or no.\n\n'
        f'Response: """{text[:800]}"""'
    )

    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
            },
            timeout=30,
        )

        response.raise_for_status()

        verdict = response.json()["message"]["content"].strip().lower()

        return not verdict.startswith("yes")

    except Exception as error:
        print(f"[TARO Safety] Check failed, assuming safe: {error}")
        return True  # Fail open — don't block on network issues


def safe_response(text: str) -> str:
    """Returns the text if safe, or a fallback message if not."""
    return text if is_output_safe(text) else _SAFE_FALLBACK


# ─── Memory extraction ────────────────────────────────────────────────────────

def extract_memories(user_message: str, assistant_response: str) -> list[dict]:
    """
    Asks the model to look at a single user/assistant exchange and return
    a list of facts worth remembering.

    Returns a list of dicts: [{"key": str, "value": str, "type": str}, ...]
    Returns an empty list if nothing is worth storing or parsing fails.

    Types used:
      personal   — name, age, location, relationship, etc.
      preference — likes, dislikes, habits, favourite things
      project    — ongoing work, tech stack, goals
      general    — anything else factual
    """
    prompt = f"""You are a memory extraction system for a personal AI assistant called TARO.

Given the exchange below, extract any facts about the user that TARO should remember long-term.

Rules:
- Only extract clear, explicit facts stated by the user — never infer or guess.
- Ignore greetings, small talk, and one-off questions with no personal relevance.
- Each memory must have a short key (snake_case, e.g. "user_name"), a concise value, and a type.
- Valid types: personal, preference, project, general
- If there is nothing worth remembering, return an empty array.
- Return ONLY a valid JSON array — no explanation, no markdown, no extra text.

Examples:
User: "My name is Elisa"
Output: [{{"key": "user_name", "value": "Elisa", "type": "personal"}}]

User: "I prefer dark mode"
Output: [{{"key": "prefers_dark_mode", "value": "true", "type": "preference"}}]

User: "I'm building a project called TARO using Vue and FastAPI"
Output: [{{"key": "current_project", "value": "TARO — Vue + FastAPI personal AI", "type": "project"}}]

User: "What's 2 + 2?"
Output: []

Exchange:
User: {user_message}
TARO: {assistant_response}

Output:"""

    response = requests.post(
        OLLAMA_URL,
        json={
            "model": MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
        },
        timeout=60,
    )

    response.raise_for_status()

    raw = response.json()["message"]["content"].strip()

    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    try:
        memories = json.loads(raw)

        if not isinstance(memories, list):
            return []

        valid = []

        for item in memories:
            if (
                isinstance(item, dict)
                and isinstance(item.get("key"), str)
                and isinstance(item.get("value"), str)
                and isinstance(item.get("type"), str)
                and item["key"].strip()
                and item["value"].strip()
            ):
                valid.append({
                    "key": item["key"].strip(),
                    "value": item["value"].strip(),
                    "type": item["type"].strip(),
                })

        return valid

    except (json.JSONDecodeError, ValueError):
        return []


# ─── Title generation ─────────────────────────────────────────────────────────

def generate_title(message: str) -> str:
    response = requests.post(
        OLLAMA_URL,
        json={
            "model": MODEL,
            "messages": [
                {
                    "role": "user",
                    "content": (
                        f'Write a short title for a conversation that starts with this message: "{message}"\n\n'
                        f'Rules:\n'
                        f'- Output ONLY the title, nothing else.\n'
                        f'- 2 to 6 words.\n'
                        f'- No quotation marks.\n'
                        f'- No punctuation at the end.\n'
                        f'- Base the title strictly on what the message says.'
                    ),
                },
            ],
            "stream": False,
        },
        timeout=60,
    )

    response.raise_for_status()

    title = response.json()["message"]["content"].strip()
    title = title.strip('"').strip("'").strip()

    return title[:120]
