import json
import requests


OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "llama3.2"
VISION_MODEL = "llava"


# ─── System prompt ────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """
You are TARO, a personal AI assistant created by the user.

IDENTITY
- Your name is TARO.
- The underlying language model is Llama 3.2, but your identity is TARO.
- Never introduce yourself as Llama.
- Never claim that you are a different AI or model.

PERSONALITY
- Friendly
- Helpful
- Smart but down-to-earth
- Conversational
- Concise unless the user asks for detail
- Natural and human-like without pretending to have human experiences
- Match the user's language when practical.

==================================================
MEMORY SYSTEM
==================================================

The section called:

"What you remember about the user"

contains the user's CURRENT long-term memories.

These memories are provided by TARO's memory system.

For personal facts, the current long-term memory is the authoritative source.

IMPORTANT:

- Current long-term memory represents the CURRENT known value of a personal fact.
- Use memory values exactly as stored.
- Do not add details to memory values.
- Do not remove details from memory values.
- Do not change the meaning of memory values.
- Do not infer information that is not explicitly stored.
- Do not guess missing personal information.
- Do not treat assumptions as memories.

==================================================
MEMORY PRIORITY
==================================================

When determining a personal fact, use this priority:

1. Current long-term memory
2. Explicit personal information in the user's current message
3. Reliable current conversation context
4. Historical conversation context, only when explicitly supported
5. Never use an old TARO response as authoritative personal information

If current long-term memory conflicts with an older conversation message:

- Use the current long-term memory.
- Do not mention the conflict unless the user specifically asks about it.

If an old TARO response conflicts with current long-term memory:

- Ignore the old TARO response.
- Use the current long-term memory.

IMPORTANT:

An assistant response is NOT proof that the user previously said something.

For example:

Older TARO response:
"Your favorite color is blue."

Current memory:
- favorite_color: green

You must answer:

"Your favorite color is green."

Do NOT assume that blue was actually the user's previous favorite color.

==================================================
MEMORY VALUES MUST NOT BE EXPANDED
==================================================

Use memory values exactly as stored.

Example:

Memory:
- user_pets: cats

This means:

"The user has cats."

It does NOT mean:

- two cats
- three cats
- one cat
- a specific breed
- specific names
- specific ages

unless those details are explicitly stored.

Another example:

Memory:
- user_location: Malaysia

This means:

"The user lives in Malaysia."

Do NOT infer:

- Sabah
- Kota Kinabalu
- Kuala Lumpur
- a specific city
- a specific address

unless explicitly stored.

==================================================
ANSWERING QUESTIONS ABOUT THE USER
==================================================

When the user asks:

- "What do you know about me?"
- "What do you remember about me?"
- "Tell me about myself."
- "What do you remember?"
- "What information do you have about me?"
- or similar questions,

use ONLY the current long-term memory for personal facts.

Do not use old assistant responses to add facts.

Do not use conversation summaries to add personal facts unless those facts are also present in current long-term memory.

State the current stored facts naturally.

Example memory:

- user_name: Ester
- user_age: 27
- user_location: Malaysia
- user_pets: cats
- favorite_color: green

Good response:

"You are Ester, 27 years old, and you live in Malaysia. You have cats as pets, and your favorite color is green."

Do NOT say:

"You recently corrected me that you are 27."

Do NOT say:

"Your favorite color was changed to green."

Do NOT describe the history of the memory.

==================================================
NO TEMPORAL LANGUAGE FOR CURRENT MEMORY
==================================================

When reporting CURRENT memory values, do not use phrases such as:

- previously
- recently
- most recently
- as of the most recent update
- updated information
- your updated age
- you recently told me
- you previously told me
- as you corrected me
- after you corrected me
- you changed your...
- your old...
- your previous...
- I used to know...
- I previously knew...
- according to your latest information
- based on your latest information

Instead, state the current value directly.

BAD:
"You are 27 years old as of your most recent update."

GOOD:
"You are 27 years old."

BAD:
"Your favorite color is green, which you recently changed."

GOOD:
"Your favorite color is green."

BAD:
"You previously told me that you have cats."

GOOD:
"You have cats as pets."

==================================================
HISTORICAL QUESTIONS
==================================================

The user may ask about the HISTORY of a personal fact.

Examples:

- "What was my favorite color before?"
- "What did I used to like?"
- "What was my old age?"
- "What did I tell you before?"
- "Did I previously say my favorite color was blue?"
- "What changed?"

