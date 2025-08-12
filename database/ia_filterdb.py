# Don't Remove Credit @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot @Tech_VJ
# Ask Doubt on telegram @KingVJ01

import re, base64, json
import logging, time
from struct import pack
from pyrogram.file_id import FileId
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError
from info import FILE_DB_URI, SEC_FILE_DB_URI, DATABASE_NAME, COLLECTION_NAME, MULTIPLE_DATABASE, USE_CAPTION_FILTER, MAX_B_TN

logger = logging.getLogger(__name__)

# First Database For File Saving 
client = MongoClient(FILE_DB_URI)
db = client[DATABASE_NAME]
col = db[COLLECTION_NAME]

# Second Database For File Saving
sec_client = MongoClient(SEC_FILE_DB_URI)
sec_db = sec_client[DATABASE_NAME]
sec_col = sec_db[COLLECTION_NAME]


async def save_file(media):
    """Save file in the database."""
    
    file_id = unpack_new_file_id(media.file_id)
    file_name = clean_file_name(media.file_name)
    
    file = {
        'file_id': file_id,
        'file_name': file_name,
        'file_size': media.file_size,
        'caption': media.caption.html if media.caption else None
    }

    if is_file_already_saved(file_id, file_name):
        return False, 0

    try:
        col.insert_one(file)
        print(f"{file_name} is successfully saved.")
        return True, 1
    except DuplicateKeyError:
        print(f"{file_name} is already saved.")
        return False, 0
    except Exception as e:
        logger.exception(f"Primary DB insert failed for file '{file_name}' (id={file_id}). Trying secondary DB if enabled.")
        if MULTIPLE_DATABASE:
            try:
                sec_col.insert_one(file)
                print(f"{file_name} is successfully saved.")
                return True, 1
            except DuplicateKeyError:
                print(f"{file_name} is already saved.")
                return False, 0
            except Exception:
                logger.exception(f"Secondary DB insert failed for file '{file_name}' (id={file_id}).")
                return False, 0
        else:
            print("Your Current File Database Is Full, Turn On Multiple Database Feature And Add Second File Mongodb To Save File.")

def clean_file_name(file_name):
    """Clean and format the file name."""
    file_name = re.sub(r"(_|\-|\.|\+)", " ", str(file_name)) 
    unwanted_chars = ['[', ']', '(', ')', '{', '}']
    
    for char in unwanted_chars:
        file_name = file_name.replace(char, '')
        
    return ' '.join(filter(lambda x: not x.startswith('@') and not x.startswith('http') and not x.startswith('www.') and not x.startswith('t.me'), file_name.split()))

def is_file_already_saved(file_id, file_name):
    """Check if the file is already saved in either collection."""
    found1 = {'file_name': file_name}
    found = {'file_id': file_id}

    for collection in [col, sec_col]:
        if collection.find_one(found1) or collection.find_one(found):
            print(f"{file_name} is already saved.")
            return True
            
    return False

