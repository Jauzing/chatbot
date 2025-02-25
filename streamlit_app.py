import streamlit as st
import random
import time
from openai import OpenAI
from datetime import datetime
import requests

# 🚀 Title and Description
st.set_page_config(page_title="Fredrik News Network", layout="wide")
st.title("📰 BIGRED News Network (BNN)")
st.write("Bringing you swell news about Fredrik, all day err' day.")

# OpenAI API Key
openai_api_key = st.secrets.get("OPENAI_API_KEY")
client = OpenAI(api_key=openai_api_key)


# 📰 Fake Breaking News Headlines
def generate_headline():
    headlines = [
        "Fredrik Accidentally Invents Time Travel but Only Goes Back 7 Minutes",
        "Study Shows 98% of Fredriks Have No Idea What's Happening Right Now",
        "Fredrik Declares Himself 'Supreme Overlord' of His Apartment",
        "Local Authorities Confused After Every Street in Town Renamed to 'Fredrik Road'",
        "Breaking: Fredrik Discovers New Species of Fish Inside His Own Fridge",
    ]
    return random.choice(headlines)


# 🏆 Fake News Articles
def generate_article():
    prompts = [
        "Write a funny fake news article about Fredrik being announced as the second most fast leveler in World of warcraft",
        "Create a hilarious news report about a secret agent finding  10,000 bottles of baby oil in Fredriks closet.",
        "Generate a satirical article about riots in Sweden because of Fredrik having too much luck on his rolls in wow",
    ]

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "system",
                   "content": "You are a satirical news writer. Roast Fredrik and dont hold back. Keep it in a real news format."},
                  {"role": "user", "content": random.choice(prompts)}]
    )
    return response.choices[0].message.content if response.choices else "Error generating article."


# 🎨 Fake Sponsored Ads
def get_fake_ad():
    ads = [
        "📢 **Try BigRedFred's Leveling Guide!** - *Sign up later, or get clapped*",
        "🍕 **Fredrik’s Pizza Delivery Service** - *We bring you pizza from Rimini.*",
        "📺 **Fredrik TV: All Mobgrinding, All the Time** - *Now streaming @ Behind Dalkiosken!*",
    ]
    return random.choice(ads)


# 🎭 News Ticker at the Top
st.markdown(f"<h2 style='color: white;'>BREAKING: {generate_headline()}</h2>", unsafe_allow_html=True)

# 📰 Generate News Content
col1, col2 = st.columns([2, 1])

with col1:
    st.header("Top Story")
    st.write(generate_article())

with col2:
    st.header("Sponsored")
    st.markdown(
        f"<div style='border: 1px solid black; padding: 10px; background-color: #f9f9f9;'>{get_fake_ad()}</div>",
        unsafe_allow_html=True)

# 🔄 Auto-refreshing Fake Breaking News
if st.button("🔄 Refresh News"):
    st.rerun()

# 🏁 Footer
st.markdown("---")
st.write("© 2025 BIGRED News Network. All Rights Absurd Din Lille Turd.")
