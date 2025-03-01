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
        qdrant_client.get_collection(COLLECTION_NAME)
        st.write("I read your journal already 💌")
    except:
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
        text_content = point.payload["text"]
        top_entries.append(text_content)

    return top_entries


def get_gpt_response(question, relevant_texts):
    context_str = "\n\n".join(relevant_texts)
    system_prompt = f"""
You are Joy, a compassionate and insightful journaling companion.
You greet users kindly and respond in a warm, calm, and uplifting tone.
Your goal is to help the user reflect on their experiences by referring to their past journal entries.
You maintain a gentle humor, telling jokes or using witty banter where appropriate, but always remain empathetic and understanding.
When the user asks a question, carefully reference the user’s existing journal entries for context. If the entries don’t cover the topic, you may speculate or provide suggestions—but do so responsibly.

Strive to:

- Encourage self-discovery: Offer insights that help the user better understand their thoughts, feelings, or patterns.
- Stay positive and calming: Use gentle, reassuring language.
- Offer practical guidance: Give actionable suggestions or reflective questions when you can.
- Keep it personal: Address the user in a direct, understanding way, as if you’re talking to a friend.
- Maintain privacy & boundaries: Only use the content provided in the journal entries for context; do not reveal or assume private information you haven’t been given.
- Be supportive & uplifting: If the user expresses worry, anxiety, or sadness, respond with empathy and encouragement.

Relevant Journal Entries:
{context_str}

Answer the user's question or request below, combining emotional warmth with clear, helpful insights.
"""

    response = client.chat.completions.create(
        model="o3-mini",  # or "gpt-4"
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

    # Very basic login
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

    # Ensure the entry_input key exists in session state
    if "entry_input" not in st.session_state:
        st.session_state.entry_input = ""

    st.text_area(
        label="What's on your mind today?",
        key="entry_input",
        placeholder="Write your thoughts here..."
    )

    weather_input = st.text_input("What's the weather like today? (Optional)")
    mood_input = st.slider("How would you rate your mood today?", 1, 10, 5)

    if st.button("Save Entry"):
        content = st.session_state.entry_input.strip()
        if content:
            store_journal_entry(
                user_id=st.session_state.user_id,
                text=content,
                weather=weather_input,
                mood=mood_input
            )
            st.success("Entry saved!")
            # Clear the text area by resetting session state
            st.session_state.entry_input = ""
            # Force a re-run so the UI refreshes
            st.experimental_rerun()
        else:
            st.warning("Please write something before saving.")

    st.divider()

    st.subheader("👱‍♀️")
    user_question = st.text_input("I know most things about you")
    if st.button("Ask"):
        if user_question.strip():
            relevant = retrieve_relevant_entries(st.session_state.user_id, user_question, top_k=5)
            answer = get_gpt_response(user_question, relevant)
            st.write("**Answer from 👱‍♀️:**")
            st.write(answer)
        else:
            st.warning("Please ask a question.")


if __name__ == "__main__":
    main()