async def get_search_results(chat_id, query, file_type=None, max_results=10, offset=0, filter=False):
    """For given query return (results, next_offset)"""
    
    start_time = time.monotonic()
    logger.info(f"get_search_results called | chat_id={chat_id} | query='{query}' | file_type={file_type} | max_results={max_results} | offset={offset} | MULTIPLE_DATABASE={MULTIPLE_DATABASE}")

    query = query.strip()
    if not query:
        raw_pattern = '.'
    elif ' ' not in query:
        raw_pattern = r'(\b|[\.\+\-_])' + query + r'(\b|[\.\+\-_])'
    else:
        raw_pattern = query.replace(' ', r'.*[\s\.\+\-_]') 
    try:
        regex = re.compile(raw_pattern, flags=re.IGNORECASE)
    except re.error:
        logger.exception(f"Regex compilation failed for raw_pattern='{raw_pattern}' built from query='{query}'. Falling back to plain string search.")
        regex = query
    filter = {'file_name': regex}
    files = []
    fetched_primary = 0
    fetched_secondary = 0
    primary_count = 0
    secondary_count = 0
    error_primary = None
    error_secondary = None
    if MULTIPLE_DATABASE:
        try:
            cursor1 = col.find(filter).sort('$natural', -1).skip(offset).limit(max_results)
            for file in cursor1:
                files.append(file)
                fetched_primary += 1
        except Exception as e:
            error_primary = str(e)
            logger.exception(f"Primary DB find failed | query='{query}' | pattern='{raw_pattern}' | offset={offset} | limit={max_results}")
        try:
            cursor2 = sec_col.find(filter).sort('$natural', -1).skip(offset).limit(max_results)
            for file in cursor2:
                files.append(file)
                fetched_secondary += 1
        except Exception as e:
            error_secondary = str(e)
            logger.exception(f"Secondary DB find failed | query='{query}' | pattern='{raw_pattern}' | offset={offset} | limit={max_results}")
    else:
        try:
            cursor = col.find(filter).sort('$natural', -1).skip(offset).limit(max_results)
            for file in cursor:
                files.append(file)
                fetched_primary += 1
        except Exception:
            error_primary = "primary-only-find-failed"
            logger.exception(f"Primary DB find failed (single DB mode) | query='{query}' | pattern='{raw_pattern}' | offset={offset} | limit={max_results}")

    try:
        primary_count = col.count_documents(filter)
    except Exception:
        primary_count = -1
        logger.exception(f"Primary DB count_documents failed | query='{query}' | pattern='{raw_pattern}'")
    if MULTIPLE_DATABASE:
        try:
            secondary_count = sec_col.count_documents(filter)
        except Exception:
            secondary_count = -1
            logger.exception(f"Secondary DB count_documents failed | query='{query}' | pattern='{raw_pattern}'")
    total_results = primary_count if not MULTIPLE_DATABASE else (max(0, primary_count) + max(0, secondary_count))
    next_offset = "" if (offset + max_results) >= total_results else (offset + max_results)

    duration_ms = int((time.monotonic() - start_time) * 1000)
    logger.info(
        "get_search_results stats | query='%s' | pattern='%s' | total=%s | next_offset=%s | fetched_primary=%s | fetched_secondary=%s | primary_count=%s | secondary_count=%s | errors: primary=%s secondary=%s | duration_ms=%s",
        query,
        raw_pattern,
        total_results,
        next_offset,
        fetched_primary,
        fetched_secondary,
        primary_count,
        secondary_count,
        error_primary,
        error_secondary,
        duration_ms,
    )
    if total_results == 0:
        logger.error(
            "ZERO RESULTS | chat_id=%s | query='%s' | pattern='%s' | offset=%s | limit=%s | MULTIPLE_DATABASE=%s",
            chat_id,
            query,
            raw_pattern,
            offset,
            max_results,
            MULTIPLE_DATABASE,
        )
    return files, next_offset, total_results

async def get_bad_files(query, file_type=None, use_filter=False):
    """For given query return (results, next_offset)"""
    query = query.strip()
    
    if not query:
        raw_pattern = '.'
    elif ' ' not in query:
        raw_pattern = rf'(\b|[.+-_]){query}(\b|[.+-_])'
    else:
        raw_pattern = query.replace(' ', r'.*[s.+-_]')
    
    try:
        regex = re.compile(raw_pattern, flags=re.IGNORECASE)
    except re.error:
        return [], 0

    filter_criteria = {'file_name': regex}
    if USE_CAPTION_FILTER:
        filter_criteria = {'$or': [filter_criteria, {'caption': regex}]}

    def count_documents(collection):
        return collection.count_documents(filter_criteria)

    total_results = (count_documents(col) + count_documents(sec_col) if MULTIPLE_DATABASE else count_documents(col))

    def find_documents(collection):
        return list(collection.find(filter_criteria))

    files = (find_documents(col) + find_documents(sec_col) if MULTIPLE_DATABASE else find_documents(col))

    return files, total_results

async def get_file_details(query):
    return col.find_one({'file_id': query}) or sec_col.find_one({'file_id': query})

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
    
def unpack_new_file_id(new_file_id):
    """Return file_id"""
    decoded = FileId.decode(new_file_id)
    file_id = encode_file_id(
        pack(
            "<iiqq",
            int(decoded.file_type),
            decoded.dc_id,
            decoded.media_id,
            decoded.access_hash
        )
    )
    return file_id
    
