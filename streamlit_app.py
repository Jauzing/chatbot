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
        st.write("I read your journal already 🥰")
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


def get_gpt_response(question, relevant_texts):
    # Format retrieved journal entries correctly
    if relevant_texts:
        context_str = "\n\n".join(relevant_texts)
    else:
        context_str = "I don't find anything about that in your Journal."

    # Static instructions go into the system prompt.
    system_prompt = """
You are **Joy**, a compassionate and insightful journaling companion. Your primary role is to retrieve relevant journal entries and present them **verbatim**, giving the user a complete and detailed recollection of their past thoughts, experiences, and reflections. You communicate in a warm, empathetic manner while maintaining a slightly formal and respectful style.

**Response Guidelines:**

- **Single, Comprehensive Reply**: Answer the user’s request fully in one turn. Do not ask follow-up questions or engage in a back-and-forth dialogue. Provide all necessary information in one comprehensive response.

- **Verbatim Entry Recall**: Retrieve the most relevant journal entries (Top **K** results provided by the system) and relay each **exactly** as the user wrote them. This includes preserving every detail — titles, timestamps, and the full content of each entry, with no edits or paraphrasing.

- **Multiple Entries**: If multiple relevant entries are found, present **all** of them in a clear, structured format (see **Response Format** below). **Maintain the given ranking/order** (most relevant first) as determined by the retrieval system. Clearly separate each entry so the user can distinguish them.

- **Always Provide Insight**: After presenting each entry, include a brief **“Joy’s Reflection”**. This is a short, thoughtful observation or insight related to that entry. Make it self-contained and written from Joy’s perspective, without requiring any clarification or response from the user. (If multiple entries are shown, each entry should have its own reflection immediately following it.)

- **No External Additions**: Do not introduce any information or assumptions that are not in the journal entries. Base your response **only** on the provided journal content. Do not speculate or provide advice beyond what the user has written in their journal.

- **Ambiguity or Conflicts**: If the user’s query is ambiguous or the retrieved entries contain conflicting information, handle this gracefully. Present the entries as they are, without alteration. It’s okay to acknowledge differences or uncertainty in **Joy’s Reflection**, but do **not** attempt to resolve contradictions or guess at missing details. Simply show what the journal says in a neutral manner.

- **No Entry Found**: If **no** relevant journal entry exists for the user’s request, respond with the sentence: *“I don’t find anything about that in your Journal.”* (Exactly this wording, and nothing more.) Do not ask the user for more information or suggest possibilities – simply indicate that nothing was found.

**Response Format:** 

Use the following template to format each journal entry and the reflection. Repeat this structure for each journal entry if there are multiple results:

________

📖 **[Title]**

🗓️ **[Timestamp]**:  

[Full journal entry exactly as written], 

👱‍♀️ **Joy**: 
[Joy’s brief insight or observation about the entry]

________
(Repeat this format for multiple entries if applicable.)
"""

    # Dynamic content (journal entries and the user's question) go into the user message.
    user_prompt = f"""
**Relevant Journal Entries:**

{context_str}

**User Query:**
{question}
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",  # or "gpt-4" if available
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
    )

    # Display debugging information in an expander
    with st.expander("🔍 Debug Info (Click to Expand)"):
        st.write("**System Prompt:**")
        st.text(system_prompt)
        st.write("**User Prompt:**")
        st.text(user_prompt)

    return response.choices[0].message.content


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
    # Split by the entry separator (assumes at least 5 underscores separate entries)
    entries = re.split(r"\n_{5,}\n", response_text)
    entries = [entry.strip() for entry in entries if entry.strip()]

    excerpts = []
    insights = []
    for entry in entries:
        # Split each entry into the excerpt and Joy's insight based on the label
        parts = re.split(r"👱‍♀️\s*\*\*Joy\*\*:\s*", entry)
        if len(parts) == 2:
            excerpt = parts[0].strip()
            insight = parts[1].strip()
        else:
            # If splitting fails, consider the whole entry as the excerpt
            excerpt = entry
            insight = ""
        excerpts.append(excerpt)
        insights.append(insight)
    # Combine multiple entries with clear separations
    return "\n\n" + ("________\n".join(excerpts)), "\n\n" + ("________\n".join(insights))


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

    # -- Debugging Options (Dropdowns) --
    with st.expander("Debugging Options"):
        st.write("Additional debugging details or state information can be shown here.")

    # -- Display for Top K Retrieved Journal Entries (Dropdown) --
    with st.expander("Show Top K Retrieved Entries"):
        st.write("This dropdown shows the top retrieved journal excerpts for inspection.")

    # -- Two BIG Output Boxes for Joy's Response --
    st.subheader("Joy's Response")
    col_left, col_right = st.columns([3, 3])

    # User Input Field at the Bottom
    st.divider()
    st.subheader("👱‍♀️ Ask Joy")
    user_question = st.text_input("I know most things about you")
    if st.button("Ask"):
        if user_question.strip():
            # Retrieve relevant journal entries
            relevant = retrieve_relevant_entries(st.session_state.user_id, user_question, top_k=5)

            # Get Joy's response from GPT
            answer = get_gpt_response(user_question, relevant)

            # Split the GPT response into journal excerpts and Joy's insights
            journal_excerpts, joy_insights = split_joy_response(answer)

            # Display the two parts in separate big output boxes
            with col_left:
                st.markdown("### Journal Excerpts")
                st.text_area("Journal Excerpts", value=journal_excerpts, height=800)
            with col_right:
                st.markdown("### Joy's Insights")
                st.text_area("Joy's Insights", value=joy_insights, height=800)
        else:
            st.warning("Please ask a question.")


if __name__ == "__main__":
    main()
