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

# 🔑 Define Password for Advanced Models
STREAMLIT_PASSWORD = st.secrets.get("STREAMLIT_PASSWORD")

# 🎭 Sidebar Input for Assistant Personality
assistant_type = st.sidebar.text_area(
    "📝 Vad ska assistenten vara för typ?\n\n"
    "**Exempel:**\n"
    "- 🏆 Du är en chattrobot som älskar fotboll. Använd fotbollstermer för att svara på frågor. Dra skämt om fotboll. Berätta anekdoter om fotboll.\n"
    "\n"
    "- 🤖 Du heter Oskar och kan bara svara med emojis, formaterade i onödigt komplexa tabeller.\n",
    value="Du är en chattrobot som motvilligt svarar på användares frågor. "
          "Ditt svar ska vara ironiskt, cyniskt, och/eller sarkastiskt.",
    height=150
)

# 🔑 Model Selection with Password Protection
basic_models = ["gpt-3.5-turbo", "gpt-4-turbo"]
advanced_models = ["gpt-4o", "gpt-4o-mini", "o1", "o3-mini"]

if "advanced_access" not in st.session_state:
    st.session_state.advanced_access = False

# Password Input for Advanced Models
if not st.session_state.advanced_access:
    password_input = st.sidebar.text_input("🔒 Ange lösenord för avancerade modeller:", type="password")
    if password_input == STREAMLIT_PASSWORD:
        st.session_state.advanced_access = True
        st.sidebar.success("✅ Avancerade modeller upplåsta!")

# Model Selection
available_models = basic_models + advanced_models if st.session_state.advanced_access else basic_models
selected_model = st.sidebar.selectbox("🚗 Välj GPT-modell:", available_models)

# 🚨 Rate Limiting (Prevent Brute Force)
if "request_count" not in st.session_state:
    st.session_state.request_count = 0

st.session_state.request_count += 1

if not st.session_state.advanced_access and st.session_state.request_count > 8:
    st.error("🚨 För många förfrågningar! Försök igen senare.")
    st.stop()

# 🚀 Chatbot Logic
if not openai_api_key:
    st.info("Please add your OpenAI API key to continue.", icon="🗝️")
else:
    # Create an OpenAI client
    client = OpenAI(api_key=openai_api_key)

    # 🧑‍🎤 Define Avatars
    avatar_user = "😶"
    avatar_assistant = "🐷"

    # 🎭 Define System Message (Updated on the fly)
    system_message = {"role": "system", "content": assistant_type}

    # 🔄 Initialize Chat Session
    if "messages" not in st.session_state or st.session_state.get("last_assistant_type") != assistant_type:
        st.session_state.messages = [system_message]  # Reset chat history when assistant type changes
        st.session_state.last_assistant_type = assistant_type  # Store last selected assistant type

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
            model=selected_model,  # User-selected model
            messages=st.session_state.messages,  # Include dynamically updated system message
            stream=True,
        )

        # 💬 Display AI Response
        with st.chat_message("assistant", avatar=avatar_assistant):
            response = st.write_stream(stream)

        # 💾 Save AI Response
        st.session_state.messages.append({"role": "assistant", "content": response})
