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
    """Saves a completed research session to MongoDB using the strict schema required by the UI."""
    try:
        collection = _get_collection()
        doc = {
            "task_id": task_id,
            "query": user_request,          # Fixed key
            "sub_topics": sub_topics,
            "report": final_report,         # Fixed key
            "latency": latency_seconds,     # Fixed key
            "timestamp": datetime.datetime.now(datetime.timezone.utc)
        }
        result = collection.insert_one(doc)
        return str(result.inserted_id)
    except Exception as e:
        print(f"[!] MongoDB Save Failed: {e}")
        return None

def fetch_recent_history(limit: int = 20) -> list:
    """Retrieves recent research records, strictly filtering out broken or empty data."""
    try:
        collection = _get_collection()
        
        # Explicit filter to drop the "Unknown Query" garbage
        query_filter = {
            "query": {"$exists": True, "$ne": None, "$ne": ""},
            "report": {"$exists": True, "$ne": None, "$ne": ""}
        }
        
        # Fetch, sort by newest, and apply the filter
        cursor = collection.find(query_filter).sort("_id", -1).limit(limit)
        
        history_list = []
        for doc in cursor:
            history_list.append({
                "id": doc.get("task_id", str(doc.get("_id"))),
                "query": doc.get("query"),
                "report": doc.get("report"),
                "latency": doc.get("latency", 0.0),
                "saved_id": str(doc.get("_id"))
            })
        return history_list
        
    except Exception as e:
        print(f"[!] MongoDB Fetch Failed: {e}")
        return []