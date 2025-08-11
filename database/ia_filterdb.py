# Don't Remove Credit @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot @Tech_VJ
# Ask Doubt on telegram @KingVJ01

import re, base64, json, logging
from struct import pack
from pyrogram.file_id import FileId
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError, BulkWriteError
from info import FILE_DB_URI, SEC_FILE_DB_URI, DATABASE_NAME, COLLECTION_NAME, MULTIPLE_DATABASE, USE_CAPTION_FILTER

logger = logging.getLogger(__name__)

# Using the synchronous PyMongo driver consistently for stability
client = MongoClient(FILE_DB_URI)
db = client[DATABASE_NAME]
col = db[COLLECTION_NAME]

sec_client = MongoClient(SEC_FILE_DB_URI)
sec_db = sec_client[DATABASE_NAME]
sec_col = sec_db[COLLECTION_NAME]

# Ensure indexes exist for faster queries
col.create_index([('file_name', 'text')])
if MULTIPLE_DATABASE:
    sec_col.create_index([('file_name', 'text')])

async def save_file(media):
    """
    Save a single file in the database.
    This function is required by plugins/channel.py and is now restored.
    """
    file_id = unpack_new_file_id(media.file_id)
    file_name = clean_file_name(media.file_name)
    file = {
        '_id': file_id,
        'file_name': file_name,
        'file_size': media.file_size,
        'caption': media.caption.html if media.caption else None
    }
    try:
        col.insert_one(file)
    except DuplicateKeyError:
        logger.warning(f"Duplicate file (single save): {file_name}")
        return False, 0
    except Exception as e:
        logger.error(f"Error saving single file {file_name}: {e}")
        if MULTIPLE_DATABASE:
            try:
                sec_col.insert_one(file)
            except DuplicateKeyError:
                return False, 0
            except Exception as se:
                logger.error(f"Error saving single file to secondary DB: {se}")
                return False, 2
        else:
            return False, 2
    else:
        return True, 1

async def save_files(files):
    """Save multiple files in the database for batch indexing."""
    documents_to_insert = []
    for file_info in files:
        doc = {
            '_id': file_info['file_id'],
            'file_name': file_info['file_name'],
            'file_size': file_info['file_size'],
            'caption': file_info['caption']
        }
        documents_to_insert.append(doc)

    if not documents_to_insert:
        return 0, 0, 0

    duplicates = 0
    errors = 0
    try:
        result = col.insert_many(documents_to_insert, ordered=False)
        return len(result.inserted_ids), duplicates, errors
    except BulkWriteError as e:
        successful_inserts = e.details.get('nInserted', 0)
        for error in e.details.get('writeErrors', []):
            if error.get('code') == 11000:
                duplicates += 1
            else:
                errors += 1
        return successful_inserts, duplicates, errors
    except Exception as e:
        logger.error(f"General error saving batch: {e}")
        return 0, 0, len(documents_to_insert)

def clean_file_name(file_name):
    file_name = re.sub(r"(_|\-|\.|\+)", " ", str(file_name))
    unwanted_chars = ['[', ']', '(', ')', '{', '}']
    for char in unwanted_chars:
        file_name = file_name.replace(char, '')
    return ' '.join(filter(lambda x: not x.startswith('@'), file_name.split()))

async def get_search_results(chat_id, query, file_type=None, max_results=10, offset=0, filter=False):
    """For given query return (results, next_offset)"""
    query = query.strip()

    # Restored the original, more accurate search logic
    if not query:
        raw_pattern = '.'
    elif ' ' not in query:
        raw_pattern = r'(\b|[\.\+\-_])' + re.escape(query) + r'(\b|[\.\+\-_])'
    else:
        raw_pattern = query.replace(' ', r'.*[\s\.\+\-_]')
    
    try:
        regex = re.compile(raw_pattern, flags=re.IGNORECASE)
    except:
        regex = query
        
    filter_criteria = {'file_name': regex}
    
    # This is the fix for the search crash. It correctly retrieves the list.
    cursor = col.find(filter_criteria).sort('$natural', -1).skip(offset).limit(max_results)
    files = list(cursor) 

    if MULTIPLE_DATABASE:
        cursor2 = sec_col.find(filter_criteria).sort('$natural', -1).skip(offset).limit(max_results)
        files.extend(list(cursor2))

    total_results = col.count_documents(filter_criteria)
    if MULTIPLE_DATABASE:
        total_results += sec_col.count_documents(filter_criteria)
        
    next_offset = offset + max_results if total_results > offset + max_results else ""
    return files, next_offset, total_results

async def get_bad_files(query, file_type=None, use_filter=False):
    """This function is required by other plugins and is now restored."""
    query = query.strip()
    raw_pattern = query.replace(' ', r'.*[s.+-_]')
    try:
        regex = re.compile(raw_pattern, flags=re.IGNORECASE)
    except re.error:
        return [], 0
    
    filter_criteria = {'file_name': regex}
    if USE_CAPTION_FILTER:
        filter_criteria = {'$or': [filter_criteria, {'caption': regex}]}
        
    total_results = col.count_documents(filter_criteria)
    if MULTIPLE_DATABASE:
        total_results += sec_col.count_documents(filter_criteria)
        
    files = list(col.find(filter_criteria))
    if MULTIPLE_DATABASE:
        files.extend(list(sec_col.find(filter_criteria)))
        
    return files, total_results

async def get_file_details(query):
    result = col.find_one({'_id': query})
    if not result and MULTIPLE_DATABASE:
        result = sec_col.find_one({'_id': query})
    return result

def encode_file_id(s: bytes) -> str:
    r = b""
    n = 0
    for i in s + bytes([22]) + bytes([4]):
        if i == 0: n += 1
        else:
            if n: r += b"\x00" + bytes([n]); n = 0
            r += bytes([i])
    return base64.urlsafe_b64encode(r).decode().rstrip("=")

def unpack_new_file_id(new_file_id):
    """Return only the file_id string, which is what the schema expects."""
    decoded = FileId.decode(new_file_id)
    file_id = encode_file_id(
        pack("<iiqq", int(decoded.file_type), decoded.dc_id, decoded.media_id, decoded.access_hash)
    )
    return file_id
