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
        st.write("I have your journal ready 🥰")
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
            f"Title: {title}\n"
            f"Creator: {creator}\n"
            f"Date: {date}\n"
            f"Content: {content}"
        )
        top_entries.append(entry_str)
    return top_entries


def stream_gpt_response(
    question,
    relevant_texts,
    left_placeholder,
    right_placeholder
):
    """
    Streams GPT response while:
      - Streaming journal entries live into the left column.
      - Switching to storing reflections (marked by "👱‍♀️ **Joy**:") in the right column.
      - Switching back when a new journal entry marker (e.g., "📖") appears.
    """
    # Build initial context
    if relevant_texts:
        context_str = "\n\n".join(relevant_texts)
    else:
        context_str = "I didn't find anything about that in your Journal."

    system_prompt = """
You are **Joy**, a compassionate and insightful journaling companion. 
Your primary role is to retrieve relevant journal entries and present them verbatim.
After each entry, include a short reflection.
When presenting multiple entries, precede each entry with "📖 Entry Title:" 
and precede each reflection with "👱‍♀️ **Joy**:".

If no entry is found, respond with: “I don’t find anything about that in your Journal.”
"""

    user_prompt = f"""
**Relevant Journal Entries:**

{context_str}

**User Query:**
{question}
"""

    # Create a stream from the LLM
    response_stream = client.chat.completions.create(
        model="gpt-4o-mini",  # or "gpt-4" if available
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        stream=True
    )

    journal_text = ""
    reflection_text = ""
    full_response = ""
    mode = "journal"  # Start in journal mode

    for chunk in response_stream:
        token = getattr(chunk.choices[0].delta, "content", "") or ""
        if not token:
            continue

        full_response += token

        # Switching logic:
        # If the token includes the reflection marker, switch mode.
        if "👱‍♀️ **Joy**:" in token:
            # Split at the first occurrence of the reflection marker
            parts = token.split("👱‍♀️ **Joy**:", 1)
            journal_text += parts[0]
            reflection_text += "👱‍♀️ **Joy**:" + parts[1]
            mode = "reflection"
        # If a new journal entry marker appears (e.g., "📖"), switch back
        elif "📖" in token:
            mode = "journal"
            journal_text += "\n\n" + token
        else:
            if mode == "journal":
                journal_text += token
            else:
                reflection_text += token

        # Update the left placeholder (journal) live
        left_placeholder.markdown(f"### Journal Pages\n\n{journal_text}")

    # After streaming, do a final re-render so that the reflection text is correctly shown on the right.
    right_placeholder.markdown(f"### Joy's Insights\n\n{reflection_text.strip()}")

    return full_response



def main():
    st.set_page_config(page_title="Log.AI", layout="wide")
    init_qdrant_collection()

    # Basic Login
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    if "user_id" not in st.session_state:
        st.session_state.user_id = None

    if not st.session_state.logged_in:
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

    # Two columns for output: left (journal pages), right (reflections)
    col_left, col_right = st.columns([3, 3])
    with col_left:
        left_placeholder = st.empty()
    with col_right:
        right_placeholder = st.empty()

    st.divider()
    st.subheader("👱‍♀️ Ask Joy")
    user_question = st.text_input("I know most things about you")
    if st.button("Ask"):
        if user_question.strip():
            relevant = retrieve_relevant_entries(st.session_state.user_id, user_question, top_k=5)
            with st.expander("Show Top K Retrieved Entries"):
                st.write("📚 **Top K Retrieved Entries**")
                st.write(relevant)

            # Stream the response (with partial updates)
            stream_gpt_response(user_question, relevant, left_placeholder, right_placeholder)
        else:
            st.warning("Please ask a question.")


if __name__ == "__main__":
    main()
