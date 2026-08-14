import os
import datetime
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
DB_NAME = os.getenv("MONGO_DB_NAME", "deep_research_db")
COLLECTION_NAME = "research_history"

def _get_collection():
    """Establishes MongoDB connection and returns the target collection."""
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=3000)
    db = client[DB_NAME]
    return db[COLLECTION_NAME]

def save_research_run(user_request: str, sub_topics: list, final_report: str, task_id: str, latency_seconds: float = None) -> str:
    """Saves a completed research session to MongoDB including execution latency."""
    try:
        collection = _get_collection()
        doc = {
            "task_id": task_id,
            "user_request": user_request,
            "sub_topics": sub_topics,
            "final_report": final_report,
            "latency_seconds": latency_seconds,
            "timestamp": datetime.datetime.now(datetime.timezone.utc)
        }
        result = collection.insert_one(doc)
        return str(result.inserted_id)
    except Exception as e:
        print(f"[!] MongoDB Save Failed: {e}")
        return None

def fetch_recent_history(limit: int = 5) -> list:
    """Retrieves recent research records sorted by timestamp descending."""
    try:
        collection = _get_collection()
        records = list(collection.find({}, {"_id": 0}).sort("timestamp", -1).limit(limit))
        return records
    except Exception as e:
        print(f"[!] MongoDB Fetch Failed: {e}")
        return []