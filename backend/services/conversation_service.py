from database.db import get_connection


def create_conversation(title: str = "New Chat") -> int:
    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT INTO conversations (title)
        VALUES (?)
        """,
        (title,)
    )

    conversation_id = cursor.lastrowid

    connection.commit()
    connection.close()

    return conversation_id


def get_conversations():
    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT id, title, created_at, updated_at
        FROM conversations
        ORDER BY updated_at DESC
        """
    )

    conversations = [dict(row) for row in cursor.fetchall()]

    connection.close()

    return conversations


def get_conversation(conversation_id: int):
    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT id, title, created_at, updated_at
        FROM conversations
        WHERE id = ?
        """,
        (conversation_id,)
    )

    conversation = cursor.fetchone()

    connection.close()

    if conversation is None:
        return None

    return dict(conversation)


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
        (conversation_id,)
    )

    messages = [dict(row) for row in cursor.fetchall()]

    connection.close()

    return messages


def add_message(
    conversation_id: int,
    role: str,
    content: str
):
    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT INTO messages (
            conversation_id,
            role,
            content
        )
        VALUES (?, ?, ?)
        """,
        (
            conversation_id,
            role,
            content
        )
    )

    cursor.execute(
        """
        UPDATE conversations
        SET updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (conversation_id,)
    )

    connection.commit()
    connection.close()

def update_conversation_title(
    conversation_id: int,
    title: str
):
    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute(
        """
        UPDATE conversations
        SET title = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (
            title,
            conversation_id
        )
    )

    connection.commit()
    connection.close()