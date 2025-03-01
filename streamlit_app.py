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
        st.write("Collection already exists.")
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
    # Embed the query text
    query_embedding = embed_text(query_text)

    # Query Qdrant using query_points with the correct parameter name
    query_result = qdrant_client.query_points(
        collection_name=COLLECTION_NAME,
        vector=query_embedding,  # use "vector" instead of "query_vector"
        limit=top_k
    )

    # Extract and return the text from the payloads of the retrieved points
    top_entries = []
    for point in query_result:
        text_content = point.payload["text"]
        top_entries.append(text_content)

    return top_entries

# 5. Function to get GPT’s answer, given top entries
def get_gpt_response(question, relevant_texts):
    # Combine relevant texts into a single context
    context_str = "\n\n".join(relevant_texts)
    system_prompt = (
        "You are a helpful AI. The user has journal entries. "
        "Use the provided content to answer the user's question or provide insights. "
        "If the information is not in the entries, you can speculate responsibly, "
        "but prefer to stick to the content.\n\n"
        f"Relevant Journal Entries:\n{context_str}\n\n"
        "Answer the user's question below.\n\n"
    )

    # Use GPT-3.5 or GPT-4 (depending on your access)
    response = client.ChatCompletion.create(
        model="gpt-3.5-turbo",  # or gpt-4 if you have access
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question},
        ],
        temperature=0.7
    )

    answer = response["choices"][0]["message"]["content"]
    return answer

# 6. Main Streamlit UI
def main():
    st.title("My Simple Journal App")

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

    st.subheader("Ask GPT About Your Journal")
    user_question = st.text_input("Ask a question about your journal entries")
    if st.button("Get Answer"):
        if user_question.strip():
            # 1) Retrieve top relevant entries
            relevant = retrieve_relevant_entries(st.session_state.user_id, user_question, top_k=5)
            # 2) Get GPT’s response
            answer = get_gpt_response(user_question, relevant)
            st.write("**Answer from GPT:**")
            st.write(answer)
        else:
            st.warning("Please ask a question.")

if __name__ == "__main__":
    main()
