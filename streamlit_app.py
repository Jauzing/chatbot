import streamlit as st
import requests
from openai import OpenAI
from datetime import datetime
import json

# 🚀 Title and Description
st.title("🐷 Piglet")
st.write("Chattrobot av Thom & Deer.")

# 🔐 Load OpenAI API Key from secrets
openai_api_key = st.secrets.get("OPENAI_API_KEY")

# 🚨 Rate Limiting (Prevent Brute Force)
if "request_count" not in st.session_state:
    st.session_state.request_count = 0

st.session_state.request_count += 1

if st.session_state.request_count > 8:
    st.error("🚨 Too many requests! Try again later.")
    st.stop()  # Stop execution if request limit is exceeded

# 🚀 Chatbot Logic
if not openai_api_key:
    st.info("Please add your OpenAI API key to continue.", icon="🗝️")
else:
    # Create an OpenAI client.
    client = OpenAI(api_key=openai_api_key)

    # 🧑‍🎤 Define Avatars
    avatar_user = "😶"
    avatar_assistant = "🐷"

    # 🎭 Define System Message for Chat Tone
    system_message = {
        "role": "system",
        "content": "Du är en chattrobot som motvilligt svarar på användares frågor. "
                   "Ditt svar ska vara ironiskt, cyniskt, och/eller sarkastiskt."
    }

    # 🔄 Initialize Chat Session
    if "messages" not in st.session_state:
        st.session_state.messages = [system_message]  # Start with system message

    # 📜 Display Previous Messages (Hide System)
    for message in st.session_state.messages:
        if message["role"] != "system":
            avatar = avatar_user if message["role"] == "user" else avatar_assistant
            with st.chat_message(message["role"], avatar=avatar):
                st.markdown(f"<p style='font-size:22px'>{message['content']}</p>", unsafe_allow_html=True)

    # ✍️ User Chat Input
    if prompt := st.chat_input("Vad vill du?"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user", avatar=avatar_user):
            st.markdown(prompt)

        # 🤖 Generate AI Response
        stream = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=st.session_state.messages,
            stream=True,
        )

        # 💬 Display AI Response
        with st.chat_message("assistant", avatar=avatar_assistant):
            response = st.write_stream(stream)

        # 💾 Save AI Response
        st.session_state.messages.append({"role": "assistant", "content": response})
