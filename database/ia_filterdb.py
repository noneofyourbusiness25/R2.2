# Don't Remove Credit @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot @Tech_VJ
# Ask Doubt on telegram @KingVJ01

import re, base64, json
import logging, time
from struct import pack
from pyrogram.file_id import FileId
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError, BulkWriteError
from info import FILE_DB_URI, SEC_FILE_DB_URI, DATABASE_NAME, COLLECTION_NAME, MULTIPLE_DATABASE

logger = logging.getLogger(__name__)

# Databases
client = MongoClient(FILE_DB_URI)
db = client[DATABASE_NAME]
col = db[COLLECTION_NAME]

sec_client = MongoClient(SEC_FILE_DB_URI)
sec_db = sec_client[DATABASE_NAME]
sec_col = sec_db[COLLECTION_NAME]


async def save_file(media):
    file_id, file_ref = unpack_new_file_id(media.file_id)
    file_name = ' '.join(media.file_name.split()) if media.file_name else ''
    caption = ' '.join(media.caption.html.split()) if media.caption and media.caption.html else ''

    file = {
        '_id': file_id, 'file_ref': file_ref, 'file_name': file_name,
        'file_size': media.file_size, 'file_type': media.file_type,
        'mime_type': media.mime_type, 'caption': caption
    }

    try:
        col.insert_one(file)
    except DuplicateKeyError:
        logger.warning(f"{file_name} is already saved.")
        return False, 0
    except Exception as e:
        logger.error(f"Error saving file {file_name}: {e}")
        if MULTIPLE_DATABASE:
            try:
                sec_col.insert_one(file)
            except Exception as e:
                logger.error(f"Secondary DB Error saving file {file_name}: {e}")
                return False, 0
        else:
            return False, 0
    return True, 1

async def save_files(files):
    """Save multiple files in the database."""
    try:
        result = col.insert_many(files, ordered=False)
        return len(result.inserted_ids), 0
    except BulkWriteError as e:
        # Count duplicates and other errors
        duplicates = sum(1 for error in e.details['writeErrors'] if error['code'] == 11000)
        return e.details['nInserted'], duplicates
    except Exception as e:
        logger.exception(f"Primary DB bulk insert failed. Trying secondary DB if enabled.")
        if MULTIPLE_DATABASE:
            try:
                result = sec_col.insert_many(files, ordered=False)
                return len(result.inserted_ids), 0
            except BulkWriteError as e:
                duplicates = sum(1 for error in e.details['writeErrors'] if error['code'] == 11000)
                return e.details['nInserted'], duplicates
            except Exception:
                logger.exception(f"Secondary DB bulk insert failed.")
                return 0, len(files)
        else:
            print("Your Current File Database Is Full, Turn On Multiple Database Feature And Add Second File Mongodb To Save File.")
            return 0, len(files)

def clean_file_name(file_name):
    """Clean and format the file name."""
    if not file_name:
        return ""
    # A basic cleaning to remove unwanted characters and spaces
    return ' '.join(re.sub(r'[\W_]+', ' ', file_name).split())

def is_file_already_saved(file_id):
    """Check if the file is already saved in either collection."""
    found = {'_id': file_id}
    if col.find_one(found) or sec_col.find_one(found):
        return True
    return False

async def get_search_results(query, max_results=300):
    """
    Performs a simple, fast initial search in the database.
    This fetches a batch of candidate files for further processing.
    """
    query_parts = query.strip().split()
    if not query_parts:
        return [], 0

    # Build a query that requires all parts to be present
    # This is more efficient than a single complex regex
    filter_clauses = [
        {'$or': [{'file_name': re.compile(part, re.IGNORECASE)}, {'caption': re.compile(part, re.IGNORECASE)}]}
        for part in query_parts
    ]
    filter_criteria = {'$and': filter_clauses} if len(filter_clauses) > 1 else filter_clauses[0]

    try:
        total_results = col.count_documents(filter_criteria)
        if MULTIPLE_DATABASE:
            total_results += sec_col.count_documents(filter_criteria)

        # Fetch from primary DB
        files = list(col.find(filter_criteria).limit(max_results))

        # Fetch from secondary DB if needed
        if MULTIPLE_DATABASE and len(files) < max_results:
            remaining_limit = max_results - len(files)
            files.extend(list(sec_col.find(filter_criteria).limit(remaining_limit)))

        return files, total_results
    except Exception as e:
        logger.exception(f"Database search failed for query '{query}': {e}")
        return [], 0

async def get_file_details(query):
    return col.find_one({'_id': query}) or sec_col.find_one({'_id': query})

def unpack_new_file_id(new_file_id):
    decoded = FileId.decode(new_file_id)
    file_id = encode_file_id(
        pack("<iiqq", int(decoded.file_type), decoded.dc_id, decoded.media_id, decoded.access_hash)
    )
    return file_id, decoded.file_reference

def encode_file_id(s: bytes) -> str:
    r = b""
    n = 0
    for i in s + bytes([22]) + bytes([4]):
        if i == 0:
            n += 1
        else:
            if n:
                r += b"\x00" + bytes([n])
                n = 0
            r += bytes([i])
    return base64.urlsafe_b64encode(r).decode().rstrip("=")
