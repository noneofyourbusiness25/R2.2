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

STOP_WORDS = ["download", "full", "hd", "send", "movie", "series"]

def normalize_and_generate_regex(query_text):
    # Clean the query by removing stop words
    query_text = ' '.join([word for word in query_text.split() if word.lower() not in STOP_WORDS])

    # --- Parse Season/Episode ---
    season = None
    episode = None
    season_match = re.search(r'\b(s|season)\s?(\d{1,2})\b', query_text, re.IGNORECASE)
    if season_match:
        season = int(season_match.group(2))
        query_text = query_text.replace(season_match.group(0), '')

    episode_match = re.search(r'\b(e|ep|episode)\s?(\d{1,3})\b', query_text, re.IGNORECASE)
    if episode_match:
        episode = int(episode_match.group(2))
        query_text = query_text.replace(episode_match.group(0), '')

    # --- Parse Year ---
    year = None
    year_match = re.search(r'\b(19|20)\d{2}\b', query_text)
    if year_match:
        year = year_match.group(0)
        query_text = query_text.replace(year_match.group(0), '')

    # --- The rest is the title ---
    title = query_text.strip()

    # --- Build Regex ---
    regex_parts = []
    if title:
        title_parts = title.split(' ')
        regex_parts.append(''.join([f'(?=.*{re.escape(part)})' for part in title_parts]))

    if year:
        regex_parts.append(f'(?=.*{year})')

    if season is not None and episode is not None:
        s_str = f"{season:01d}"
        s0_str = f"{season:02d}"
        e_str = f"{episode:01d}"
        e0_str = f"{episode:02d}"

        se_regex = f"S(0?{s_str}|{s0_str})[\\s\\._-]*E(P|p)?(0?{e_str}|{e0_str})"
        regex_parts.append(f'(?=.*{se_regex})')
    elif season is not None:
        s_str = f"{season:01d}"
        s0_str = f"{season:02d}"
        s_regex = f"S(0?{s_str}|{s0_str})"
        regex_parts.append(f'(?=.*{s_regex})')

    final_regex = ''.join(regex_parts)

    return final_regex if final_regex else ".*" # Return ".*" if no parts were found

async def get_search_results(chat_id, query, file_type=None, max_results=10, offset=0, filter=False):
    """For given query return (results, next_offset)"""

    start_time = time.monotonic()

    raw_pattern = normalize_and_generate_regex(query)

    try:
        regex = re.compile(raw_pattern, flags=re.IGNORECASE)
    except re.error:
        regex = re.escape(query)

    filter_criteria = {'$or': [{'file_name': regex}, {'caption': regex}]}

    # Extract language from query for filtering, but don't use it for the main search pattern
    language = None
    parts = query.split()
    for part in parts:
        if part.lower() in [lang for sublist in LANGUAGES.values() for lang in sublist]:
            for lang, tokens in LANGUAGES.items():
                if part.lower() in tokens:
                    language = lang
                    break

    if language and language != "english":
        lang_regex = re.compile(get_language_regex(language), re.IGNORECASE)
        filter_criteria = {
            '$and': [
                filter_criteria,
                {'$or': [{'file_name': lang_regex}, {'caption': lang_regex}]}
            ]
        }
    elif language == "english":
        all_other_lang_tokens = [token for lang, tokens in LANGUAGES.items() if lang != 'english' for token in tokens]
        other_langs_regex = re.compile(r'\b(' + '|'.join(all_other_lang_tokens) + r')\b', re.IGNORECASE)

        filter_criteria = {
            '$and': [
                filter_criteria,
                {
                    '$nor': [
                        {'file_name': other_langs_regex},
                        {'caption': other_langs_regex}
                    ]
                }
            ]
        }

    files = []
    fetched_primary = 0
    fetched_secondary = 0

    if MULTIPLE_DATABASE:
        try:
            cursor1 = col.find(filter_criteria).sort('$natural', -1).skip(offset).limit(max_results)
            for file in cursor1:
                files.append(file)
                fetched_primary += 1
        except Exception as e:
            logger.exception(f"Primary DB find failed | query='{query}' | pattern='{raw_pattern}'")
        try:
            cursor2 = sec_col.find(filter_criteria).sort('$natural', -1).skip(offset).limit(max_results)
            for file in cursor2:
                files.append(file)
                fetched_secondary += 1
        except Exception as e:
            logger.exception(f"Secondary DB find failed | query='{query}' | pattern='{raw_pattern}'")
    else:
        try:
            cursor = col.find(filter_criteria).sort('$natural', -1).skip(offset).limit(max_results)
            for file in cursor:
                files.append(file)
                fetched_primary += 1
        except Exception:
            logger.exception(f"Primary DB find failed (single DB mode) | query='{query}' | pattern='{raw_pattern}'")

    total_results = len(files)
    next_offset = "" if len(files) < max_results else (offset + max_results)

    duration_ms = int((time.monotonic() - start_time) * 1000)
    logger.info(
        "get_search_results stats | query='%s' | pattern='%s' | total=%s | next_offset=%s | fetched_primary=%s | fetched_secondary=%s | duration_ms=%s",
        query,
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
