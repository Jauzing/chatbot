def stream_gpt_response(question, relevant_texts, chat_container):
    """
    Streams GPT response and dynamically updates a conversation-style display.
    Journal entries appear first, then Joy's reflections.
    """
    if relevant_texts:
        context_str = "\n\n".join(relevant_texts)
    else:
        context_str = "I didn't find anything about that in your Journal."

    system_prompt = """
You are **Joy**, a compassionate and insightful journaling companion. 
Your primary role is to retrieve relevant journal entries and present them verbatim.
After each entry, include a short reflection.
Use this format:
- **Journal Entry:** 📖 [Title] followed by the entry.
- **Reflection:** 👱‍♀️ **Joy**: followed by your insights.

If no relevant journal entry exists, respond with: "I don’t find anything about that in your Journal."
"""

    user_prompt = f"""
**Relevant Journal Entries:**  

{context_str}  

**User Query:**  
{question}
"""

    # Start streaming response
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
    mode = "journal"  # Start in journal mode

    # **Use placeholders to prevent message duplication**
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

        # Detect transition from journal to reflection
        if "👱‍♀️ **Joy**:" in message_buffer:
            parts = message_buffer.split("👱‍♀️ **Joy**:", 1)
            journal_text = parts[0].strip()
            reflection_text = "👱‍♀️ **Joy**:" + parts[1].strip()
            mode = "reflection"
        else:
            journal_text = message_buffer
            reflection_text = ""

        # **Update placeholders instead of adding new messages**
        with journal_placeholder:
            st.chat_message("system").markdown(f"📖 **Journal Entry:**\n\n{journal_text}")

        with reflection_placeholder:
            st.chat_message("assistant").markdown(reflection_text)

    return full_response
