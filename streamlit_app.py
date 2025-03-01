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

# Collection name in Qdrant
COLLECTION_NAME = "journal_entries"


# 1. Create (or ensure) a Qdrant collection for journal entries
def init_qdrant_collection():
    # Vector size depends on the embedding model.
    # e.g. text-embedding-ada-002 returns 1536-dimensional vectors.
    vector_size = 1536

    try:
        qdrant_client.get_collection(COLLECTION_NAME)
        st.write("I read your journal already 💌")
    except:
        qdrant_client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=qdrant_models.VectorParams(size=vector_size, distance="Cosine")
        )
        st.write("Created a new collection in Qdrant.")

# 2. Function to embed text using OpenAI
def embed_text(text: str) -> list[float]:
    response = client.embeddings.create(
        input=text,
        model="text-embedding-3-small"  # or "text-embedding-3-large" if preferred
    )
    embedding = response.data[0].embedding
    return embedding

# 3. Store a journal entry in Qdrant
def store_journal_entry(user_id, text):
    embedding = embed_text(text)

    # upsert into Qdrant
    qdrant_client.upsert(
        collection_name=COLLECTION_NAME,
        points=[
            qdrant_models.PointStruct(
                id=str(uuid.uuid4()),
                vector=embedding,
                payload={
                    "user_id": user_id,
                    "text": text,
                    "timestamp": str(datetime.datetime.now())
                }
            )
        ]
    )

# 4. Retrieve top-k relevant entries from Qdrant
def retrieve_relevant_entries(user_id, query_text, top_k=3):
    # 1. Embed the query text
    query_embedding = embed_text(query_text)

    # 2. Query Qdrant
    response = qdrant_client.query_points(
        collection_name=COLLECTION_NAME,
        query=query_embedding,
        limit=top_k,
        with_payload=True,
        with_vectors=False
    )

    # 3. Extract and return text from the payloads.
    # 'response' is a QueryResponse object; use response.points to get a list of records.
    top_entries = []
    for point in response.points:
        text_content = point.payload["text"]
        top_entries.append(text_content)

    return top_entries


# 5. Function to get GPT’s answer, given top entries
def get_gpt_response(question, relevant_texts):
    # Combine relevant texts into a single context
    context_str = "\n\n".join(relevant_texts)
    system_prompt = (

        f"""
        You are Joy, a compassionate and insightful journaling companion.
You greet users kindly and respond in a warm, calm, and uplifting tone.
Your goal is to help the user reflect on their experiences by referring to their past journal entries.
You maintain a gentle humor, telling jokes or using witty banter where appropriate, but always remain empathetic and understanding.
When the user asks a question, carefully reference the user’s existing journal entries for context. If the entries don’t cover the topic, you may speculate or provide suggestions—but do so responsibly.
Strive to:

Encourage self-discovery: Offer insights that help the user better understand their thoughts, feelings, or patterns.

Stay positive and calming: Use gentle, reassuring language.

Offer practical guidance: Give actionable suggestions or reflective questions when you can.

Keep it personal: Address the user in a direct, understanding way, as if you’re talking to a friend.

Maintain privacy & boundaries: Only use the content provided in the journal entries for context; do not reveal or assume private information you haven’t been given.

Be supportive & uplifting: If the user expresses worry, anxiety, or sadness, respond with empathy and encouragement.

Relevant Journal Entries: {context_str}

Answer the user's question or request below, combining emotional warmth with clear, helpful insights.
"""
    )

    # Use GPT-3.5 or GPT-4 (depending on your access)
    response = client.chat.completions.create(
        model="o3-mini",  # or gpt-4 if you have access
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question},
        ]
    )

    answer = response.choices[0].message.content
    return answer

# 6. Main Streamlit UI
def main():
    st.title("Journalai 👱‍♀️📓")

    # Initialization: create collection in Qdrant if needed
    init_qdrant_collection()

    # Simple login
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    if "user_id" not in st.session_state:
        st.session_state.user_id = None

    # Login form
    if not st.session_state.logged_in:
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.button("Login"):
            # Super naive check - obviously not secure
            if username and password:
                st.session_state.logged_in = True
                st.session_state.user_id = username  # or a hashed version
                st.success(f"Logged in as {username}")
            else:
                st.error("Invalid credentials")
        return

    st.subheader("Add a New Journal Entry")
    new_entry_text = st.text_area("What's on your mind today?")
    if st.button("Save Entry"):
        if new_entry_text.strip():
            store_journal_entry(st.session_state.user_id, new_entry_text)
            st.success("Entry saved!")
        else:
            st.warning("Please write something before saving.")

    st.divider()  # just a horizontal line

    st.subheader("👱‍♀️")
    user_question = st.text_input("I know most things about you")
    if st.button("Ask"):
        if user_question.strip():
            # 1) Retrieve top relevant entries
            relevant = retrieve_relevant_entries(st.session_state.user_id, user_question, top_k=5)
            # 2) Get GPT’s response
            answer = get_gpt_response(user_question, relevant)
            st.write("**Answer from 👱‍♀️ :**")
            st.write(answer)
        else:
            st.warning("Please ask a question.")

if __name__ == "__main__":
    main()
