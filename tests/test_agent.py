
import pytest

from agent import generate_reply

class FakeModels:
    def generate_content(self, **kwargs):
        self.last_request = kwargs

        class Response:
            text = "Python is a programming language."

        return Response()

class FakeClient:
    def __init__(self):
        self.models = FakeModels()

import pytest

from agent import generate_reply, prepare_history


def test_empty_question_is_rejected():
    with pytest.raises(ValueError):
        generate_reply(
            history=[],
            user_message="   ",
            client=object(),
        )


def test_non_text_question_is_rejected():
    with pytest.raises(ValueError):
        generate_reply(
            history=[],
            user_message=123,
            client=object(),
        )


def test_history_ignores_invalid_roles():
    history = [
        {"role": "system", "content": "Invalid role"},
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi!"},
    ]

    result = prepare_history(history)

    assert len(result) == 2
    assert result[0].role == "user"
    assert result[1].role == "model"


def test_history_does_not_start_with_assistant():
    history = [
        {"role": "assistant", "content": "Previous answer"},
        {"role": "user", "content": "New question"},
    ]

    result = prepare_history(history)

    assert len(result) == 1
    assert result[0].role == "user"
def test_generate_reply():
    client = FakeClient()

    answer = generate_reply(
        history=[],
        user_message="What is Python?",
        client=client,
    )

    assert "Python" in answer
    assert client.models.last_request["model"]

def test_history_is_passed_to_model():
    client = FakeClient()

    history = [
        {"role": "user", "content": "My name is Hetvi."},
        {"role": "assistant", "content": "Nice to meet you!"},
    ]

    generate_reply(
        history=history,
        user_message="What is my name?",
        client=client,
    )

    contents = client.models.last_request["contents"]

    assert len(contents) == 3
    assert contents[0].role == "user"
    assert contents[1].role == "model"
    assert contents[2].role == "user"

def test_empty_question_is_rejected():
    with pytest.raises(ValueError):
        generate_reply(
            history=[],
            user_message="   ",
            client=FakeClient(),
        )