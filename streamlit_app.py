import re
import streamlit as st
from openai import OpenAI
import os
from qdrant_client import QdrantClient
from qdrant_client.http import models as qdrant_models
import uuid
import datetime

client = OpenAI()

# Initialize Qdrant client
QDRANT_URL = "https://67bd4e7c-9e18-4183-8655-cb368b598d90.europe-west3-0.gcp.cloud.qdrant.io"
QDRANT_API_KEY = st.secrets["QDRANT_API_KEY"]

qdrant_client = QdrantClient(
    url=QDRANT_URL,
    api_key=QDRANT_API_KEY,
    prefer_grpc=False
)

COLLECTION_NAME = "journal_entries"


def init_qdrant_collection():
    vector_size = 1536  # matches "text-embedding-3-small"
    try:
        collections_info = qdrant_client.get_collections()
        collection_names = [col.name for col in collections_info.collections]
    except Exception as e:
        st.error(f"Error fetching collections: {e}")
        collection_names = []

    if COLLECTION_NAME in collection_names:
        st.write(" Qdrant is locked and loaded 😎")
    else:
        qdrant_client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=qdrant_models.VectorParams(size=vector_size, distance="Cosine")
        )
        st.write("Created a new collection in Qdrant.")


def embed_text(text: str) -> list[float]:
    response = client.embeddings.create(
        input=text,
        model="text-embedding-3-small"
    )
    return response.data[0].embedding


def retrieve_relevant_entries(user_id, query_text, top_k=3):
    query_embedding = embed_text(query_text)
    response = qdrant_client.query_points(
        collection_name=COLLECTION_NAME,
        query=query_embedding,
        limit=top_k,
        with_payload=True,
        with_vectors=False
    )
    top_entries = []
    for point in response.points:
        payload = point.payload
        title = payload.get("title") or payload.get("text", "N/A")
        creator = payload.get("creator", "N/A")
        date = payload.get("post_date") or payload.get("timestamp", "N/A")
        content = payload.get("content", "N/A")
        entry_str = (
            f"📖 **{title}**\n"
            f"🗓️ {date}\n\n"
            f"{content}"
        )
        top_entries.append(entry_str)
    return top_entries


def stream_gpt_response(question, relevant_texts, chat_container):
    """
    Streams GPT response and dynamically updates a conversation-style display.
    - Journal entries appear in one message (system role).
    - Reflection is triggered by "Reflektion:" marker and displayed with a robot avatar (assistant role).
    """

    # 1) Adjust system prompt so the model uses "Reflection:" as the marker
    #    (instead of "👱‍♀️ **Joy**:").
    if relevant_texts:
        context_str = "\n\n".join(relevant_texts)
    else:
        context_str = "I didn't find anything about that in your Journal."

    system_prompt = """
You are a compassionate and insightful journaling companion. 
Your primary role is to retrieve relevant journal entries verbatim and then provide a reflection. 
Always answer in Swedish.
Use the following format exactly:

- **Inlägg:** 
  [Show the entries]

- **Reflektion:** 
  [Your insight here]

If no relevant journal entry exists, respond with: "Jag hittar inget om det i din dagbok 😐."
"""

    user_prompt = f"""
**Relevant Journal Entries:**  

{context_str}  

**User Query:**  
{question}
"""

    response_stream = client.chat.completions.create(
        model="gpt-4o-mini",  # or "gpt-4" if available
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        stream=True
    )

    full_response = ""
    message_buffer = ""

    # Placeholders for updating messages
    journal_placeholder = chat_container.empty()
    reflection_placeholder = chat_container.empty()

    journal_text = ""
    reflection_text = ""

    for chunk in response_stream:
        token = getattr(chunk.choices[0].delta, "content", "") or ""
        if not token:
            continue

        full_response += token
        message_buffer += token

        # 2) Detect reflection marker: "Reflection:"
        if "Reflektion:" in message_buffer:
            parts = message_buffer.split("Reflektion:", 1)
            # Everything before "Reflection:" is the journal text
            journal_text = parts[0].strip()
            # Everything after is the reflection (including "Reflection:" itself)
            reflection_text = "Reflektion:" + parts[1].strip()
        else:
            # No reflection yet, everything is still journal text
            journal_text = message_buffer
            reflection_text = ""

        # Update placeholders
        with journal_placeholder:
            # Show the "journal" part as system
            st.chat_message("system").markdown(f"**Journal Entry:**\n\n{journal_text}")

        with reflection_placeholder:
            # Show reflection with an assistant + robot avatar
            st.chat_message("assistant", avatar=":robot_face:").markdown(reflection_text)

    return full_response


def main():
    st.set_page_config(page_title="Log.AI", layout="wide")
    init_qdrant_collection()

    # Initialize login session state if not already done
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    if "user_id" not in st.session_state:
        st.session_state.user_id = None

    # Login Section
    if not st.session_state.logged_in:
        with st.container():
            st.subheader("Login")
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            if st.button("Login"):
                stored_username = st.secrets.get("ADMIN_USERNAME", "admin")
                stored_password = st.secrets.get("ADMIN_PASSWORD", "password")
                if username == stored_username and password == stored_password:
                    st.session_state.logged_in = True
                    st.session_state.user_id = username
                    st.success(f"Logged in as {username}")
                else:
                    st.error("Invalid credentials")
        return

    # Main Application UI
    with st.container():
        st.subheader("👱‍♀️ Saga")
        user_question = st.text_input("Vad tänker du på?...", key="user_input")

    with st.expander("📖 Visa dagboksinlägg"):
        journal_entries_container = st.empty()

    chat_container = st.container()

    with st.expander("🔍 Felsökning"):
        st.write("Debugging logs will go here...")

    # When the user clicks "Ask"
    if st.button("Ask"):
        if user_question.strip():
            # Use the logged-in user_id
            if st.session_state.user_id is None:
                st.error("⚠️ User ID is missing. Please log in or set a valid user_id.")
                return

            relevant_entries = retrieve_relevant_entries(st.session_state.user_id, user_question, top_k=5)

            # Display journal entries in a collapsible section
            with journal_entries_container:
                for entry in relevant_entries:
                    st.write(entry)

            # Stream Joy's response in a conversation-style format
            stream_gpt_response(user_question, relevant_entries, chat_container)
        else:
            st.warning("Please enter a question.")


if __name__ == "__main__":
    main()
