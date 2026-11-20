import logging
import streamlit as st

from agent import generate_reply
from database import (
    init_db,
    create_conversation,
    get_conversations,
    get_messages,
    add_turn,
    delete_conversation,
    rename_conversation,
    clear_conversation,
    export_conversation,
)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)
logger.exception("AI agent request failed")
st.set_page_config(
    page_title="Simple AI Agent",
    page_icon="🤖",
    layout="centered",
)

init_db()

st.title("🤖 Simple AI Agent")
st.caption("Your personal AI assistant for everyday questions.")

st.markdown(
    """
    <style>
    .welcome-subtitle {
        color: #9CA3AF;
        font-size: 16px;
        margin-bottom: 24px;
    }

    .suggestion-heading {
        font-size: 18px;
        font-weight: 600;
        margin-top: 24px;
        margin-bottom: 12px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

if "current_conversation_id" not in st.session_state:
    st.session_state.current_conversation_id = None

# Sidebar
with st.sidebar:
    st.header("Conversations")

    if st.button("➕ New chat", use_container_width=True):
        new_id = create_conversation()
        st.session_state.current_conversation_id = new_id
        st.rerun()

    conversations = get_conversations()
    conversation_ids = [item["id"] for item in conversations]

    current_id = st.session_state.current_conversation_id

    if current_id not in conversation_ids:
        if conversation_ids:
            current_id = conversation_ids[0]
        else:
            current_id = create_conversation()

        st.session_state.current_conversation_id = current_id

    if conversations:
        title_map = {
            item["id"]: item["title"]
            for item in conversations
        }

        selected_id = st.selectbox(
            "Open a conversation",
            options=conversation_ids,
            index=conversation_ids.index(current_id),
            format_func=lambda cid: title_map[cid],
        )

        if selected_id != st.session_state.current_conversation_id:
            st.session_state.current_conversation_id = selected_id
            st.rerun()

        st.divider()

        if st.button(
            "🗑️ Delete current chat",
            use_container_width=True,
        ):
            delete_conversation(current_id)
            st.session_state.current_conversation_id = None
            st.rerun()

    st.caption("Conversations are stored locally in SQLite.")

# Load selected conversation
conversation_id = st.session_state.current_conversation_id
messages = get_messages(conversation_id)

# Welcome screen for an empty conversation
if not messages:
    st.markdown(
        '<div class="suggestion-heading">'
        'What would you like to explore today?'
        '</div>',
        unsafe_allow_html=True,
    )

    suggestions = [
        "Explain Python in simple terms",
        "Help me write a Python program",
        "Explain object-oriented programming",
        "Give me a logical reasoning question",
    ]

    col1, col2 = st.columns(2)

    for index, suggestion in enumerate(suggestions):
        column = col1 if index % 2 == 0 else col2

        with column:
            if st.button(
                suggestion,
                key=f"suggestion_{conversation_id}_{index}",
                use_container_width=True,
            ):
                st.session_state.pending_prompt = suggestion
                st.rerun()

# Display previous messages
for message in messages:
    with st.chat_message(
        "user" if message["role"] == "user" else "assistant"
    ):
        st.markdown(message["content"])

# User input
pending_prompt = st.session_state.pop(
    "pending_prompt",
    None,
)

typed_prompt = st.chat_input(
    "Ask me anything..."
)

prompt = typed_prompt or pending_prompt

if prompt:
    if not prompt.strip():
        st.warning("Please enter a question.")
        st.stop()

    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                answer = generate_reply(
                    history=messages,
                    user_message=prompt,
                )

                st.markdown(answer)

                add_turn(
                    conversation_id,
                    prompt,
                    answer,
                )

            except ValueError as exc:
                st.warning(str(exc))

            except Exception as exc:
                print(
                    f"AI agent error: "
                    f"{type(exc).__name__}: {exc}"
                )

                st.error(
                    "I couldn't generate a response. "
                    "Please try again shortly. "
                    "If the problem continues, "
                    "check the application logs."
                )
st.divider()

with st.expander("Manage conversation"):

    new_title = st.text_input(
        "Conversation title",
        key=f"title_{current_id}",
        max_chars=100,
    )

    if st.button(
        "Rename conversation",
        key=f"rename_{current_id}",
    ):
        if new_title.strip():
            rename_conversation(
                current_id,
                new_title,
            )

            st.success("Conversation renamed.")
            st.rerun()
        else:
            st.warning("Enter a conversation title.")

    if st.button(
        "Clear messages",
        key=f"clear_{current_id}",
    ):
        clear_conversation(current_id)
        st.rerun()

    conversation_json = export_conversation(current_id)

    st.download_button(
        label="Export conversation",
        data=conversation_json,
        file_name=f"conversation_{current_id}.json",
        mime="application/json",
        key=f"export_{current_id}",
    )