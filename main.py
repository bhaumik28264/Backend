from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import os
import pymongo
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MongoDB connection
MONGO_URI = os.getenv("MONGO_URI")
if not MONGO_URI:
    raise RuntimeError("❌ MONGO_URI not found in environment variables!")

client = pymongo.MongoClient(MONGO_URI)
db = client["amazon_tracker"]
collection = db["asin_data"]

# Request schema
class ASINRequest(BaseModel):
    asins: List[str]

@app.post("/track_asin")
def track_asins(request: ASINRequest):
    print("➡️ Received ASINs:", request.asins)
    results = []

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }

    for asin in request.asins:
        try:
            url = f"https://www.amazon.in/dp/{asin}"
            print("🔍 Fetching:", url)
            response = requests.get(url, headers=headers)

            if response.status_code != 200:
                raise Exception(f"Amazon returned status code {response.status_code}")

            soup = BeautifulSoup(response.content, "html.parser")

            title = soup.find(id="productTitle")
            price = soup.find("span", class_="a-price-whole")
            rating = soup.find("span", class_="a-icon-alt")
            reviews = soup.find(id="acrCustomerReviewText")

            if not title:
                raise Exception("🔴 Product title not found (maybe blocked or bad ASIN)")

            data = {
                "asin": asin,
                "title": title.get_text(strip=True) if title else "N/A",
                "price": price.get_text(strip=True) if price else "N/A",
                "rating": rating.get_text(strip=True) if rating else "N/A",
                "reviews": reviews.get_text(strip=True) if reviews else "N/A",
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }

            collection.insert_one(data)
            results.append(data)
            print("✅ Scraped:", data["title"])

        except Exception as e:
            print(f"❌ Error processing {asin}:", e)
            raise HTTPException(status_code=500, detail=str(e))

    return results
