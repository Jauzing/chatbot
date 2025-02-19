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

# 🌎 Function to Get Real User IP and Location
def get_real_ip():
    """Fetch the real IP address of the user by checking request headers."""
    try:
        # Get external IP via httpbin (bypasses Google/Streamlit proxy)
        response = requests.get("https://httpbin.org/ip")
        return response.json().get("origin", "Unknown")
    except Exception:
        return "Unknown"

def get_user_info():
    """Fetch user details from IP info service."""
    user_ip = get_real_ip()
    try:
        response = requests.get(f"https://ipinfo.io/{user_ip}/json")
        data = response.json()
        return {
            "ip": user_ip,
            "city": data.get("city", "Unknown"),
            "country": data.get("country", "Unknown"),
            "region": data.get("region", "Unknown"),
            "org": data.get("org", "Unknown"),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
    except Exception as e:
        return {"ip": user_ip, "error": str(e)}

# 🚫 Geo-Blocking (Deny Access for Specific Countries)
blocked_countries = ["CN", "RU", "KP", "IR"]  # China, Russia, North Korea, Iran
user_info = get_user_info()

if user_info.get("country") in blocked_countries:
    st.error("🚨 Access Denied: Your country is restricted.")
    st.stop()  # Stop execution for blocked users

# 📜 Log Visitors
log_file = "visitor_log.json"

# Load previous logs
try:
    with open(log_file, "r") as f:
        visitor_logs = json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
    visitor_logs = []

# Append new visitor and save logs
visitor_logs.append(user_info)

with open(log_file, "w") as f:
    json.dump(visitor_logs, f, indent=4)

# 📝 Display Visitor Log
st.write("### Visitor Log")
st.table(visitor_logs)

# 🚨 Rate Limiting (Prevent Brute Force)
if "request_count" not in st.session_state:
    st.session_state.request_count = 0

st.session_state.request_count += 1

if st.session_state.request_count > 10:
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