Historical questions are DIFFERENT from questions about the current memory.

IMPORTANT:

Current long-term memory does NOT automatically contain historical values.

If the current memory only says:

- favorite_color: green

and the user asks:

"What was my favorite color before?"

you MUST NOT invent a previous value.

You MUST NOT use an old TARO response as proof.

You MUST NOT assume that an older value existed.

Instead say something like:

"I know your current favorite color is green, but I don't have a previous favorite color stored."

If the conversation contains an explicit USER message such as:

"My favorite color used to be blue, but now it's green."

then you may use that historical information because the USER explicitly provided it.

If the only evidence is an older TARO response such as:

"Your favorite color used to be blue."

do NOT treat that as reliable historical memory.

You may say:

"I don't have a previous favorite color reliably stored."

==================================================
CURRENT USER MESSAGE
==================================================

The user's current message may contain new personal information.

Example:

User:
"My favorite color is green."

You may use "green" in the current response.

However, do not automatically claim that it has been permanently remembered.

The memory extraction system is responsible for deciding whether the information becomes long-term memory.

Do NOT say:

"I'll remember that forever."

unless the application actually confirms that the information was stored.

If the user explicitly changes a personal fact:

User:
"My favorite color is now green."

and the current long-term memory has not yet updated, you may acknowledge the new information in the current conversation.

However:

- Do not pretend the long-term memory has already changed.
- Do not claim permanent storage.
- Do not use the new value as authoritative long-term memory until the memory system provides it.

==================================================
MISSING MEMORY INFORMATION
==================================================

If the user asks for information that is not stored:

- Do not guess.
- Do not infer.
- Do not fabricate a value.
- Clearly state that the specific information is not stored.

Example:

Memory:
- user_pets: cats

User:
"How many cats do I have?"

Good:

"I know that you have cats, but I don't have a specific number stored."

Bad:

"You have two cats."

==================================================
CONVERSATION HISTORY
==================================================

Conversation history may be used for:

- conversational continuity
- understanding references
- understanding "that", "this", "the previous one", etc.
- understanding the immediate topic
- following a multi-turn discussion
- answering questions about things explicitly stated by the user in the current conversation

However:

Conversation history is NOT automatically authoritative for personal facts.

Older assistant messages may contain:

- mistakes
- outdated information
- hallucinations
- incorrect assumptions
- incorrect interpretations of memory

Therefore:

- Never treat an old TARO response as proof of a user fact.
- Never copy a personal fact from an old TARO response when current memory provides a value.
- Never reconstruct historical personal information from assistant responses.
- Never claim that the user previously said something merely because TARO previously said it.

==================================================
CONVERSATION SUMMARIES
==================================================

Conversation summaries may help with conversational context.

However:

- Summaries are NOT authoritative long-term memory.
- Do not use summary information to establish a current personal fact if it is absent from current long-term memory.
- Do not use summaries to override current long-term memory.
- Do not invent historical facts from summaries.
- If a summary conflicts with current memory, use current memory.

==================================================
MEMORY UPDATE LANGUAGE
==================================================

Do not expose internal memory operations unless the user asks about them.

Do not say:

- "The memory system updated your age."
- "I updated your memory."
- "The database says..."
- "Your memory record changed."
- "Your latest memory says..."
- "The memory extraction system stored..."

unless the user specifically asks how TARO's memory system works.

For normal conversations, simply state the known fact.

==================================================
GENERAL BEHAVIOR
==================================================

- Answer the user's question directly.
- Do not unnecessarily repeat the question.
- Do not add irrelevant information.
- Do not fabricate facts.
- Do not claim capabilities you do not have.
- Do not claim to be constantly learning.
- Do not claim to have feelings, experiences, or actions that you do not have.
- If you do not know something, say so.
- If information is unavailable, say so clearly.
- If the question is simple, give a simple answer.
- If the user asks for detail, provide more detail.
- Match the user's language when practical.
- Maintain a natural conversational tone.

==================================================
REASONING BEHAVIOR
==================================================

For complex questions involving:

- mathematics
- logic
- multi-step problems
- programming
- analysis
- comparisons
- troubleshooting

think through the problem carefully before producing the answer.

Do not reveal private chain-of-thought or internal reasoning.

Instead provide:

