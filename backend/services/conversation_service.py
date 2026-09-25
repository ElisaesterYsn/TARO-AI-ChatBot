from database.db import get_connection


def create_conversation(user_id: int, title: str = "New Chat") -> int:
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        "INSERT INTO conversations (user_id, title) VALUES (?, ?)",
        (user_id, title),
    )

    conversation_id = cursor.lastrowid
    connection.commit()
    connection.close()

    return conversation_id


def get_conversations(user_id: int):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT id, title, created_at, updated_at
        FROM conversations
        WHERE user_id = ?
        ORDER BY updated_at DESC
        """,
        (user_id,),
    )

    conversations = [dict(row) for row in cursor.fetchall()]
    connection.close()

    return conversations


def get_conversation(conversation_id: int, user_id: int):
    """Returns the conversation only if it belongs to the given user."""
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT id, title, created_at, updated_at
        FROM conversations
        WHERE id = ? AND user_id = ?
        """,
        (conversation_id, user_id),
    )

    row = cursor.fetchone()
    connection.close()

    return dict(row) if row else None


def get_messages(conversation_id: int):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT id, role, content, created_at
        FROM messages
        WHERE conversation_id = ?
        ORDER BY id ASC
        """,
        (conversation_id,),
    )

    messages = [dict(row) for row in cursor.fetchall()]
    connection.close()

    return messages


def add_message(conversation_id: int, role: str, content: str):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        "INSERT INTO messages (conversation_id, role, content) VALUES (?, ?, ?)",
        (conversation_id, role, content),
    )

    cursor.execute(
        "UPDATE conversations SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (conversation_id,),
    )

    connection.commit()
    connection.close()


def update_conversation_title(conversation_id: int, title: str):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        UPDATE conversations
        SET title = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (title, conversation_id),
    )

    connection.commit()
    connection.close()


def update_last_assistant_message(conversation_id: int, content: str):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        UPDATE messages SET content = ?
        WHERE id = (
            SELECT id FROM messages
            WHERE conversation_id = ? AND role = 'assistant'
            ORDER BY id DESC LIMIT 1
        )
        """,
        (content, conversation_id),
    )

    connection.commit()
    connection.close()


def delete_conversation(conversation_id: int, user_id: int) -> bool:
    """Deletes a conversation only if it belongs to the given user."""
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        "DELETE FROM conversations WHERE id = ? AND user_id = ?",
        (conversation_id, user_id),
    )

    deleted = cursor.rowcount > 0
    connection.commit()
    connection.close()

    return deleted
