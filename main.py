import streamlit as st
import requests
from bs4 import BeautifulSoup
from pymongo import MongoClient
import openai

# MongoDB Atlas connection string
mongo_uri = st.secrets["MONGODB_URI"]

# Connect to MongoDB Atlas
client = MongoClient(mongo_uri)

# Select the database and collection
db = client['chess']
collection = db['stats']

# Function to scrape data and store it in MongoDB
def scrape_and_store_data():
    urls = [
        "https://www.chessgames.com/chessstats.html",
        "https://www.chess.com/stats",
        "https://www.fide.com/official-partners/our-partners.html"
    ]
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
    }
    for url in urls:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            page_text = soup.get_text(separator='\n', strip=True)
            document = {
                "url": url,
                "content": page_text
            }
            collection.insert_one(document)
            st.success(f"Data has been successfully scraped and stored in MongoDB from {url}.")
        else:
            st.error(f"Failed to retrieve the webpage at {url}. Status code: {response.status_code}")

# Function to structure and clean up the content
def structure_content(content):
    # Placeholder implementation; adapt based on actual content
    structured_data = {
        "players": []
    }
    lines = content.splitlines()
    for line in lines:
        if "player" in line.lower() and "wins:" in line.lower():
            parts = line.split()
            player_name = parts[0]
            wins = int(parts[parts.index("wins:") + 1])
            structured_data["players"].append({"name": player_name, "wins": wins})
    return structured_data

# Function to get data from MongoDB and use LLM for analysis
def analyze_data(prompt):
    # Retrieve the latest document from the MongoDB collection
    document = collection.find_one(sort=[('_id', -1)])
    if document:
        content = document['content']
        structured_data = structure_content(content)
        # Format the query for the LLM based on the prompt and the structured data
        if "highest number of winnings" in prompt.lower() or "lowest number of winnings" in prompt.lower():
            if structured_data["players"]:
                player_stats = structured_data["players"]
                max_wins_player = max(player_stats, key=lambda x: x['wins'])
                min_wins_player = min(player_stats, key=lambda x: x['wins'])
                return f"The player with the highest number of winnings is {max_wins_player['name']} with {max_wins_player['wins']} wins.\n" \
                       f"The player with the lowest number of winnings is {min_wins_player['name']} with {min_wins_player['wins']} wins."
            else:
                return "Player win data is not available in the current content."
        else:
            # Use OpenAI API to analyze the data based on the user's prompt
            openai.api_key = st.secrets["OPENAI_API_KEY"]
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",  # or gpt-4, depending on your use case
                messages=[
                    {"role": "user", "content": f"{prompt}\n\nContent:\n{content}"}
                ],
                max_tokens=150
            )
            return response.choices[0].message['content'].strip()
    else:
        st.error("No data found in the MongoDB collection.")
        return None

# Streamlit UI
st.title("Chess Stats Analyzer")
st.write("This app scrapes chess stats from the web, stores it in MongoDB, and allows you to analyze it using an LLM.")

# Scrape data button
if st.button("Scrape and Store Data"):
    scrape_and_store_data()

# LLM prompt input
user_prompt = st.text_input("Enter your prompt for the LLM:")
if st.button("Analyze Data") and user_prompt:
    result = analyze_data(user_prompt)
    if result:
        st.write("Analysis Result:")
        st.write(result)
