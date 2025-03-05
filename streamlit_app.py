import re
import streamlit as st
from openai import OpenAI
import os
from qdrant_client import QdrantClient
from qdrant_client.http import models as qdrant_models
import uuid
import datetime

# 🔥 Welcome to the Underground 🔥
# This is a slick journaling app that stores and retrieves entries from Qdrant,
# and summons the power of OpenAI's GPT-4o-mini to reflect on your thoughts.
# It’s got embeddings, a bit of authentication, and a smooth streaming chat.

client = OpenAI()

# --- 🏴‍☠️ QDRANT SETUP (VECTOR DATABASE) ---
# Qdrant: The unsung hero storing high-dimensional vectors.
QDRANT_URL = "https://67bd4e7c-9e18-4183-8655-cb368b598d90.europe-west3-0.gcp.cloud.qdrant.io"
QDRANT_API_KEY = st.secrets["QDRANT_API_KEY"]

qdrant_client = QdrantClient(
    url=QDRANT_URL,
    api_key=QDRANT_API_KEY,
    prefer_grpc=False  # Because sometimes, gRPC is just overkill.
)

COLLECTION_NAME = "journal_entries"


def init_qdrant_collection():
    """ Ensures the Qdrant collection exists, otherwise creates it. """
    vector_size = 1536  # Matches OpenAI's "text-embedding-3-small"
    try:
        collections_info = qdrant_client.get_collections()
        collection_names = [col.name for col in collections_info.collections]
    except Exception as e:
        st.error(f"Error fetching collections: {e}")
        collection_names = []

    if COLLECTION_NAME in collection_names:
        st.write(" ")  # Don't want any confirmation message atm, just works.
    else:
        qdrant_client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=qdrant_models.VectorParams(size=vector_size, distance="Cosine")
        )
        st.write("🚀 Created a new collection in Qdrant.")


# --- 🤖 TEXT EMBEDDING ---
def embed_text(text: str) -> list[float]:
    """ Converts input text into a vector embedding using OpenAI. """
    response = client.embeddings.create(
        input=text,
        model="text-embedding-3-small"
    )
    return response.data[0].embedding  # Returning pure vector goodness.


# --- 🔍 RETRIEVING RELEVANT ENTRIES ---
def retrieve_relevant_entries(user_id, query_text, top_k=3):
    """
    Fetches the top K most relevant journal entries based on vector similarity.
    Uses cosine distance because, well, that’s what the cool kids use.
    """
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

        entry_str = f"📖 **{title}**\n🗓️ {date}\n\n{content}"
        top_entries.append(entry_str)

    return top_entries


# --- 🧠 STREAMING GPT RESPONSE ---
def stream_gpt_response(question, relevant_texts, chat_container):
    """
    Streams GPT response dynamically.
    - Retrieves journal entries as context.
    - Generates a reflection (always in Swedish 🇸🇪).
    - Uses smart placeholders to avoid flickering UI updates.
    """
    if relevant_texts:
        context_str = "\n\n".join(relevant_texts)
    else:
        context_str = "Jag hittar inget om det i din dagbok 😐."

    system_prompt = """
    Du är en empatisk och insiktsfull dagbokskompanjon. 
    Din uppgift är att hämta relevanta dagboksinlägg och ge en reflektion.
    Alla svar måste vara på svenska.

    - **Inlägg:** 
      [Visa inläggen]

    - **Reflektion:** 
      [Din insikt här]
    """

    user_prompt = f"""
    **Relevanta dagboksinlägg:**  

    {context_str}  

    **Användarens fråga:**  
    {question}
    """

    response_stream = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        stream=True
    )

    full_response = ""
    message_buffer = ""
    journal_placeholder = chat_container.empty()
    reflection_placeholder = chat_container.empty()

    journal_text = ""
    reflection_text = ""


    # --- 📸 SET LOCAL AVATAR IMAGE ---
    # Define the local image path (inside "static/" folder)
    avatar_filename = "static/noras.PNG"
    avatar_path = os.path.join(os.path.dirname(__file__), avatar_filename)

    # Check if the file exists and serve it correctly
    if os.path.exists(avatar_path):
        # Streamlit needs a public URL or in-memory image, so we use `st.image()` workaround
        avatar_image = avatar_path
    else:
        st.warning(f"⚠️ Avatar image '{avatar_filename}' not found! Using fallback URL.")
        avatar_image = "https://raw.githubusercontent.com/your-user/your-repo/main/static/noras.png"  # Replace with actual hosted URL

    for chunk in response_stream:
        token = getattr(chunk.choices[0].delta, "content", "") or ""
        if not token:
            continue
        full_response += token
        message_buffer += token

        if "Reflektion:" in message_buffer:
            parts = message_buffer.split("Reflektion:", 1)
            journal_text = parts[0].strip()
            reflection_text = "Reflektion:" + parts[1].strip()
        else:
            journal_text = message_buffer
            reflection_text = ""

        with journal_placeholder:
            st.chat_message("system").markdown(f"**Inlägg:**\n\n{journal_text}")

        with reflection_placeholder:
            # ✅ FIX: Use `avatar_image`, whether it's a valid local file or fallback URL
            st.chat_message("assistant", avatar=avatar_image).markdown(reflection_text)

    return full_response

# --- 🚀 MAIN APP ---
def main():
    """ Streamlit UI and authentication flow """
    st.set_page_config(page_title="Log.AI", layout="wide")
    init_qdrant_collection()

    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    if "user_id" not in st.session_state:
        st.session_state.user_id = None

    if not st.session_state.logged_in:
        with st.container():
            st.subheader("🔐 Login")
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")

            if st.button("Login"):
                stored_username = st.secrets.get("ADMIN_USERNAME", "admin")
                stored_password = st.secrets.get("ADMIN_PASSWORD", "password")

                if username == stored_username and password == stored_password:
                    st.session_state.logged_in = True
                    st.session_state.user_id = username
                    st.success(f"🎉 Logged in as {username}")
                else:
                    st.error("🚨 Invalid credentials")
        return

    with st.container():
        st.subheader("👱‍♀️ Saga - Din Dagbokskompanjon")
        user_question = st.text_input("Vad tänker du på?...", key="user_input")

    chat_container = st.container()

    if st.button("🔎 Sök"):
        if user_question.strip():
            if st.session_state.user_id is None:
                st.error("⚠️ User ID saknas. Logga in först.")
                return

            relevant_entries = retrieve_relevant_entries(st.session_state.user_id, user_question, top_k=5)

            with st.expander("🔍 Felsökning", expanded=True):
                st.write("📚 **Top K hämtade inlägg:**")
                st.write(relevant_entries)

            stream_gpt_response(user_question, relevant_entries, chat_container)
        else:
            st.warning("⚠️ Skriv en fråga först.")


if __name__ == "__main__":
    main()
