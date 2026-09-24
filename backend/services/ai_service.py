import json
import requests


OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "llama3.2"


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
"""


def generate_response(messages: list[dict]) -> str:
    ollama_messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT
        },
        *messages
    ]

    response = requests.post(
        OLLAMA_URL,
        json={
            "model": MODEL,
            "messages": ollama_messages,
            "stream": False
        },
        timeout=120
    )

    response.raise_for_status()

    data = response.json()

    return data["message"]["content"]

def stream_response(messages, memory_context: str = ""):
    system_content = SYSTEM_PROMPT

    if memory_context:
        system_content += f"\n\nWhat you remember about the user:\n{memory_context}"

    response = requests.post(
        OLLAMA_URL,
        json={
            "model": MODEL,
            "messages": [
                {
                    "role": "system",
                    "content": system_content,
                },
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

        data = line.decode("utf-8")

        chunk = json.loads(data)

        if chunk.get("done"):
            break

        content = chunk.get("message", {}).get("content", "")

        if content:
            yield content

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
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            "stream": False,
        },
        timeout=60,
    )

    response.raise_for_status()

    raw = response.json()["message"]["content"].strip()

    # Strip markdown code fences if the model wrapped the JSON
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


def generate_title(message: str) -> str:
    response = requests.post(
        OLLAMA_URL,
        json={
            "model": MODEL,
            "messages": [
                {
                    "role": "user",
                    "content": f'Write a short title for a conversation that starts with this message: "{message}"\n\nRules:\n- Output ONLY the title, nothing else.\n- 2 to 6 words.\n- No quotation marks.\n- No punctuation at the end.\n- Base the title strictly on what the message says.',
                },
            ],
            "stream": False,
        },
        timeout=60,
    )

    response.raise_for_status()

    data = response.json()

    title = data["message"]["content"].strip()

    title = title.strip('"').strip("'").strip()

    return title[:120]