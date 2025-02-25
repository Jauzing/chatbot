import streamlit as st
import random
import time
from openai import OpenAI
from datetime import datetime
import requests

# 🚀 Title and Description
st.set_page_config(page_title="Fredrik News Network", layout="wide")
st.title("📰 Fredrik News Network (FNN)")
st.write("Bringing you breaking news about Fredrik, 24/7.")

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
        "Write a funny fake news article about Fredrik discovering a secret government conspiracy in his sock drawer.",
        "Create a hilarious news report about Fredrik accidentally buying 10,000 rubber ducks online.",
        "Generate a satirical article about Fredrik being elected mayor due to a typo in the voting system.",
    ]

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "system",
                   "content": "You are a satirical news writer. Make it funny, but keep it in a real news format."},
                  {"role": "user", "content": random.choice(prompts)}]
    )
    return response.choices[0].message.content if response.choices else "Error generating article."


# 🎨 Fake Sponsored Ads
def get_fake_ad():
    ads = [
        "📢 **Try Fredrik's Masterclass on Procrastination!** - *Sign up later, or maybe never.*",
        "🍕 **Fredrik’s Pizza Delivery Service** - *We bring you pizza, eventually.*",
        "📺 **Fredrik TV: All Fredrik, All the Time** - *Now streaming 24/7!*",
    ]
    return random.choice(ads)


# 🎭 News Ticker at the Top
st.markdown(f"<h2 style='color: red;'>BREAKING: {generate_headline()}</h2>", unsafe_allow_html=True)

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
st.write("© 2025 Fredrik News Network. All Rights Absurd.")
