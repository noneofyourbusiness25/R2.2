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
    return r'\b(' + '|'.join(tokens) + r')\b'

def build_filter_query(state):
    query_text = state.get('query', '')
    filters = state.get('filters', {})
    filter_clauses = []

    # --- Title Filter ---
    # Each word in the query must be present in the name or caption
    title_parts = [re.escape(part) for part in query_text.split() if part]
    if title_parts:
        for part in title_parts:
            regex = re.compile(part, flags=re.IGNORECASE)
            filter_clauses.append({'$or': [{'file_name': regex}, {'caption': regex}]})

    # --- Season/Episode Filter ---
    season = filters.get('s')
    episode = filters.get('e')
    if season and episode:
        # Strict SXXEXX search
        s_str, s0_str = f"{season:01d}", f"{season:02d}"
        e_str, e0_str = f"{episode:01d}", f"{episode:02d}"
        se_pattern = f"S(0?{s_str}|{s0_str})[\\s\\._-]*?(E|EP)?[\\s\\._-]*?(0?{e_str}|{e0_str})"
        se_regex = re.compile(se_pattern, re.IGNORECASE)
        filter_clauses.append({'$or': [{'file_name': se_regex}, {'caption': se_regex}]})
    elif season:
        # Search for season only, e.g., "S01" or "Season 01"
        season_pattern = r'\b(s|season)\s?(0?' + str(season) + r'|' + f"{season:02d}" + r')\b'
        season_regex = re.compile(season_pattern, re.IGNORECASE)
        filter_clauses.append({'$or': [{'file_name': season_regex}, {'caption': season_regex}]})

    # --- Year Filter ---
    year = filters.get('year')
    if year:
        year_regex = re.compile(str(year))
        filter_clauses.append({'$or': [{'file_name': year_regex}, {'caption': year_regex}]})

    # --- Language Filter ---
    language = filters.get('lang')
    if language and language != "english":
        lang_regex_str = get_language_regex(language)
        if lang_regex_str:
            lang_regex = re.compile(lang_regex_str, re.IGNORECASE)
            filter_clauses.append({'$or': [{'file_name': lang_regex}, {'caption': lang_regex}]})
    elif language == "english":
        all_other_lang_tokens = [token for lang, tokens in LANGUAGES.items() if lang != 'english' for token in tokens]
        other_langs_regex = re.compile(r'\b(' + '|'.join(all_other_lang_tokens) + r')\b', re.IGNORECASE)
        filter_clauses.append({
            '$nor': [
                {'file_name': other_langs_regex},
                {'caption': other_langs_regex}
            ]
        })

    if not filter_clauses:
        return {} # Match all documents if no criteria is provided

    # Combine all clauses with $and
    return {'$and': filter_clauses} if len(filter_clauses) > 1 else filter_clauses[0]

async def get_search_results(chat_id, query, file_type=None, max_results=10, offset=0, filter=False):
    """For given query return (results, next_offset, total_results)"""

    start_time = time.monotonic()

    if isinstance(query, str):
        # Handle old format or calls from other parts of the code for compatibility
        state = {'query': query, 'filters': {}}
    else:
        state = query

    # Use the new, robust query builder
    filter_criteria = build_filter_query(state)

    # For logging purposes, create a representative string
    query_log_string = json.dumps(state)
    raw_pattern = query_log_string # Use the json string for the pattern log

    # Get total count for pagination
    total_results = 0
    try:
        total_results += col.count_documents(filter_criteria)
        if MULTIPLE_DATABASE:
            total_results += sec_col.count_documents(filter_criteria)
    except Exception as e:
        logger.exception(f"Count documents failed | query='{query_log_string}'")

    # Fetch paginated results
    files = []
    fetched_primary = 0
    fetched_secondary = 0

    if MULTIPLE_DATABASE:
        try:
            # Primary DB query
            primary_count = col.count_documents(filter_criteria)
            cursor1 = col.find(filter_criteria).sort('$natural', -1).skip(offset).limit(max_results)
            for file in cursor1:
                files.append(file)
                fetched_primary += 1

            # Secondary DB query if needed
            remaining_limit = max_results - fetched_primary
            if remaining_limit > 0:
                secondary_offset = max(0, offset - primary_count)
                cursor2 = sec_col.find(filter_criteria).sort('$natural', -1).skip(secondary_offset).limit(remaining_limit)
                for file in cursor2:
                    files.append(file)
                    fetched_secondary += 1
        except Exception as e:
            logger.exception(f"DB find failed | query='{query_log_string}'")
    else:
        try:
            cursor = col.find(filter_criteria).sort('$natural', -1).skip(offset).limit(max_results)
            for file in cursor:
                files.append(file)
                fetched_primary += 1
        except Exception as e:
            logger.exception(f"Primary DB find failed (single DB mode) | query='{query_log_string}'")

    current_fetched = len(files)
    next_offset = offset + current_fetched if total_results > offset + current_fetched else ""

    duration_ms = int((time.monotonic() - start_time) * 1000)
    logger.info(
        "get_search_results stats | query='%s' | pattern='%s' | total=%s | next_offset=%s | fetched_primary=%s | fetched_secondary=%s | duration_ms=%s",
        query_log_string,
        raw_pattern,
        total_results,
        next_offset,
        fetched_primary,
        fetched_secondary,
        duration_ms,
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
