from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
from datetime import datetime
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import requests
import os
import pymongo
from bson import ObjectId

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI()

# Allow all origins (for testing/deployment purposes)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MongoDB connection
client = pymongo.MongoClient(os.getenv("MONGO_URI"))
db = client["amazon_tracker"]
collection = db["asin_data"]

# Request body model
class ASINRequest(BaseModel):
    asins: List[str]

# Scrape function
def scrape_amazon_title(asin: str) -> str:
    url = f"https://www.amazon.in/dp/{asin}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")
    title = soup.find(id="productTitle")
    return title.text.strip() if title else "N/A"

# API endpoint
@app.post("/track_asin")
def track_asins(request: ASINRequest):
    results = []
    for asin in request.asins:
        print(f"🔍 Fetching: https://www.amazon.in/dp/{asin}")
        title = scrape_amazon_title(asin)
        print(f"✅ Scraped: {title}")
        data = {
            "asin": asin,
            "title": title,
            "timestamp": datetime.now()
        }
        inserted = collection.insert_one(data)
        data["_id"] = str(inserted.inserted_id)  # Fix: Convert ObjectId to string
        results.append(data)
    return results