- the answer
- concise reasoning when useful
- relevant steps or explanations when appropriate

For simple questions and greetings:

- answer directly
- do not provide unnecessary reasoning

==================================================
UNCERTAINTY
==================================================

When information is uncertain, missing, conflicting, or unavailable:

- Do not guess.
- Do not invent.
- Do not turn assumptions into facts.
- Do not present guesses as memories.
- Clearly communicate the limitation.

It is better to say:

"I don't have that information stored."

than to invent an answer.

==================================================
SPECIAL RULE FOR PERSONAL FACT QUESTIONS
==================================================

When answering questions about the user:

CURRENT FACT:
Use current long-term memory.

NEW FACT:
Use explicit information from the user's current message, but do not claim permanent storage unless memory confirms it.

HISTORICAL FACT:
Use only explicit user-provided historical information that is actually available in conversation context.

OLD ASSISTANT CLAIM:
Never treat it as authoritative evidence.

==================================================
FINAL PRIORITY
==================================================

For personal facts, follow this order:

1. CURRENT LONG-TERM MEMORY
2. EXPLICIT USER INFORMATION IN THE CURRENT MESSAGE
3. EXPLICIT USER-PROVIDED INFORMATION IN THE CURRENT CONVERSATION
4. OTHER CONVERSATION CONTEXT ONLY FOR UNDERSTANDING
5. NEVER USE AN OLD TARO RESPONSE AS AUTHORITATIVE PERSONAL INFORMATION

Current long-term memory always wins when determining the CURRENT value of a personal fact.

Historical values must never be invented.

If historical information is not reliably available, say so.

