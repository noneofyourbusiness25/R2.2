# Don't Remove Credit @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot @Tech_VJ
# Ask Doubt on telegram @KingVJ01

import re, base64, json, logging
from struct import pack
from pyrogram.file_id import FileId
import motor.motor_asyncio
from pymongo.errors import DuplicateKeyError, BulkWriteError
from info import (
    DATABASE_NAME,
    COLLECTION_NAME,
    FILE_DB_URI,
    SEC_FILE_DB_URI,
    MULTIPLE_DATABASE,
    USE_CAPTION_FILTER,
)

logger = logging.getLogger(__name__)

# Use motor (async) for all database clients
client = motor.motor_asyncio.AsyncIOMotorClient(FILE_DB_URI)
db = client[DATABASE_NAME]
col = db[COLLECTION_NAME]

sec_client = motor.motor_asyncio.AsyncIOMotorClient(SEC_FILE_DB_URI) if MULTIPLE_DATABASE else None
sec_db = sec_client[DATABASE_NAME] if sec_client else None
sec_col = sec_db[COLLECTION_NAME] if sec_db else None

# It's good practice to ensure indexes exist on startup
async def ensure_indexes():
    await col.create_index([('file_name', 'text')])
    if MULTIPLE_DATABASE:
        await sec_col.create_index([('file_name', 'text')])

# Run this once when the module is loaded
import asyncio
asyncio.ensure_future(ensure_indexes())


async def save_files(files):
    """Save multiple files in the database and report duplicates."""
    duplicates = 0
    errors = 0

    documents_to_insert = []
    for file_info in files:
        doc = {
            '_id': file_info['file_id'], # Use file_id as the unique _id
            'file_ref': file_info.get('file_ref'), # Store file_ref separately
            'file_name': file_info['file_name'],
            'file_size': file_info['file_size'],
            'file_type': file_info.get('file_type'),
            'mime_type': file_info.get('mime_type'),
            'caption': file_info['caption']
        }
        documents_to_insert.append(doc)

    if not documents_to_insert:
        return 0, 0, 0

    try:
        result = await col.insert_many(documents_to_insert, ordered=False)
        return len(result.inserted_ids), duplicates, errors
    except BulkWriteError as e:
        successful_inserts = e.details.get('nInserted', 0)
        for error in e.details.get('writeErrors', []):
            if error.get('code') == 11000:  # Code for duplicate key error
                duplicates += 1
            else:
                errors += 1
        return successful_inserts, duplicates, errors
    except Exception as e:
        logger.error(f"General error saving batch: {e}")
        if MULTIPLE_DATABASE:
            try:
                result = await sec_col.insert_many(documents_to_insert, ordered=False)
                return len(result.inserted_ids), 0, 0
            except BulkWriteError as se:
                successful_inserts = se.details.get('nInserted', 0)
                dupes = sum(1 for err in se.details.get('writeErrors', []) if err.get('code') == 11000)
                errs = len(se.details.get('writeErrors', [])) - dupes
                return successful_inserts, dupes, errs
            except Exception as se:
                logger.error(f"Error saving batch to secondary DB: {se}")
        return 0, 0, len(documents_to_insert)

def clean_file_name(file_name):
    file_name = re.sub(r"(_|\-|\.|\+)", " ", str(file_name))
    unwanted_chars = ['[', ']', '(', ')', '{', '}']
    for char in unwanted_chars:
        file_name = file_name.replace(char, '')
    return ' '.join(filter(lambda x: not x.startswith(('@', 'http', 'www.', 't.me')), file_name.split()))

async def get_search_results(chat_id, query, file_type=None, max_results=10, offset=0, filter=False):
    query = query.strip()
    if not query:
        raw_pattern = '.'
    else:
        raw_pattern = query.replace(' ', r'.*[\s\.\+\-_]')
    
    try:
        regex = re.compile(raw_pattern, flags=re.IGNORECASE)
        filter_criteria = {'file_name': regex}
    except re.error:
        filter_criteria = {'file_name': re.escape(query)}

    total_results = await col.count_documents(filter_criteria)
    if MULTIPLE_DATABASE:
        total_results += await sec_col.count_documents(filter_criteria)

    files = []
    cursor = col.find(filter_criteria).sort('$natural', -1).skip(offset).limit(max_results)
    files.extend(await cursor.to_list(length=max_results))

    if MULTIPLE_DATABASE:
        cursor2 = sec_col.find(filter_criteria).sort('$natural', -1).skip(offset).limit(max_results)
        files.extend(await cursor2.to_list(length=max_results))
        
    next_offset = offset + max_results if total_results > offset + max_results else ""
    return files, next_offset, total_results

async def get_bad_files(query, file_type=None, use_filter=False):
    """Restored and corrected function to find files for deletion."""
    query = query.strip()
    if not query:
        raw_pattern = '.'
    else:
        raw_pattern = query.replace(' ', r'.*[\s\.\+\-_]')
    
    try:
        regex = re.compile(raw_pattern, flags=re.IGNORECASE)
        filter_criteria = {'file_name': regex}
    except re.error:
        filter_criteria = {'file_name': re.escape(query)}

    if USE_CAPTION_FILTER:
        filter_criteria = {'$or': [filter_criteria, {'caption': regex}]}

    total_results = await col.count_documents(filter_criteria)
    files = await col.find(filter_criteria).to_list(length=None)

    if MULTIPLE_DATABASE:
        total_results += await sec_col.count_documents(filter_criteria)
        files.extend(await sec_col.find(filter_criteria).to_list(length=None))
        
    return files, total_results

async def get_file_details(query):
    result = await col.find_one({'_id': query})
    if not result and MULTIPLE_DATABASE:
        result = await sec_col.find_one({'_id': query})
    return result

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
    """Return file_id string"""
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
