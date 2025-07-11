
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import IndexModel, UpdateOne
from datetime import datetime
from dotenv import load_dotenv
from typing import List, Dict, Any
import os

# Local import — your scraper must return a list of dicts with at least 'title' and either 'url' or 'link'
from scrap import scrape_all_sources

load_dotenv()

app = FastAPI()

MONGODB_URL    = os.getenv("MONGODB_URL", "mongodb+srv://cybernews:12121212@cluster0.zn1gohj.mongodb.net/")
DB_NAME        = os.getenv("DB_NAME",    "cybernews")
COLLECTION     = "cybernews"

# CORS for your React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite (if you're using Vite)
        "https://cybernews-frontend-zrvs-cqfxrphh1-aryaman170s-projects.vercel.app",
        "http://localhost:3000",  # Create React App
        "http://localhost:8080"   # Your current frontend port
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_db_client():
    app.mongodb_client    = AsyncIOMotorClient(MONGODB_URL)
    app.mongodb           = app.mongodb_client[DB_NAME]
    app.article_collection = app.mongodb[COLLECTION]
    # Create the indexes only once
    await app.article_collection.create_indexes([
        IndexModel([("url", 1)], unique=True),
        IndexModel([("date", -1)]),
        IndexModel([("source", 1)])
    ])

@app.on_event("shutdown")
async def shutdown_db_client():
    app.mongodb_client.close()

async def store_articles(articles: List[Dict[str, Any]]):
    if not articles:
        return

    now = datetime.utcnow()
    ops: List[UpdateOne] = []

    for art in articles:
        # normalize URL field
        url = art.get("url") or art.get("link")
        if not url:
            print("⚠️ Skipping article — no URL/link:", art)
            continue

        art["url"] = url
        art["_id"] = url              # use URL as MongoDB _id
        art["last_updated"] = now
        if "date" not in art or not art["date"]:
            art["date"] = now

        # remove 'link' if present
        if "link" in art:
            del art["link"]

        # prepare an UpdateOne upsert
        ops.append(
            UpdateOne(
                {"_id": url},
                {"$set": art},
                upsert=True
            )
        )

    if not ops:
        print("⚠️ No valid articles to upsert.")
        return

    try:
        result = await app.article_collection.bulk_write(ops)
        print(f"✅ bulk_write upserted: {result.upserted_count}, modified: {result.modified_count}")
    except Exception as e:
        print("❌ MongoDB bulk_write error:", e)
        raise

@app.get("/")
def root():
    return {"message": "Welcome to Cybernews API — use /api/news"}
@app.get("/api/db-news")
async def get_news_from_db():
    try:
        db_articles = await app.article_collection.find().sort("date", -1).to_list(length=100)
        for article in db_articles:
            article["id"] = article.pop("_id", None)
        return {"articles": db_articles}
    except Exception as e:
        print("❌ ERROR:", str(e))
        raise HTTPException(status_code=500, detail="Failed to fetch from DB")

@app.get("/api/news")
async def get_all_news():
    try:
        print("🔄 Scraping…")
        articles = scrape_all_sources()
        print(f"✅ Scraped {len(articles)} articles")

        await store_articles(articles)

        # fetch back sorted
        db_articles = await app.article_collection.find().sort("date", -1).to_list(length=100)
        for doc in db_articles:
            doc["id"] = str(doc.pop("_id"))
        return {"articles": db_articles}

    except Exception as e:
        print("❌ ERROR in /api/news:", e)
        raise HTTPException(status_code=500, detail=str(e))