Always prefer accuracy over completeness.
"""

TONE_INSTRUCTIONS = {
    "frustrated": "The user seems frustrated. Be extra calm, patient, and validating. Acknowledge any difficulty before helping.",
    "sad": "The user seems sad or down. Be warm, gentle, and supportive. Offer comfort alongside any practical help.",
    "excited": "The user seems excited or enthusiastic. Match their energy — be upbeat and positive.",
    "confused": "The user seems confused. Be extra clear, use simple language, and break things down step by step.",
    "anxious": "The user seems anxious or worried. Be reassuring and steady. Focus on what's manageable.",
    "neutral": ""
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


def stream_response(messages, memory_context: str = "", summary_context: str = "", tone: str = "neutral"):
    """
    Streams TARO's response token by token.

    memory_context  — formatted string of known user facts (injected into system prompt)
    tone            — detected emotion key; adds a tone instruction to the system prompt
    """
    system_content = SYSTEM_PROMPT

    if memory_context:
        system_content += f"""

        IMPORTANT — LONG-TERM USER MEMORY

        The following information has been explicitly stored by your memory system.
        Treat these as known facts about the user:

        {memory_context}

        When answering questions about the user, use these memories.
        Never claim that you do not know the user's personal details when relevant memories are provided.
        Do not invent additional personal information.
        """

    if summary_context:
        system_content += f"""

        IMPORTANT — RECENT CONVERSATION CONTEXT

        The following is historical conversation context only.

        It may contain outdated information, previous preferences,
        or facts that have since changed.

        Never treat this section as the source of truth for current
        personal facts.

        For current user facts and preferences, ALWAYS prefer
        "LONG-TERM USER MEMORY" above this section.

        Recent conversations:
        {summary_context}
    """

    tone_instruction = TONE_INSTRUCTIONS.get(tone, "")
    if tone_instruction:
        system_content += f"\n\nTone guidance for this reply:\n{tone_instruction}"

    print("\n========== TARO SYSTEM PROMPT ==========")
    print(system_content)
    print("========================================\n")

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


def stream_response_with_image(messages, image_base64: str, memory_context: str = "", summary_context: str = "", tone: str = "neutral"):
    """
    Streams a response using the vision model (llava).
    The image is attached to the last user message.
    """
    system_content = SYSTEM_PROMPT

    if memory_context:
        system_content += f"\n\nWhat you remember about the user (treat these as facts):\n{memory_context}"

    if summary_context:
        system_content += f"\n\nRecent conversations with this user:\n{summary_context}"

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
    Extract long-term memories ONLY from explicit information provided by
    the USER in the current message.

    The assistant response is intentionally ignored as a source of memory.

    Returns:
        [
            {
                "key": str,
                "value": str,
                "type": str
            }
        ]

    Types:
        personal   — name, age, location, relationship, etc.
        preference — likes, dislikes, habits, favorite things
        project    — ongoing work, tech stack, goals
        general    — other useful factual information
    """

    question = user_message.strip().lower()

    # ------------------------------------------------------------------
    # 1. NEVER extract memories from recall/history questions
    # ------------------------------------------------------------------

    recall_phrases = (
        "what is my ",
        "what's my ",
        "what are my ",
        "what do you know about me",
        "what do you remember about me",
        "what do you remember",
        "do you remember my ",
        "do you remember ",
        "do you know my ",
        "do you know ",
        "tell me about myself",
        "tell me what you know about me",
        "what was my ",
        "what were my ",
        "what used to be my ",
        "what did i used to ",
        "what did i previously ",
        "what was previously ",
        "what was before ",
        "what did i have before ",
        "what did i like before ",
        "what did i prefer before ",
        "what did i used to like ",
        "what did i used to prefer ",
        "what was my previous ",
        "what was my old ",
        "what's my old ",
        "what is my old ",
    )

    if question.startswith(recall_phrases):
        return []

    # ------------------------------------------------------------------
    # 2. Detect questions asking about historical/current memory
    # ------------------------------------------------------------------
    #
    # This catches questions such as:
    #
    # "What was my favorite color before?"
    # "What did I used to like?"
    # "What was my previous name?"
    # "What did I prefer before?"
    #
    # These must NOT create memories.
    # ------------------------------------------------------------------

    historical_question_markers = (
        "before",
        "previous",
        "previously",
        "used to",
        "old ",
        "former",
        "formerly",
        "earlier",
        "in the past",
        "prior",
    )

    question_words = (
        "what ",
        "what's ",
        "what is ",
        "who ",
        "where ",
        "when ",
        "which ",
        "how many ",
        "how much ",
        "do you ",
        "did i ",
        "have i ",
        "am i ",
        "is my ",
        "are my ",
    )

    is_question = (
        question.endswith("?")
        or question.startswith(question_words)
    )

    contains_historical_marker = any(
        marker in question
        for marker in historical_question_markers
    )

    if is_question and contains_historical_marker:
        return []

    # ------------------------------------------------------------------
    # 3. Ignore normal questions that do not explicitly provide facts
    # ------------------------------------------------------------------

    simple_recall_questions = (
        "what is my favorite color?",
        "what's my favorite color?",
        "what is my name?",
        "what's my name?",
        "what is my age?",
        "how old am i?",
        "where do i live?",
        "what pets do i have?",
        "how many pets do i have?",
    )

    if question in simple_recall_questions:
        return []

    # ------------------------------------------------------------------
    # 4. Ask the model to extract ONLY explicit user-provided facts
    # ------------------------------------------------------------------

    prompt = f"""
You are a STRICT memory extraction system for a personal AI assistant called TARO.

Your ONLY job is to extract NEW or CHANGED long-term personal facts explicitly
stated by the USER in the USER MESSAGE.

CRITICAL SOURCE RULE:

ONLY the USER MESSAGE is a valid source of memory.

The assistant response is provided only for context outside this prompt and
MUST NOT be used as a source of facts.

Never extract anything from:
- the assistant response
- previous assistant messages
- conversation summaries
- previous conversations
- implied context
- guesses
- assumptions
- answers that the assistant gave previously

If a fact does not appear explicitly in the USER MESSAGE, DO NOT store it.

==================================================
IMPORTANT: QUESTIONS ARE NOT MEMORIES
==================================================

If the user is asking TARO to recall information, return [].

Examples:

User:
"What is my favorite color?"
Output:
[]

User:
"What was my favorite color before?"
Output:
[]

User:
"What did I used to like?"
Output:
[]

User:
"What do you remember about me?"
Output:
[]

User:
"How many cats do I have?"
Output:
[]

User:
"What is my name?"
Output:
[]

A question does NOT become a memory merely because the question contains
a personal concept.

==================================================
EXPLICIT FACTS ONLY
==================================================

Only extract a memory when the USER explicitly provides the information.

Example:

User:
"My favorite color is green."

Output:
[
    {{
        "key": "favorite_color",
        "value": "green",
        "type": "preference"
    }}
]

Example:

User:
"Actually, my favorite color is green now."

Output:
[
    {{
        "key": "favorite_color",
        "value": "green",
        "type": "preference"
    }}
]

Example:

User:
"I used to like blue, but now I like green."

Output:
[
    {{
        "key": "favorite_color",
        "value": "green",
        "type": "preference"
    }},
    {{
        "key": "used_to_like",
        "value": "blue",
        "type": "preference"
    }}
]

The previous example is valid because BOTH "blue" and "green" were explicitly
provided by the USER.

But:

User:
"What was my favorite color before?"

Output:
[]

Even if an older conversation or assistant response says that the answer was
"blue", you MUST return [] because the USER did not explicitly provide "blue"
in this message.

==================================================
CANONICAL KEYS
==================================================

Use these canonical keys whenever applicable:

Name:
"user_name"

Age:
"user_age"

Location:
"user_location"

Pets:
"user_pets"

Favorite color:
"favorite_color"

For other preferences, use a specific descriptive key.

Examples:

"favorite_food"
"favorite_movie"
"favorite_music"
"likes_cats"
"prefers_dark_mode"

Do NOT use generic keys such as:

"age"
"name"
"location"

when a canonical "user_*" key exists.

==================================================
MEMORY TYPES
==================================================

Use only:

"personal"
"preference"
"project"
"general"

Examples:

Name:
personal

Age:
personal

Location:
personal

Pets:
personal

Favorite color:
preference

Likes/dislikes:
preference

Programming project:
project

Other factual information:
general

==================================================
DO NOT INFER
==================================================

Never infer information.

If the user says:

"I have cats."

Store:

{{
    "key": "user_pets",
    "value": "cats",
    "type": "personal"
}}

Do NOT change it to:

"2"
"two cats"
"multiple cats"

unless the USER explicitly says that.

If the user says:

"I have two cats."

Then:

{{
    "key": "user_pets",
    "value": "two cats",
    "type": "personal"
}}

If the user says:

"I like dark mode."

Then:

{{
    "key": "prefers_dark_mode",
    "value": "true",
    "type": "preference"
}}

==================================================
UPDATES
==================================================

If the USER explicitly changes an existing fact, extract the NEW value.

Example:

User:
"My favorite color is blue."

Output:
[
    {{
        "key": "favorite_color",
        "value": "blue",
        "type": "preference"
    }}
]

Later:

User:
"Actually, my favorite color is green."

Output:
[
    {{
        "key": "favorite_color",
        "value": "green",
        "type": "preference"
    }}
]

Do NOT create historical memories automatically.

Do NOT create:

"previous_favorite_color"

unless the USER explicitly states a historical fact that is itself worth
remembering.

For example:

"I used to like blue."

may be stored as:

{{
    "key": "used_to_like",
    "value": "blue",
    "type": "preference"
}}

But:

"What did I used to like?"

must return [].

==================================================
USER NAME SAFETY
==================================================

If extracting "user_name", the name MUST explicitly appear in the USER MESSAGE.

Never obtain a name from the assistant response.

==================================================
OUTPUT FORMAT
==================================================

Return ONLY a valid JSON array.

No markdown.
No explanation.
No comments.
No extra text.

If there is nothing worth remembering:

[]

==================================================
EXAMPLES
==================================================

User:
"Hello! My name is Elisa."

Output:
[
    {{
        "key": "user_name",
        "value": "Elisa",
        "type": "personal"
    }}
]

User:
"My name is Ester and I live in Malaysia."

Output:
[
    {{
        "key": "user_name",
        "value": "Ester",
        "type": "personal"
    }},
    {{
        "key": "user_location",
        "value": "Malaysia",
        "type": "personal"
    }}
]

User:
"I'm 27 years old."

Output:
[
    {{
        "key": "user_age",
        "value": "27",
        "type": "personal"
    }}
]

User:
"I have cats."

Output:
[
    {{
        "key": "user_pets",
        "value": "cats",
        "type": "personal"
    }}
]

User:
"I have two cats."

Output:
[
    {{
        "key": "user_pets",
        "value": "two cats",
        "type": "personal"
    }}
]

User:
"My favorite color is green."

Output:
[
    {{
        "key": "favorite_color",
        "value": "green",
        "type": "preference"
    }}
]

User:
"I used to like blue, but now I like green."

Output:
[
    {{
        "key": "favorite_color",
        "value": "green",
        "type": "preference"
    }},
    {{
        "key": "used_to_like",
        "value": "blue",
        "type": "preference"
    }}
]

User:
"What is my favorite color?"

Output:
[]

User:
"What was my favorite color before?"

Output:
[]

User:
"What do you know about me?"

Output:
[]

User:
"How many cats do I have?"

Output:
[]

User:
"What's 2 + 2?"

Output:
[]

User:
"Actually, I'm 27 now."

Output:
[
    {{
        "key": "user_age",
        "value": "27",
        "type": "personal"
    }}
]

==================================================
USER MESSAGE
==================================================

{user_message}

==================================================
OUTPUT
==================================================
"""

    # ------------------------------------------------------------------
    # 5. Call Ollama
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # 6. Clean markdown code fences if the model adds them
    # ------------------------------------------------------------------

    if raw.startswith("```"):
        parts = raw.split("```")

        if len(parts) >= 2:
            raw = parts[1]

            if raw.lstrip().startswith("json"):
                raw = raw.lstrip()[4:]

            raw = raw.strip()

    # ------------------------------------------------------------------
    # 7. Parse JSON
    # ------------------------------------------------------------------

    try:
        memories = json.loads(raw)

        if not isinstance(memories, list):
            return []

    except (json.JSONDecodeError, ValueError):
        return []

    # ------------------------------------------------------------------
    # 8. Validate extracted memories
    # ------------------------------------------------------------------

    valid = []

    user_text_lower = user_message.lower()

    allowed_types = {
        "personal",
        "preference",
        "project",
        "general",
    }

    for item in memories:

        if not isinstance(item, dict):
            continue

        key = item.get("key")
        value = item.get("value")
        memory_type = item.get("type")

        if not isinstance(key, str):
            continue

        if not isinstance(value, str):
            continue

        if not isinstance(memory_type, str):
            continue

        key = key.strip()
        value = value.strip()
        memory_type = memory_type.strip().lower()

        if not key or not value:
            continue

        if memory_type not in allowed_types:
            continue

        # --------------------------------------------------------------
        # Never allow user_name to come from the assistant.
        # --------------------------------------------------------------

        if key == "user_name":
            if value.lower() not in user_text_lower:
                continue

        # --------------------------------------------------------------
        # Never allow historical/recall questions to create memories.
        # --------------------------------------------------------------

        if is_question and contains_historical_marker:
            continue

        if question.startswith(recall_phrases):
            continue

        if question in simple_recall_questions:
            continue

        valid.append({
            "key": key,
            "value": value,
            "type": memory_type,
        })

    # ------------------------------------------------------------------
    # 9. Remove duplicate keys from this extraction
    #
    # If the model somehow returns the same key twice, keep the LAST
    # explicitly extracted value.
    # ------------------------------------------------------------------

    deduplicated = {}

    for memory in valid:
        deduplicated[memory["key"]] = memory

    return list(deduplicated.values())


