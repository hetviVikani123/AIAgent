import sqlite3
import json

from pathlib import Path
from contextlib import contextmanager

from config import DATABASE_PATH as DB_PATH



@contextmanager
def get_connection(db_path=None):
    path = db_path or DB_PATH

    if str(path) != ":memory:":
        Path(path).parent.mkdir(
            parents=True,
            exist_ok=True,
        )

    connection = sqlite3.connect(
        str(path),
        timeout=10,
    )

    connection.row_factory = sqlite3.Row

    try:
        connection.execute("PRAGMA foreign_keys = ON")

        yield connection

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()

def init_db():
    with get_connection() as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL DEFAULT 'New conversation',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        connection.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id INTEGER NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (conversation_id)
                    REFERENCES conversations(id) ON DELETE CASCADE
            )
        """)

        connection.execute("PRAGMA foreign_keys = ON")

def create_conversation():
    with get_connection() as connection:
        cursor = connection.execute(
            "INSERT INTO conversations (title) VALUES (?)",
            ("New conversation",)
        )
        return cursor.lastrowid

def get_conversations():
    with get_connection() as connection:
        rows = connection.execute("""
            SELECT id, title, created_at, updated_at
            FROM conversations
            ORDER BY updated_at DESC, id DESC
        """).fetchall()

    return [dict(row) for row in rows]

def get_messages(conversation_id):
    with get_connection() as connection:
        rows = connection.execute("""
            SELECT role, content, created_at
            FROM messages
            WHERE conversation_id = ?
            ORDER BY id ASC
        """, (conversation_id,)).fetchall()

    return [dict(row) for row in rows]

def add_turn(conversation_id, user_message, assistant_message):
    with get_connection() as connection:
        connection.execute("""
            INSERT INTO messages (conversation_id, role, content)
            VALUES (?, 'user', ?)
        """, (conversation_id, user_message))

        connection.execute("""
            INSERT INTO messages (conversation_id, role, content)
            VALUES (?, 'assistant', ?)
        """, (conversation_id, assistant_message))

        connection.execute("""
            UPDATE conversations
            SET title = CASE
                WHEN title = 'New conversation' THEN ?
                ELSE title
            END,
            updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """, (
                " ".join(user_message.split())[:45],
                conversation_id,
            )
        )

def delete_conversation(conversation_id):
    with get_connection() as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute(
            "DELETE FROM messages WHERE conversation_id = ?",
            (conversation_id,)
        )
        connection.execute(
            "DELETE FROM conversations WHERE id = ?",
            (conversation_id,)
        )
import json


def conversation_exists(conversation_id):
    """Check whether a conversation exists."""

    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT id
            FROM conversations
            WHERE id = ?
            """,
            (conversation_id,),
        ).fetchone()

    return row is not None


def rename_conversation(conversation_id, new_title):
    """Rename an existing conversation."""

    new_title = new_title.strip()

    if not new_title:
        raise ValueError(
            "Conversation title cannot be empty."
        )

    if len(new_title) > 100:
        raise ValueError(
            "Conversation title cannot exceed 100 characters."
        )

    with get_connection() as connection:
        cursor = connection.execute(
            """
            UPDATE conversations
            SET title = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (new_title, conversation_id),
        )

        return cursor.rowcount > 0


def clear_conversation(conversation_id):
    """Delete messages but preserve the conversation."""

    with get_connection() as connection:
        connection.execute(
            """
            DELETE FROM messages
            WHERE conversation_id = ?
            """,
            (conversation_id,),
        )

        connection.execute(
            """
            UPDATE conversations
            SET title = 'New conversation',
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (conversation_id,),
        )


def export_conversation(conversation_id):
    """Export a conversation as a JSON string."""

    if not conversation_exists(conversation_id):
        raise ValueError(
            "Conversation does not exist."
        )

    with get_connection() as connection:
        conversation = connection.execute(
            """
            SELECT id, title, created_at, updated_at
            FROM conversations
            WHERE id = ?
            """,
            (conversation_id,),
        ).fetchone()

    messages = get_messages(conversation_id)

    result = {
        "conversation": dict(conversation),
        "messages": messages,
    }

    return json.dumps(
        result,
        indent=2,
        ensure_ascii=False,
    )