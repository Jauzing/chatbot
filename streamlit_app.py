import streamlit as st
from openai import OpenAI

# Show title and description.
st.title("💬 Davids chatbot")
st.write(
    "This is a simple chatbot that uses OpenAI's GPT-3.5 model to generate responses. "
)

# Ask user for their OpenAI API key via `st.text_input`.
# Alternatively, you can store the API key in `./.streamlit/secrets.toml` and access it
# via `st.secrets`, see https://docs.streamlit.io/develop/concepts/connections/secrets-management

# get api key from secrets.toml
openai_api_key = st.secrets.get("OPENAI_API_KEY")

if not openai_api_key:
    st.info("Please add your OpenAI API key to continue.", icon="🗝️")
else:

    # Create an OpenAI client.
    client = OpenAI(api_key=openai_api_key)

    # Create a session state variable to store the chat messages. This ensures that the
    # messages persist across reruns.
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Define avatars for user and assistant
    avatar_user = "😶"  # Or use a custom image path
    avatar_assistant = "🤖"  # Or use a custom image path
    
    # Display the existing chat messages via `st.chat_message`.
    for message in st.session_state.messages:
            avatar = avatar_user if message["role"] == "user" else avatar_assistant
            with st.chat_message(message["role"], avatar=avatar):
                st.markdown(f"<p style='font-size:22px'>{message['content']}</p>", unsafe_allow_html=True)
                st.markdown(message["content"])

    # Create a chat input field to allow the user to enter a message. This will display
    # automatically at the bottom of the page.
    if prompt := st.chat_input("Vad vill du?"):

        # Store and display the current prompt.
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Generate a response using the OpenAI API.
        stream = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": m["role"], "content": m["content"]}
                for m in st.session_state.messages
            ],
            stream=True,
        )

        # Display assistant response with avatar
        with st.chat_message("assistant", avatar=avatar_assistant):
            response = st.write_stream(stream)
            
        # Save response to session state
        st.session_state.messages.append({"role": "assistant", "content": response})
