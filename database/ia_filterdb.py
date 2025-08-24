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
    """
    Create a robust text index on file_name and caption fields.
    This function will drop any conflicting text indexes and create the desired one.
    """
    for collection in [col, sec_col] if MULTIPLE_DATABASE else [col]:
        try:
            # Check for any existing text indexes
            existing_indexes = collection.index_information()
            text_index_name = None
            for index_name, index_info in existing_indexes.items():
                if 'text' in [key[0] for key in index_info['key']]:
                    text_index_name = index_name
                    break

            # If a text index exists and it's not the one we want, drop it
            if text_index_name and text_index_name != 'file_name_text_caption_text':
                collection.drop_index(text_index_name)
                logger.info(f"Dropped conflicting text index '{text_index_name}' from collection '{collection.name}'.")
                existing_indexes = collection.index_information() # Refresh index info

            # Now, create the desired text index if it doesn't exist
            if 'file_name_text_caption_text' not in existing_indexes:
                collection.create_index(
                    [('file_name', 'text'), ('caption', 'text')],
                    name='file_name_text_caption_text',
                    default_language='english'
                )
                logger.info(f"Text index created successfully for collection '{collection.name}'.")
            else:
                logger.info(f"Text index already exists for collection '{collection.name}'.")

        except Exception as e:
            logger.error(f"Failed to create text index for collection '{collection.name}': {e}")


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
    """
    Conditionally executes a search based on the query type (pattern or text).
    """
    start_time = time.monotonic()

    # --- Language Processing ---
    language, query = process_language_from_query(query)

    # --- Custom Stop Word Removal and Query Sanitization ---
    STOP_WORDS = ["movie", "send", "full", "hd"]
    clean_query = ' '.join([word for word in query.strip().lower().split() if word not in STOP_WORDS])

    # --- Pattern Detection ---
    pattern_regex = detect_and_build_pattern_regex(clean_query)

    if pattern_regex:
        # --- Execute Pattern-Based Search (Regex) ---
        search_type = "PATTERN"
        filter_criteria = {'$or': [{'file_name': pattern_regex}, {'caption': pattern_regex}]}
        if language:
            lang_filter = build_language_filter(language)
            filter_criteria = {'$and': [filter_criteria, lang_filter]}

        try:
            total_results = col.count_documents(filter_criteria)
            if MULTIPLE_DATABASE:
                total_results += sec_col.count_documents(filter_criteria)

            # Fetch, sort by word count, then paginate
            all_files = []
            for collection in [col, sec_col] if MULTIPLE_DATABASE else [col]:
                all_files.extend(list(collection.find(filter_criteria)))

            files = all_files[offset : offset + max_results]
            next_offset = offset + len(files) if total_results > offset + len(files) else ""
        except Exception as e:
            logger.exception(f"Pattern search failed for query='{query}': {e}")
            files, next_offset, total_results = [], "", 0

    else:
        # --- Execute Text-Based Search (Aggregation) ---
        search_type = "TEXT"
        # If the query contains spaces, wrap it in quotes for phrase search
        search_query = f'"{clean_query}"' if ' ' in clean_query else clean_query

        pipeline = []
        match_criteria = {'$text': {'$search': search_query}}
        if language:
            lang_filter = build_language_filter(language)
            match_criteria = {'$and': [match_criteria, lang_filter]}
        pipeline.append({'$match': match_criteria})

        # Add fields and sort
        pipeline.extend([
            {'$addFields': {
                'text_score': {'$meta': 'textScore'},
                'word_count': {'$size': {'$split': ["$file_name", " "]}}
            }},
            {'$sort': {'text_score': -1, 'word_count': 1}}
        ])

        try:
            count_pipeline = pipeline + [{'$count': 'total'}]
            total_results = 0
            all_files = []

            # Since pagination on aggregated results from multiple DBs is tricky,
            # we fetch a bit more and sort/paginate in Python for the multi-db case.
            # For a single DB, we can do it all in the pipeline.
            if MULTIPLE_DATABASE:
                 for collection in [col, sec_col]:
                    all_files.extend(list(collection.aggregate(pipeline)))
                 all_files.sort(key=lambda x: (x.get('text_score', 0), x.get('word_count', float('inf'))), reverse=False) # Note: this sort is tricky
                 total_results = len(all_files)
                 files = all_files[offset : offset + max_results]
            else:
                total_results_cursor = col.aggregate(count_pipeline)
                total_results = next(total_results_cursor, {'total': 0})['total']

                paginated_pipeline = pipeline + [{'$skip': offset}, {'$limit': max_results}]
                files = list(col.aggregate(paginated_pipeline))

            next_offset = offset + len(files) if total_results > offset + len(files) else ""
        except Exception as e:
            logger.exception(f"Aggregation pipeline failed for query='{query}': {e}")
            files, next_offset, total_results = [], "", 0

    duration_ms = int((time.monotonic() - start_time) * 1000)
    logger.info(
        "get_search_results stats | type=%s | query='%s' | total=%s | next_offset=%s | duration_ms=%s",
        search_type, clean_query, total_results, next_offset, duration_ms
    )

    return files, next_offset, total_results, clean_query

