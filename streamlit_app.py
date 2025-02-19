import streamlit as st
from openai import OpenAI

# Show title and description.
st.title("💬 Davids chatbot")
st.write("This is a simple chatbot that uses OpenAI's GPT-4o-mini model to generate responses.")

# Get API key from secrets.toml
openai_api_key = st.secrets.get("OPENAI_API_KEY")

if not openai_api_key:
    st.info("Please add your OpenAI API key to continue.", icon="🗝️")
else:
    # Create an OpenAI client.
    client = OpenAI(api_key=openai_api_key)

    # Define avatars for user and assistant
    avatar_user = "😶"  # User avatar
    avatar_assistant = "🤖"  # Assistant avatar

    # Define system message (modify this to affect tonality)
    system_message = {
        "role": "system",
        "content": "You are a helpful, friendly, and slightly humorous AI assistant. "
                   "Keep responses engaging, professional, and concise."
    }

    # Initialize session state for chat messages
    if "messages" not in st.session_state:
        st.session_state.messages = [system_message]  # Start chat history with system message

    # Display existing chat messages (excluding system message)
    for message in st.session_state.messages:
        if message["role"] != "system":  # Hide system message from chat UI
            avatar = avatar_user if message["role"] == "user" else avatar_assistant
            with st.chat_message(message["role"], avatar=avatar):
                st.markdown(f"<p style='font-size:22px'>{message['content']}</p>", unsafe_allow_html=True)

    # Chat input for user message
    if prompt := st.chat_input("Vad vill du?"):
        # Store and display user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user", avatar=avatar_user):
            st.markdown(prompt)

        # Generate assistant response using OpenAI API
        stream = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=st.session_state.messages,  # Include system message in request
            stream=True,
        )

        # Display assistant response with avatar
        with st.chat_message("assistant", avatar=avatar_assistant):
            response = st.write_stream(stream)

        # Save assistant response to session state
        st.session_state.messages.append({"role": "assistant", "content": response})
