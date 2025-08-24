# Don't Remove Credit @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot @Tech_VJ
# Ask Doubt on telegram @KingVJ01

import re, base64, json
import logging, time
from struct import pack
from pyrogram.file_id import FileId
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError, BulkWriteError
from info import FILE_DB_URI, SEC_FILE_DB_URI, DATABASE_NAME, COLLECTION_NAME, MULTIPLE_DATABASE, USE_CAPTION_FILTER, MAX_B_TN
from database.backup_db import get_backup_status
import asyncio

logger = logging.getLogger(__name__)

# First Database For File Saving
client = MongoClient(FILE_DB_URI)
db = client[DATABASE_NAME]
col = db[COLLECTION_NAME]

# Second Database For File Saving
sec_client = MongoClient(SEC_FILE_DB_URI)
sec_db = sec_client[DATABASE_NAME]
sec_col = sec_db[COLLECTION_NAME]


def create_text_index():
    """Create a text index on file_name and caption fields for faster searches."""
    # Check if the index already exists for the primary collection
    existing_indexes = col.index_information()
    if 'file_name_text_caption_text' not in existing_indexes:
        try:
            # Create a text index on both 'file_name' and 'caption'
            col.create_index([('file_name', 'text'), ('caption', 'text')], name='file_name_text_caption_text')
            logger.info("Text index created successfully for the primary collection.")
        except Exception as e:
            logger.error(f"Failed to create text index for primary collection: {e}")
    else:
        logger.info("Text index already exists for the primary collection.")

    # Do the same for the secondary collection if it's enabled
    if MULTIPLE_DATABASE:
        existing_indexes_sec = sec_col.index_information()
        if 'file_name_text_caption_text' not in existing_indexes_sec:
            try:
                sec_col.create_index([('file_name', 'text'), ('caption', 'text')], name='file_name_text_caption_text')
                logger.info("Text index created successfully for the secondary collection.")
            except Exception as e:
                logger.error(f"Failed to create text index for secondary collection: {e}")
        else:
            logger.info("Text index already exists for the secondary collection.")


async def save_file(media):
    """Save file in the database."""

    file_id, file_ref = unpack_new_file_id(media.file_id)
    file_name = clean_file_name(media.file_name)

    file = {
        '_id': file_id,
        'file_ref': file_ref,
        'file_name': file_name,
        'file_size': media.file_size,
        'file_type': media.file_type,
        'mime_type': media.mime_type,
        'caption': clean_file_name(media.caption.html) if media.caption else None,
        'file_id': file_id
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
            return False, 0

async def save_files(files):
    """Save multiple files in the database and backup if enabled."""
    saved_files = []
    try:
        result = col.insert_many(files, ordered=False)
        inserted_ids = result.inserted_ids
        saved_files = [f for f in files if f['_id'] in inserted_ids]
    except BulkWriteError as e:
        inserted_ids = [item['_id'] for item in files if item['_id'] not in [err['op']['_id'] for err in e.details['writeErrors']]]
        saved_files = [f for f in files if f['_id'] in inserted_ids]
    except Exception:
        logger.exception(f"Primary DB bulk insert failed. Trying secondary DB if enabled.")
        if MULTIPLE_DATABASE:
            try:
                result = sec_col.insert_many(files, ordered=False)
                inserted_ids = result.inserted_ids
                saved_files = [f for f in files if f['_id'] in inserted_ids]
            except BulkWriteError as e:
                inserted_ids = [item['_id'] for item in files if item['_id'] not in [err['op']['_id'] for err in e.details['writeErrors']]]
                saved_files = [f for f in files if f['_id'] in inserted_ids]
            except Exception:
                logger.exception(f"Secondary DB bulk insert failed.")
                return [], len(files)
        else:
            print("Your Current File Database Is Full, Turn On Multiple Database Feature And Add Second File Mongodb To Save File.")
            return [], len(files)

    # Automatic backup
    enabled, backup_channel = get_backup_status()
    if enabled and backup_channel and saved_files:
        from bot import Client
        for file in saved_files:
            try:
                await Client.send_document(
                    chat_id=backup_channel,
                    document=file["file_id"],
                    caption=file.get("caption", "")
                )
                await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"Failed to backup file {file['_id']}: {e}")

    return saved_files, len(files) - len(saved_files)

def clean_file_name(file_name):
    """Clean and format the file name."""
    if not file_name:
        return ""
    file_name = re.sub(r'[\W_]+', ' ', str(file_name))

    return ' '.join(filter(lambda x: not x.startswith('@') and not x.startswith('http') and not x.startswith('www.') and not x.startswith('t.me'), file_name.split()))

