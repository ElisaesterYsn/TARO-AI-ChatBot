from database.db import get_connection


def save_summary(user_id: int, conversation_id: int, summary: str):
    """
    Upserts the summary for a conversation.
    Updates if a summary already exists for this conversation_id.
    """
    if not summary.strip():
        return

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT INTO conversation_summaries (user_id, conversation_id, summary)
        VALUES (?, ?, ?)
        ON CONFLICT(conversation_id) DO UPDATE SET
            summary     = excluded.summary,
            updated_at  = CURRENT_TIMESTAMP
        """,
        (user_id, conversation_id, summary.strip()),
    )

    connection.commit()
    connection.close()


def get_recent_summaries(user_id: int, limit: int = 5) -> list[dict]:
    """
    Returns the most recently updated summaries for a user,
    excluding the current conversation (newest one is still in progress).
    """
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT cs.id, cs.conversation_id, cs.summary, cs.updated_at,
               c.title
        FROM conversation_summaries cs
        JOIN conversations c ON c.id = cs.conversation_id
        WHERE cs.user_id = ?
        ORDER BY cs.updated_at DESC
        LIMIT ?
        """,
        (user_id, limit),
    )

    rows = [dict(row) for row in cursor.fetchall()]
    connection.close()

    return rows


def get_summaries_as_text(user_id: int, limit: int = 5) -> str:
    """
    Returns recent conversation summaries formatted for system prompt injection.

    Example output:
        Past conversation — "Learning Python":
        The user asked about Python basics...

        Past conversation — "Taro Setup":
        The user was building a personal AI...
    """
    summaries = get_recent_summaries(user_id, limit)

    if not summaries:
        return ""

    lines = []
    for s in summaries:
        title = s.get("title") or "Previous conversation"
        lines.append(f'Past conversation — "{title}":\n{s["summary"]}')

    return "\n\n".join(lines)
