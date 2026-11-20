
import database

def test_conversation_persistence(tmp_path, monkeypatch):
    db_file = tmp_path / "test_chat.db"
    monkeypatch.setattr(database, "DB_PATH", str(db_file))

    database.init_db()

    conversation_id = database.create_conversation()

    database.add_turn(
        conversation_id,
        "What is Python?",
        "Python is a programming language.",
    )

    messages = database.get_messages(conversation_id)

    assert len(messages) == 2
    assert messages[0]["role"] == "user"
    assert messages[0]["content"] == "What is Python?"
    assert messages[1]["role"] == "assistant"
    assert "programming language" in messages[1]["content"]

    # Confirm that data survives a fresh database connection.
    database.init_db()
    saved_messages = database.get_messages(conversation_id)

    assert len(saved_messages) == 2

def test_delete_conversation(tmp_path, monkeypatch):
    monkeypatch.setattr(
        database,
        "DB_PATH",
        str(tmp_path / "delete_test.db"),
    )

    database.init_db()
    conversation_id = database.create_conversation()

    database.add_turn(
        conversation_id,
        "Hello",
        "Hello! How can I help?",
    )

    database.delete_conversation(conversation_id)

    assert database.get_messages(conversation_id) == []
    assert all(
        item["id"] != conversation_id
        for item in database.get_conversations()
    )