from database.db import get_connection


def get_all_memories() -> list[dict]:
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT id, key, value, type, created_at, updated_at
        FROM memories
        ORDER BY updated_at DESC
        """
    )

    memories = [dict(row) for row in cursor.fetchall()]

    connection.close()

    return memories


def get_memories_as_text() -> str:
    """Returns all memories formatted as a plain text block for injection into the system prompt."""
    memories = get_all_memories()

    if not memories:
        return ""

    lines = [f"- {m['key']}: {m['value']}" for m in memories]

    return "\n".join(lines)


def save_memory(key: str, value: str, type: str = "general"):
    """
    Inserts a new memory or updates the value if the key already exists.
    Key is treated as case-insensitive by normalising to lowercase.
    """
    connection = get_connection()
    cursor = connection.cursor()

    normalized_key = key.strip().lower()

    cursor.execute(
        """
        INSERT INTO memories (key, value, type)
        VALUES (?, ?, ?)
        ON CONFLICT(key) DO UPDATE SET
            value = excluded.value,
            type = excluded.type,
            updated_at = CURRENT_TIMESTAMP
        """,
        (normalized_key, value.strip(), type.strip())
    )

    connection.commit()
    connection.close()


def delete_memory(memory_id: int) -> bool:
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        DELETE FROM memories
        WHERE id = ?
        """,
        (memory_id,)
    )

    deleted = cursor.rowcount > 0

    connection.commit()
    connection.close()

    return deleted


def clear_all_memories():
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("DELETE FROM memories")

    connection.commit()
    connection.close()
