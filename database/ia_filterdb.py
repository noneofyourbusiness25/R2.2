# Don't Remove Credit @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot @Tech_VJ
# Ask Doubt on telegram @KingVJ01

import re, base64, json, asyncio
from struct import pack
from pyrogram.file_id import FileId
from pymongo.errors import DuplicateKeyError
from info import FILE_DB_URI, SEC_FILE_DB_URI, DATABASE_NAME, COLLECTION_NAME, MULTIPLE_DATABASE, USE_CAPTION_FILTER, MAX_B_TN
import motor.motor_asyncio

# Async MongoDB clients and collections
_file_client = motor.motor_asyncio.AsyncIOMotorClient(FILE_DB_URI)
_file_db = _file_client[DATABASE_NAME]
col = _file_db[COLLECTION_NAME]

_sec_col = None
if MULTIPLE_DATABASE:
    _sec_client = motor.motor_asyncio.AsyncIOMotorClient(SEC_FILE_DB_URI)
    _sec_db = _sec_client[DATABASE_NAME]
    _sec_col = _sec_db[COLLECTION_NAME]

# Ensure indexes once (non-unique for speed and to avoid migration failures)
_indexes_created = False
_index_lock = asyncio.Lock()

async def _ensure_indexes():
    global _indexes_created
    if _indexes_created:
        return
    async with _index_lock:
        if _indexes_created:
            return
        # Speed up duplicate checks and searches
        await col.create_index('file_id')
        await col.create_index('file_name')
        if MULTIPLE_DATABASE and _sec_col is not None:
            await _sec_col.create_index('file_id')
            await _sec_col.create_index('file_name')
        _indexes_created = True


async def save_file(media):
    """Save file metadata in the database (no binary upload).
    Returns (saved: bool, code: int)
      - (True, 1): inserted
      - (False, 0): duplicate
      - (False, 2): other error
    """
    await _ensure_indexes()

    file_id = unpack_new_file_id(media.file_id)
    file_name = clean_file_name(media.file_name)

    file = {
        'file_id': file_id,
        'file_name': file_name,
        'file_size': media.file_size,
        'caption': media.caption.html if media.caption else None
    }

    try:
        # Duplicate check on primary first
        if await is_file_already_saved(file_id, file_name):
            return False, 0

        # Try insert on primary
        try:
            await col.insert_one(file)
            print(f"{file_name} is successfully saved.")
            return True, 1
        except DuplicateKeyError:
            # In case unique index is later enabled
            print(f"{file_name} is already saved (duplicate key).")
            return False, 0
        except Exception:
            # If primary fails (e.g., capacity), try secondary when enabled
            if MULTIPLE_DATABASE and _sec_col is not None:
                # Check duplicate in secondary before insert
                if await _sec_col.count_documents({'$or': [{'file_id': file_id}, {'file_name': file_name}]}) > 0:
                    print(f"{file_name} is already saved (secondary).")
                    return False, 0
                try:
                    await _sec_col.insert_one(file)
                    print(f"{file_name} is successfully saved (secondary).")
                    return True, 1
                except DuplicateKeyError:
                    print(f"{file_name} is already saved (secondary duplicate key).")
                    return False, 0
                except Exception:
                    print("Secondary database insert failed.")
                    return False, 2
            else:
                print("Primary database insert failed. If DB is full, enable MULTIPLE_DATABASE and provide secondary DB URI.")
                return False, 2
    except Exception:
        # Any unexpected error path
        return False, 2


def clean_file_name(file_name):
    """Clean and format the file name."""
    file_name = re.sub(r"(_|\-|\.|\+)", " ", str(file_name))
    unwanted_chars = ['[', ']', '(', ')', '{', '}']
    for char in unwanted_chars:
        file_name = file_name.replace(char, '')
    return ' '.join(
        filter(
            lambda x: not x.startswith('@') and not x.startswith('http') and not x.startswith('www.') and not x.startswith('t.me'),
            file_name.split()
        )
    )


async def is_file_already_saved(file_id, file_name):
    """Check if the file already exists in primary (and secondary if enabled)."""
    query = {'$or': [{'file_id': file_id}, {'file_name': file_name}]}

    # Check primary
    if await col.count_documents(query) > 0:
        print(f"{file_name} is already saved.")
        return True

    # Check secondary only when enabled
    if MULTIPLE_DATABASE and _sec_col is not None:
        if await _sec_col.count_documents(query) > 0:
            print(f"{file_name} is already saved (secondary).")
            return True

    return False


async def get_search_results(chat_id, query, file_type=None, max_results=10, offset=0, filter=False):
    """For given query return (results, next_offset, total_results)"""
    await _ensure_indexes()

    query = query.strip()
    if not query:
        raw_pattern = '.'
    elif ' ' not in query:
        raw_pattern = r'(\b|[\.\+\-_])' + query + r'(\b|[\.\+\-_])'
    else:
        raw_pattern = query.replace(' ', r'.*[\s\.\+\-_]')

    try:
        regex = re.compile(raw_pattern, flags=re.IGNORECASE)
    except Exception:
        regex = query

    filter_q = {'file_name': regex}

    files = []
    if MULTIPLE_DATABASE and _sec_col is not None:
        cursor1 = col.find(filter_q).sort('$natural', -1).skip(offset).limit(max_results)
        cursor2 = _sec_col.find(filter_q).sort('$natural', -1).skip(offset).limit(max_results)
        async for f in cursor1:
            files.append(f)
        async for f in cursor2:
            files.append(f)
        total_results = await col.count_documents(filter_q) + await _sec_col.count_documents(filter_q)
    else:
        cursor = col.find(filter_q).sort('$natural', -1).skip(offset).limit(max_results)
        async for f in cursor:
            files.append(f)
        total_results = await col.count_documents(filter_q)

    next_offset = "" if (offset + max_results) >= total_results else (offset + max_results)
    return files, next_offset, total_results


async def get_bad_files(query, file_type=None, use_filter=False):
    """For given query return (results, total_results)"""
    await _ensure_indexes()

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

    async def count_documents(collection):
        return await collection.count_documents(filter_criteria)

    async def find_documents(collection):
        return await collection.find(filter_criteria).to_list(length=None)

    if MULTIPLE_DATABASE and _sec_col is not None:
        total_results = await count_documents(col) + await count_documents(_sec_col)
        files = (await find_documents(col)) + (await find_documents(_sec_col))
    else:
        total_results = await count_documents(col)
        files = await find_documents(col)

    return files, total_results


async def get_file_details(query):
    await _ensure_indexes()
    doc = await col.find_one({'file_id': query})
    if doc:
        return doc
    if MULTIPLE_DATABASE and _sec_col is not None:
        return await _sec_col.find_one({'file_id': query})
    return None


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
    
