import pymongo
from info import DATABASE_URI, DATABASE_NAME

# Connect to MongoDB
client = pymongo.MongoClient(DATABASE_URI)
db = client[DATABASE_NAME]
collection = db["backup_settings"]

def set_backup_channel(channel_id):
    """Sets the backup channel ID."""
    collection.update_one(
        {"_id": "backup_settings"},
        {"$set": {"channel_id": channel_id}},
        upsert=True
    )

def get_backup_channel():
    """Gets the backup channel ID."""
    settings = collection.find_one({"_id": "backup_settings"})
    return settings.get("channel_id") if settings else None

def backup_on():
    """Turns on automatic backup."""
    collection.update_one(
        {"_id": "backup_settings"},
        {"$set": {"enabled": True}},
        upsert=True
    )

def backup_off():
    """Turns off automatic backup."""
    collection.update_one(
        {"_id": "backup_settings"},
        {"$set": {"enabled": False}},
        upsert=True
    )

def get_backup_status():
    """Gets the backup status."""
    settings = collection.find_one({"_id": "backup_settings"})
    if settings:
        return settings.get("enabled", False), settings.get("channel_id")
    return False, None

def update_last_backed_up_file(file_id):
    """Updates the last backed up file ID."""
    collection.update_one(
        {"_id": "backup_settings"},
        {"$set": {"last_backed_up": file_id}},
        upsert=True
    )

def get_last_backed_up_file():
    """Gets the last backed up file ID."""
    settings = collection.find_one({"_id": "backup_settings"})
    return settings.get("last_backed_up") if settings else None

def pause_backup():
    """Pauses the backup process."""
    collection.update_one(
        {"_id": "backup_settings"},
        {"$set": {"paused": True}},
        upsert=True
    )

def resume_backup():
    """Resumes the backup process."""
    collection.update_one(
        {"_id": "backup_settings"},
        {"$set": {"paused": False}},
        upsert=True
    )

def is_backup_paused():
    """Checks if the backup process is paused."""
    settings = collection.find_one({"_id": "backup_settings"})
    return settings.get("paused", False) if settings else False