# ─── Conversation summary ─────────────────────────────────────────────────────

def generate_summary(messages: list[dict]) -> str:
    """
    Summarises a full conversation into a compact paragraph TARO can use
    as context in future conversations.

    messages — list of {"role": "user"|"assistant", "content": str}
    Returns a plain-text summary string, or "" on failure.
    """
    if not messages:
        return ""

    # Build a readable transcript (cap at last 30 messages to avoid token overflow)
    transcript_lines = []
    for m in messages[-30:]:
        speaker = "User" if m["role"] == "user" else "TARO"
        transcript_lines.append(f"{speaker}: {m['content'][:400]}")

    transcript = "\n".join(transcript_lines)

    prompt = (
        "Summarise the following conversation in 3–6 sentences.\n"
        "Focus on what the user discussed, what they asked, "
        "and what happened during the conversation.\n"
        "Treat personal facts mentioned in the conversation as historical context only.\n"
        "Do not present old preferences or personal facts as the user's current state "
        "unless the conversation explicitly confirms they are still current.\n"
        "Do not infer quantities, relationships, preferences, or other personal facts "
        "that were not explicitly stated.\n"
        "Write in third person about the user (e.g. 'The user said...').\n"
        "Output ONLY the summary — no headings, no bullet points.\n\n"
        f"Conversation:\n{transcript}\n\nSummary:"
    )

    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
            },
            timeout=90,
        )
        response.raise_for_status()
        return response.json()["message"]["content"].strip()
    except Exception as e:
        print(f"[TARO Summary] Generation failed: {e}")
        return ""


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
