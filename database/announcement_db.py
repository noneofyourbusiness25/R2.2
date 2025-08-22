import pymongo
from info import DATABASE_URI, DATABASE_NAME
import time

# Connect to MongoDB
client = pymongo.MongoClient(DATABASE_URI)
db = client[DATABASE_NAME]
collection = db["announcement_settings"]
queue_collection = db["announcement_queue"]

def set_announcement_channel(channel_id):
    """Sets the announcement channel ID."""
    collection.update_one(
        {"_id": "announcement_settings"},
        {"$set": {"channel_id": channel_id}},
        upsert=True
    )

def get_announcement_channel():
    """Gets the announcement channel ID."""
    settings = collection.find_one({"_id": "announcement_settings"})
    return settings.get("channel_id") if settings else None

def announcement_on():
    """Turns on the announcement feature."""
    collection.update_one(
        {"_id": "announcement_settings"},
        {"$set": {"enabled": True}},
        upsert=True
    )

def announcement_off():
    """Turns off the announcement feature."""
    collection.update_one(
        {"_id": "announcement_settings"},
        {"$set": {"enabled": False}},
        upsert=True
    )

def get_announcement_status():
    """Gets the announcement status."""
    settings = collection.find_one({"_id": "announcement_settings"})
    return settings.get("enabled", False) if settings else False

def add_to_announcement_queue(file_name):
    """Adds a file name to the announcement queue."""
    queue_collection.insert_one({
        "file_name": file_name,
        "timestamp": time.time()
    })

def get_announcement_queue(limit=10):
    """Gets file names from the announcement queue."""
    return list(queue_collection.find().sort("timestamp", 1).limit(limit))

def clear_announcement_queue(item_ids):
    """Clears items from the announcement queue by their IDs."""
    if item_ids:
        queue_collection.delete_many({"_id": {"$in": item_ids}})
