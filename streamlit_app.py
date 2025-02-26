import streamlit as st
import random
import json
import time
from openai import OpenAI
from datetime import datetime, timedelta
import os

# 🚀 Title and Description
st.set_page_config(page_title="Fredrik News Network", layout="wide")
st.title("📰 BIGRED News Network (BNN)")
st.write("Bringing you swell news about Fredrik, all day err' day.")

# OpenAI API Key
openai_api_key = st.secrets.get("OPENAI_API_KEY")
client = OpenAI(api_key=openai_api_key)

# 🕒 Cache File for News
CACHE_FILE = "news_cache.json"
CACHE_EXPIRY_HOURS = 5  # Refresh news every 5 hours


# 📰 Fake Breaking News Headlines
def generate_headline():
    headlines = [
        "Fredrik Accidentally Invents a way to play wow while sleeping",
        "Study Shows 98% of Fredriks brain filled with fog",
        "Fredrik Declares Himself 'Supreme Overlord' of Dalkiosken",
        "Local Authorities Confused After Fredrik found  a way into the evidence room",
        "Breaking: Fredrik Discovers New Species of roach behind dalkiosken",
    ]
    return random.choice(headlines)


# 🏆 Fake News Articles & DALL-E Image Generation
def generate_article_and_image(prompt):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system",
             "content": "You are a satirical news writer. Roast Fredrik and don't hold back. Keep it in a real news format."},
            {"role": "user", "content": prompt}
        ]
    )
    article = response.choices[0].message.content if response.choices else "Error generating article."

    # 🎨 Generate an image for the article
    dalle_response = client.images.generate(
        model="dall-e-3",
        prompt=f"A hilarious satirical news image illustrating: {prompt}. Keep in mind Fredrik has the following characteristics: Swedish, Ginger/Red hair, tall, bald, beard, likes hiphop and wears loose streetstyle clothing.",
        size="1024x1024"
    )

    image_url = dalle_response.data[0].url if dalle_response else None
    return article, image_url


# 🎭 Fake Sponsored Ads
def get_fake_ad():
    ads = [
        "📢 **Try BigRedFred's Leveling Guide!** - *Sign up later, or get clapped*",
        "🍕 **Fredrik’s Pizza Delivery Service** - *We bring you pizza from Rimini.*",
        "📺 **Fredrik TV: All Mobgrinding, All the Time** - *Now streaming @ Behind Dalkiosken!*",
    ]
    return random.choice(ads)


# 🕒 Load Cached News if Fresh, Else Generate New
def load_or_generate_news():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r") as file:
            data = json.load(file)
            last_updated = datetime.strptime(data["last_updated"], "%Y-%m-%d %H:%M:%S")

            # If cache is still fresh, return it
            if datetime.now() - last_updated < timedelta(hours=CACHE_EXPIRY_HOURS):
                return data["headline"], data["top_articles"], data["other_articles"]

    # Otherwise, generate fresh news
    prompts = [
        "Write a funny fake news article about Fredrik being announced as the second most fast leveler in World of Warcraft.",
        "Create a hilarious news report about a secret agent finding 10,000 bottles of baby oil in Fredrik's closet.",
        "Generate a satirical article about riots in Sweden because of Fredrik having too much luck on his rolls in WoW.",
        "Write a satirical piece about Fredrik not being able to drift in Flatout 2 the racing game.",
        "Generate a comically absurd story about Fredrik throwing water baloons on Aveliners house."
    ]

    # Select 3-5 random articles
    num_articles = random.randint(3, 5)
    selected_prompts = random.sample(prompts, num_articles)

    # Generate new articles & images
    top_articles = [generate_article_and_image(selected_prompts[i]) for i in range(2)]
    other_articles = [generate_article_and_image(selected_prompts[i])[0] for i in range(2, num_articles)]

    # New headline
    new_headline = generate_headline()

    # Cache the new data
    data = {
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "headline": new_headline,
        "top_articles": top_articles,
        "other_articles": other_articles
    }

    with open(CACHE_FILE, "w") as file:
        json.dump(data, file)

    return new_headline, top_articles, other_articles


# 🕒 Session State for Auto Refresh
if "last_refresh_time" not in st.session_state:
    st.session_state["last_refresh_time"] = datetime.now()

# Refresh every 5 hours
if datetime.now() - st.session_state["last_refresh_time"] > timedelta(hours=CACHE_EXPIRY_HOURS):
    st.session_state["last_refresh_time"] = datetime.now()
    st.rerun()

# 📌 Load News Content
headline, top_articles, other_articles = load_or_generate_news()

# 🎭 News Ticker at the Top
st.markdown(f"<h2 style='color: white;'>BREAKING: {headline}</h2>", unsafe_allow_html=True)

# 📌 Layout Setup
col1, col2 = st.columns([3, 1])

with col1:
    st.header("📰 Top Stories")

    for i, (article, image_url) in enumerate(top_articles):
        with st.container():
            st.subheader(f"🔹 Story {i + 1}")
            if image_url:
                st.image(image_url, use_container_width=True)
            st.write(article)

    st.header("📢 Other News")

    for article in other_articles:
        with st.container():
            st.write(article)

with col2:
    st.header("🎯 Sponsored Content")
    st.markdown(
        f"<div style='border: 1px solid black; padding: 10px; background-color: #f9f9f9;'>{get_fake_ad()}</div>",
        unsafe_allow_html=True
    )

# 🔄 Auto-refreshing Fake Breaking News
if st.button("🔄 Refresh News"):
    st.session_state["last_refresh_time"] = datetime.now()
    st.rerun()

# 🏁 Footer
st.markdown("---")
st.write("© 2025 BIGRED News Network. All Rights Absurd Din Lille Turd.")

# 🕒 Auto-Refresh the Page Every 5 Hours
st.markdown(
    """
    <script>
    function autoRefresh() {
        setTimeout(function() { location.reload(); }, 18000000);
    }
    autoRefresh();
    </script>
    """,
    unsafe_allow_html=True
)
