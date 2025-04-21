
from fastapi import FastAPI, HTTPException
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
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],

client = pymongo.MongoClient(os.getenv("MONGO_URI"))
db = client["amazon_tracker"]
collection = db["asin_data"]

class ASINRequest(BaseModel):
    asins: List[str]

@app.post("/track_asin")
def track_asins(request: ASINRequest):
    results = []
    for asin in request.asins:
        url = f"https://www.amazon.in/dp/{asin}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.93 Safari/537.36"
        }
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            continue

        soup = BeautifulSoup(response.content, "html.parser")

        try:
            title = soup.find(id="productTitle").get_text().strip()
            price_tag = soup.select_one(".a-price .a-offscreen")
            price = price_tag.get_text().strip() if price_tag else "N/A"
            rating_tag = soup.select_one("span.a-icon-alt")
            rating = rating_tag.get_text().strip() if rating_tag else "N/A"
            review_count_tag = soup.select_one("#acrCustomerReviewText")
            reviews = review_count_tag.get_text().strip() if review_count_tag else "N/A"

            data = {
                "asin": asin,
                "title": title,
                "price": price,
                "rating": rating,
                "reviews": reviews,
                "timestamp": datetime.utcnow()
            }

            collection.insert_one(data)
            results.append(data)

        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    return {"status": "success", "tracked": results}

@app.get("/get_data/{asin}")
def get_asin_data(asin: str):
    data = list(collection.find({"asin": asin}, {"_id": 0}))
    if not data:
        raise HTTPException(status_code=404, detail="No data found for this ASIN")
    return data
