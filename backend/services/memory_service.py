from database.db import get_connection


def get_all_memories(user_id: int) -> list[dict]:
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT id, key, value, type, created_at, updated_at
        FROM memories
        WHERE user_id = ?
        ORDER BY updated_at DESC
        """,
        (user_id,),
    )

    memories = [dict(row) for row in cursor.fetchall()]
    connection.close()

    return memories


def get_memories_as_text(user_id: int) -> str:
    """Returns all memories for a user formatted for system prompt injection."""
    memories = get_all_memories(user_id)

    if not memories:
        return ""

    return "\n".join(f"- {m['key']}: {m['value']}" for m in memories)


def save_memory(user_id: int, key: str, value: str, type: str = "general"):
    """Upserts a memory for the given user by key."""
    connection = get_connection()
    cursor = connection.cursor()

    normalized_key = key.strip().lower()

    # Try update first, then insert
    cursor.execute(
        """
        UPDATE memories
        SET value = ?, type = ?, updated_at = CURRENT_TIMESTAMP
        WHERE user_id = ? AND key = ?
        """,
        (value.strip(), type.strip(), user_id, normalized_key),
    )

    if cursor.rowcount == 0:
        cursor.execute(
            "INSERT INTO memories (user_id, key, value, type) VALUES (?, ?, ?, ?)",
            (user_id, normalized_key, value.strip(), type.strip()),
        )

    connection.commit()
    connection.close()


def delete_memory(memory_id: int, user_id: int) -> bool:
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        "DELETE FROM memories WHERE id = ? AND user_id = ?",
        (memory_id, user_id),
    )

    deleted = cursor.rowcount > 0
    connection.commit()
    connection.close()

    return deleted


def clear_all_memories(user_id: int):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("DELETE FROM memories WHERE user_id = ?", (user_id,))

    connection.commit()
    connection.close()