def process_language_from_query(query):
    """Extracts language from query and returns the language and cleaned query."""
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
    return language, query

def build_language_filter(language):
    """Builds the language filter part of the MongoDB query."""
    if language and language != "english":
        lang_regex = re.compile(get_language_regex(language), re.IGNORECASE)
        return {'$or': [{'file_name': lang_regex}, {'caption': lang_regex}]}
    elif language == "english":
        all_other_lang_tokens = [token for lang, tokens in LANGUAGES.items() if lang != 'english' for token in tokens]
        other_langs_regex_pattern = r'(?:^|[^a-zA-Z0-9])(' + '|'.join(map(re.escape, all_other_lang_tokens)) + r')(?:$|[^a-zA-Z0-9])'
        other_langs_regex = re.compile(other_langs_regex_pattern, re.IGNORECASE)
        return {'$nor': [{'file_name': other_langs_regex}, {'caption': other_langs_regex}]}
    return {}

def detect_and_build_pattern_regex(query_text):
    """
    Detects if a query is for a season/episode pattern and builds a regex for it.
    Returns a regex object if a pattern is found, otherwise None.
    """
    # More comprehensive pattern for SXXEXX, SXX EXX, Season X Episode X, etc.
    se_match = re.search(r'\b(s|season)\s?(\d{1,2})[\s\._-]*(e|ep|episode)\s?(\d{1,3})\b', query_text, re.IGNORECASE)
    if se_match:
        season = int(se_match.group(2))
        episode = int(se_match.group(4))
        # Build a flexible regex for this specific S/E combination
        s_str, s0_str = f"{season:01d}", f"{season:02d}"
        e_str, e0_str = f"{episode:01d}", f"{episode:02d}"
        # This regex is very flexible: allows for "S01E01", "S01 E01", "S01EP01", "S01 EP 01", etc.
        pattern = f"S(0?{s_str}|{s0_str})[\\s\\._-]*?(E|EP)?[\\s\\._-]*?(0?{e_str}|{e0_str})"
        return re.compile(pattern, re.IGNORECASE)

    # Pattern for just a season, like "S01" or "Season 1"
    s_match = re.search(r'\b(s|season)\s?(\d{1,2})\b', query_text, re.IGNORECASE)
    if s_match:
        season = int(s_match.group(2))
        s_str, s0_str = f"{season:01d}", f"{season:02d}"
        # This regex finds the season. It's less specific than the S/E pattern,
        # so the S/E pattern must be checked first.
        pattern = f"S(0?{s_str}|{s0_str})"
        return re.compile(pattern, re.IGNORECASE)

    return None


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
