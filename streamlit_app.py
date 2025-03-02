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


def store_journal_entry(user_id, text, weather=None, mood=None):
    embedding = embed_text(text)
    payload = {
        "user_id": user_id,
        "text": text,
        "timestamp": str(datetime.datetime.now()),
        "weather": weather,
        "mood": mood
    }
    qdrant_client.upsert(
        collection_name=COLLECTION_NAME,
        points=[
            qdrant_models.PointStruct(
                id=str(uuid.uuid4()),
                vector=embedding,
                payload=payload
            )
        ]
    )


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


def split_joy_response(response_text):
    """
    Splits Joy's response into two parts:
      - Left: Journal excerpts (everything before Joy's reflection in each entry)
      - Right: Joy's insights (the reflection portion for each entry)
    It assumes the model's response follows the structure:
      ________
      ...journal excerpt...
      👱‍♀️ **Joy**:
      ...joy's reflection...
      ________
    """
    entries = re.split(r"\n_{5,}\n", response_text)
    entries = [entry.strip() for entry in entries if entry.strip()]
    excerpts = []
    insights = []
    for entry in entries:
        parts = re.split(r"👱‍♀️\s*\*\*Joy\*\*:\s*", entry)
        if len(parts) == 2:
            excerpt = parts[0].strip()
            insight = parts[1].strip()
        else:
            excerpt = entry
            insight = ""
        excerpts.append(excerpt)
        insights.append(insight)
    return "\n\n" + ("________\n".join(excerpts)), "\n\n" + ("________\n".join(insights))


def stream_gpt_response(question, relevant_texts, left_placeholder, right_placeholder):
    """
    Streams the GPT response token by token and updates two placeholders.
    Uses st.markdown to update the output in real time.
    """
    if relevant_texts:
        context_str = "\n\n".join(relevant_texts)
    else:
        context_str = "I didn't find anything about that in your Journal."

    system_prompt = """
You are **Joy**, a compassionate and insightful journaling companion. Your primary role is to retrieve relevant journal entries and present them **verbatim**, giving the user a complete and detailed recollection of their past thoughts, experiences, and reflections. You communicate in a warm, empathetic manner while maintaining a slightly formal and respectful style.

**Response Guidelines:**

- **Single, Comprehensive Reply**: Answer the user’s request fully in one turn. Do not ask follow-up questions or engage in a back-and-forth dialogue. Provide all necessary information in one comprehensive response.

- **Verbatim Entry Recall**: Retrieve the most relevant journal entries (Top **K** results provided by the system) and relay each **exactly** as the user wrote them. This includes preserving every detail — titles, timestamps, and the full content of each entry, with no edits or paraphrasing.

- **Multiple Entries**: If multiple relevant entries are found, present **all** of them in a clear, structured format. Clearly separate each entry so the user can distinguish them.

- **Always Provide Insight**: After each entry, include a brief **“Joy’s Reflection”** with a short insight.

- **No External Additions**: Base your response **only** on the provided journal content.

- **No Entry Found**: If no relevant journal entry exists, respond with: “I don’t find anything about that in your Journal.”

**Response Format:** 

Use the following template for each entry:

________

📖 **[Title]**

🗓️ **[Timestamp]**:  

[Journal entry exactly as written], 

👱‍♀️ **Joy**: 
[Joy’s brief insight]

________
"""

    user_prompt = f"""
**Relevant Journal Entries:**

{context_str}

**User Query:**
{question}
"""

    # Start streaming with stream=True
    response_stream = client.chat.completions.create(
        model="gpt-4o-mini",  # or "gpt-4" if available
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        stream=True
    )

    full_response = ""
    # Stream tokens as they are generated
    for chunk in response_stream:
        # Access token content
        token = getattr(chunk.choices[0].delta, "content", "") or ""
        full_response += token
        # Split the response to update outputs
        journal_excerpts, joy_insights = split_joy_response(full_response)
        # Update the placeholders using markdown to avoid duplicate widget keys
        left_placeholder.markdown(f"### Journal pages\n\n{journal_excerpts}")
        right_placeholder.markdown(f"### Joy's take\n\n{joy_insights}")

    return full_response


def main():
    st.set_page_config(page_title="Log.AI", layout="wide")
    init_qdrant_collection()

    # -- Basic Login --
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

    # -- Two BIG Output Boxes for Joy's Response --
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
            # Stream the response and update output containers in real time
            stream_gpt_response(user_question, relevant, left_placeholder, right_placeholder)
        else:
            st.warning("Please ask a question.")


if __name__ == "__main__":
    main()
