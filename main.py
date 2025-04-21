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

# Load .env file
load_dotenv()

# Initialize app
app = FastAPI()

# CORS settings
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

# Input model
class ASINRequest(BaseModel):
    asins: List[str]

# Endpoint
@app.post("/track_asin")
def track_asins(request: ASINRequest):
    results = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }

    for asin in request.asins:
        try:
            url = f"https://www.amazon.in/dp/{asin}"
            print(f"🔍 Fetching: {url}")
            response = requests.get(url, headers=headers)
            soup = BeautifulSoup(response.text, "html.parser")

            title = soup.find(id="productTitle")
            price = soup.find("span", class_="a-price-whole")
            rating = soup.find("span", class_="a-icon-alt")
            reviews = soup.find(id="acrCustomerReviewText")

            data = {
                "asin": asin,
                "title": title.get_text(strip=True) if title else "N/A",
                "price": price.get_text(strip=True) if price else "N/A",
                "rating": rating.get_text(strip=True) if rating else "N/A",
                "reviews": reviews.get_text(strip=True) if reviews else "N/A",
                "timestamp": datetime.now()
            }

            inserted = collection.insert_one(data)
            data["_id"] = str(inserted.inserted_id)
            results.append(data)

            print(f"✅ Scraped: {data['title']} | ₹{data['price']} | {data['rating']} | {data['reviews']}")

        except Exception as e:
            print(f"❌ Error processing {asin}:", e)
            raise HTTPException(status_code=500, detail=str(e))

    return results
