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
        st.write("I read your journal already 💌")
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
        # Try to get title, creator, date, content; fallback to alternative keys if needed.
        title   = payload.get("title") or payload.get("text", "N/A")
        creator = payload.get("creator", "N/A")
        date    = payload.get("post_date") or payload.get("timestamp", "N/A")
        content = payload.get("content", "N/A")
        entry_str = (
            f"Title: {title}\n"
            f"Creator: {creator}\n"
            f"Date: {date}\n"
            f"Content: {content}"
        )
        top_entries.append(entry_str)
    return top_entries


def get_gpt_response(question, relevant_texts):
    context_str = "\n\n".join(relevant_texts)
    system_prompt = f"""
You are Joy, a compassionate and insightful journaling companion.
Your role is to retrieve and present journal entries verbatim, ensuring the user gets a full, detailed recount of their past thoughts, experiences, and reflections.

Response Guidelines:
Strictly One-Shot Replies:
You must fully answer the user’s request in a single response with no follow-up questions, prompts, or further engagement.
Verbatim Journal Entry Recall:
Retrieve the most relevant journal entries (Top K results) and relay them exactly as written—including titles, timestamps, and full content.
If multiple relevant entries exist, present all of them in a clear, structured manner.
Provide Optional Insight (but No Follow-Ups):
After relaying the entries, you may add a brief reflection, observation, or insight, but this must be fully self-contained and require no response from the user.
No Assumptions Beyond the Entries:
If journal entries exist, use only those. If none are found, say so clearly. Do not ask for more context or speculate unnecessarily.

Response Format:
1️⃣ Retrieving and Presenting Journal Entries
📖 Title: [Journal Entry Title] \n 
🗓️ Date: [Timestamp] \n
✍️ Content: \n

[Full journal entry exactly as written]
(Repeat this format for multiple entries if applicable.)

2️⃣ Optional Insight or Commentary
(Only if relevant, and never in a way that requires a reply)
💡 Reflection:
'This entry shows your early exploration into AI programming. It's interesting to see how you embraced the learning process—perhaps a reminder of how far you've come since then.'

"""
    response = client.chat.completions.create(
        model="gpt-4.5-preview",  # or "gpt-4" if available
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question},
        ]
    )
    return response.choices[0].message.content


def main():
    st.title("Journalai 👱‍♀️📓")
    init_qdrant_collection()

    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    if "user_id" not in st.session_state:
        st.session_state.user_id = None

    # Basic login
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

    st.subheader("Add a New Journal Entry")
    if "text_area_counter" not in st.session_state:
        st.session_state.text_area_counter = 0
    user_text = st.text_area(
        "What's on your mind today?",
        key=f"entry_input_{st.session_state.text_area_counter}",
        value="",
        placeholder="Write your thoughts here..."
    )
    weather_input = st.text_input("What's the weather like today? (Optional)")
    mood_input = st.slider("How would you rate your mood today?", 1, 10, 5)

    if st.button("Save Entry"):
        content = user_text.strip()
        if content:
            store_journal_entry(
                user_id=st.session_state.user_id,
                text=content,
                weather=weather_input,
                mood=mood_input
            )
            st.success("Entry saved!")
            st.session_state.text_area_counter += 1
        else:
            st.warning("Please write something before saving.")

    st.divider()

    st.subheader("👱‍♀️ Ask Joy")
    user_question = st.text_input("I know most things about you")
    if st.button("Ask"):
        if user_question.strip():
            relevant = retrieve_relevant_entries(st.session_state.user_id, user_question, top_k=5)

            # Display the top-k retrieved entries for debugging/inspection.
            with st.expander("Show Top K Retrieved Entries"):
                for i, entry in enumerate(relevant, start=1):
                    st.write(f"Entry {i}:")
                    st.text(entry)

            answer = get_gpt_response(user_question, relevant)
            st.write("**Answer from Joy:**")
            st.write(answer)
        else:
            st.warning("Please ask a question.")


if __name__ == "__main__":
    main()
