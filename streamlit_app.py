import streamlit as st
import requests
from openai import OpenAI
from datetime import datetime
import json

# 🚀 Titel och beskrivning
st.title("🐷 Piglet")
st.write("Chattrobot av Thom & Deer.")

# 🔐 Ladda OpenAI API-nyckeln från secrets
openai_api_key = st.secrets.get("OPENAI_API_KEY")

# 🔑 Hämta lösenordet för avancerade modeller från secrets
STREAMLIT_PASSWORD = st.secrets.get("STREAMLIT_PASSWORD")

# 🎭 Sidofält: Ange assistentens personlighet
assistant_type = st.sidebar.text_area(
    "📝 Vad ska assistenten vara för typ?\n\n"
    "**Exempel:**\n"
    "- 🏆 Du är en chattrobot som älskar fotboll. Använd fotbollstermer för att svara på frågor. Dra skämt om fotboll. Berätta anekdoter om fotboll.\n",
    value=" ",
    height=150
)

# 🔑 Modellval med lösenordsskydd
basic_models = ["gpt-3.5-turbo", "gpt-4-turbo"]
advanced_models = ["gpt-4o", "gpt-4o-mini", "o1", "o3-mini"]

if "advanced_access" not in st.session_state:
    st.session_state.advanced_access = False

# Lösenordsinmatning för avancerade modeller
if not st.session_state.advanced_access:
    password_input = st.sidebar.text_input("🔒 Ange lösenord för avancerade modeller:", type="password")
    if password_input == STREAMLIT_PASSWORD:
        st.session_state.advanced_access = True
        st.sidebar.success("✅ Avancerade modeller upplåsta!")

# Modellval
available_models = basic_models + advanced_models if st.session_state.advanced_access else basic_models
selected_model = st.sidebar.selectbox("🚗 Välj GPT-modell:", available_models)

# Informationsruta med modellbeskrivningar
with st.sidebar.expander("ℹ️ Modellinformation"):
    st.markdown(
        """
        **gpt-3.5-turbo:** Effektiv, snabb och utmärkt för allmänna uppgifter med måttligt resonemang.  
        **gpt-4-turbo:** Förbättrad prestanda med starkare resonemangsförmåga.

        **gpt-4o:** Erbjuder avancerade resonemang och tankekedjor (chain-of-thought).  
        **gpt-4o-mini:** En kompakt version som levererar avancerat resonemang till en lägre kostnad.  
        **o1:** Optimerad för uppgifter som kräver djupgående analys och resonemang (Reasoning model).  
        **o3-mini:** En mini-version av kommande o3, som balanserar kostnad med djupgående resonemang.
        """
    )

# 🚨 Rate Limiting (gäller endast för användare utan avancerad åtkomst)
if "request_count" not in st.session_state:
    st.session_state.request_count = 0

st.session_state.request_count += 1

if not st.session_state.advanced_access and st.session_state.request_count > 8:
    st.error("🚨 För många förfrågningar! Försök igen senare.")
    st.stop()

# 🚀 Chattbot-logik
if not openai_api_key:
    st.info("Vänligen lägg till din OpenAI API-nyckel för att fortsätta.", icon="🗝️")
else:
    # Skapa en OpenAI-klient
    client = OpenAI(api_key=openai_api_key)

    # 🧑‍🎤 Definiera avatars
    avatar_user = "😶"
    avatar_assistant = "🐷"

    # 🎭 Definiera systemmeddelande (uppdateras dynamiskt)
    system_message = {"role": "system", "content": assistant_type}

    # 🔄 Initiera chatt-session
    if "messages" not in st.session_state or st.session_state.get("last_assistant_type") != assistant_type:
        st.session_state.messages = [system_message]
        st.session_state.last_assistant_type = assistant_type

    # 📜 Visa tidigare meddelanden (dölj systemmeddelandet)
    for message in st.session_state.messages:
        if message["role"] != "system":
            avatar = avatar_user if message["role"] == "user" else avatar_assistant
            with st.chat_message(message["role"], avatar=avatar):
                st.markdown(f"<p style='font-size:22px'>{message['content']}</p>", unsafe_allow_html=True)

    # ✍️ Användarens inmatning
    if prompt := st.chat_input("Vad vill du?"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user", avatar=avatar_user):
            st.markdown(prompt)

        # 🤖 Generera AI-svar
        stream = client.chat.completions.create(
            model=selected_model,
            messages=st.session_state.messages,
            stream=True,
        )

        # 💬 Visa AI-svar
        with st.chat_message("assistant", avatar=avatar_assistant):
            response = st.write_stream(stream)

        # 💾 Spara AI-svar
        st.session_state.messages.append({"role": "assistant", "content": response})