def is_file_already_saved(file_id, file_name):
    """Check if the file is already saved in either collection."""
    found = {'_id': file_id}

    for collection in [col, sec_col]:
        if collection.find_one(found):
            print(f"{file_name} is already saved.")
            return True

    return False

LANGUAGES = {
    "hindi": ["hindi", "hin"],
    "english": ["english", "eng"],
    "tamil": ["tamil", "tam"],
    "telugu": ["telugu", "tel"],
    "malayalam": ["malayalam", "mala", "mal"],
    "kannada": ["kannada", "kan"],
    "japanese": ["japanese", "jap"],
    "korean": ["korean", "ko"],
}

def get_language_regex(language):
    if language not in LANGUAGES:
        return None

    tokens = LANGUAGES[language]
    # This pattern looks for the token either at the start/end of the string
    # or surrounded by non-alphanumeric characters. This is more flexible than \b.
    return r'(?:^|[^a-zA-Z0-9])(' + '|'.join(map(re.escape, tokens)) + r')(?:$|[^a-zA-Z0-9])'

async def get_search_results(chat_id, query, file_type=None, max_results=10, offset=0, filter=False):
    """For given query return (results, next_offset, total_results)"""
    start_time = time.monotonic()

    # --- Language Processing ---
    language = None
    language_token = None
    query_parts = query.lower().split()
    for part in query_parts:
        for lang, tokens in LANGUAGES.items():
            if part in tokens:
                language = lang
                language_token = part
                break
        if language:
            break

    if language_token:
        query_parts.remove(language_token)
        query = " ".join(query_parts)

    # Clean query for search
    clean_query = query.strip()

    # --- Main Query Processing ---
    filter_criteria = {'$text': {'$search': clean_query}}

    # --- Language Filtering ---
    if language and language != "english":
        lang_regex = re.compile(get_language_regex(language), re.IGNORECASE)
        filter_criteria = {'$and': [filter_criteria, {'$or': [{'file_name': lang_regex}, {'caption': lang_regex}]}]}
    elif language == "english":
        all_other_lang_tokens = [token for lang, tokens in LANGUAGES.items() if lang != 'english' for token in tokens]
        other_langs_regex_pattern = r'(?:^|[^a-zA-Z0-9])(' + '|'.join(map(re.escape, all_other_lang_tokens)) + r')(?:$|[^a-zA-Z0-9])'
        other_langs_regex = re.compile(other_langs_regex_pattern, re.IGNORECASE)
        filter_criteria = {'$and': [filter_criteria, {'$nor': [{'file_name': other_langs_regex}, {'caption': other_langs_regex}]}]}

    # Get total count for pagination
    total_results = 0
    try:
        total_results += col.count_documents(filter_criteria)
        if MULTIPLE_DATABASE:
            total_results += sec_col.count_documents(filter_criteria)
    except Exception as e:
        logger.exception(f"Count documents failed | query='{query}'")

    # Fetch paginated results
    files = []

    # Define the projection to include the text score for sorting
    projection = {'score': {'$meta': 'textScore'}}
    sort_order = [('score', {'$meta': 'textScore'})]

    # Function to fetch from a single collection
    def fetch_from_collection(collection):
        try:
            return list(collection.find(filter_criteria, projection).sort(sort_order))
        except Exception as e:
            logger.exception(f"DB find failed | query='{query}' | collection='{collection.name}'")
            return []

    all_files = fetch_from_collection(col)
    if MULTIPLE_DATABASE:
        all_files.extend(fetch_from_collection(sec_col))
        # Sort combined results by score
        all_files.sort(key=lambda x: x.get('score', 0), reverse=True)

    # Apply pagination to the combined and sorted list
    files = all_files[offset : offset + max_results]

    current_fetched = len(files)
    next_offset = offset + current_fetched if total_results > offset + current_fetched else ""

    duration_ms = int((time.monotonic() - start_time) * 1000)
    logger.info(
        "get_search_results stats | query='%s' | total=%s | next_offset=%s | duration_ms=%s",
        query,
        total_results,
        next_offset,
        duration_ms,
    )

    return files, next_offset, total_results, clean_query


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
    """Return file_id, file_ref"""
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
    return file_id, decoded.file_reference

async def get_all_files(last_id=None):
    """Get all files from the database as a generator, starting after a specific ID."""
    query = {}
    if last_id:
        query['_id'] = {'$gt': last_id}

    cursor = col.find(query).sort('_id', 1)
    for file in cursor:
        yield file

    if MULTIPLE_DATABASE:
        cursor = sec_col.find(query).sort('_id', 1)
        for file in cursor:
            yield file

async def count_all_files():
    """Count all files in the database."""
    count = col.count_documents({})
    if MULTIPLE_DATABASE:
        count += sec_col.count_documents({})
    return count
