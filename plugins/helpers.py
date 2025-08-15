import re, os, json, random, asyncio, logging
from info import *
from imdb import Cinemagoer
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram import enums
from pyrogram.errors import *
from typing import Union, List
from Script import script
from datetime import datetime
from database.users_chats_db import db
from database.join_reqs import JoinReqs
from bs4 import BeautifulSoup
from shortzy import Shortzy

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
imdb = Cinemagoer()
BTN_URL_REGEX = re.compile(r"(\[([^\[]+?)\]\((buttonurl|buttonalert):(?:/{0,2})(.+?)(:same)?\))")
SMART_OPEN = '“'
SMART_CLOSE = '”'
START_CHAR = ('\'', '"', SMART_OPEN)

class temp(object):
    BANNED_USERS = []
    BANNED_CHATS = []
    ME = None
    BOT = None
    CURRENT=int(os.environ.get("SKIP", 2))
    CANCEL = False
    MELCOW = {}
    U_NAME = None
    B_NAME = None
    GETALL = {}
    SHORT = {}
    SETTINGS = {}
    IMDB_CAP = {}

# --- 1. Preprocessing & Normalization ---

def normalize_text(text):
    if not text: return ""
    text = text.lower()
    text = re.sub(r'[\.\_\-\(\)\[\]]+', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

# --- 2. Extraction Rules ---

LANGUAGES = {
    "hindi": ["hindi", "hin"], "english": ["english", "eng"], "tamil": ["tamil", "tam"],
    "telugu": ["telugu", "tel"], "malayalam": ["malayalam", "mala", "mal"], "kannada": ["kannada", "kan"],
    "japanese": ["japanese", "jap"], "korean": ["korean", "ko"], "bengali": ["bengali", "ben"],
    "urdu": ["urdu", "urd"], "spanish": ["spanish", "spa"], "french": ["french", "fre"],
}
ALL_LANG_TOKENS = [token for lang_tokens in LANGUAGES.values() for token in lang_tokens]
LANGUAGE_REGEX = re.compile(r'\b(' + '|'.join(ALL_LANG_TOKENS) + r')\b', re.IGNORECASE)

NOISE_TOKENS = [
    '720p', '1080p', '1440p', '2160p', '4k', '8k', '3d', 'web-dl', 'webdl', 'webrip',
    'web-rip', 'bluray', 'blu-ray', 'bdrip', 'x264', 'x265', 'h264', 'h265', 'hevc',
    '10bit', 'truehd', 'atmos', 'ddp', '5.1', 'hdrip', 'remux', 'proper', 'internal',
    'multi', 'sub', 'download', 'movie', 'series', 'tv'
]
SE_REGEX_PATTERNS = [
    re.compile(r'(?i)\bS(?:eason)?[ ._\-]?0*(\d{1,2})[ ._\-]?[Ee](?:P|p|pisode)?[ ._\-]?0*(\d{1,3})\b'),
    re.compile(r'(?i)\bSeason[ ._\-]?0*(\d{1,2})[ ._\-]?Episode[ ._\-]?0*(\d{1,3})\b'),
    re.compile(r'(?i)\b0*(\d{1,2})x0*(\d{1,3})\b'),
    re.compile(r'(?i)\bEP(?:isode)?[ ._\-]?0*(\d{1,3})\b'),
    re.compile(r'(?i)\bE[ ._\-]?0*(\d{1,3})\b')
]

def get_title_tokens(text):
    tokens = text.split()
    tokens = [t for t in tokens if t not in NOISE_TOKENS and t.lower() not in ALL_LANG_TOKENS]
    for pattern in SE_REGEX_PATTERNS:
        text = pattern.sub('', text)
    return text.split()

def extract_metadata(file_data):
    filename = file_data.get('file_name', '')
    caption = file_data.get('caption', '')
    full_text_raw = f"{filename} {caption if caption else ''}"
    normalized_text = normalize_text(full_text_raw)

    meta = {
        'season': None, 'episode': None, 'language': None, 'year': None,
        'title_tokens': [], 'raw_title': filename.rsplit('.', 1)[0]
    }
    text_to_parse = normalized_text

    for pattern in SE_REGEX_PATTERNS:
        match = pattern.search(text_to_parse)
        if match:
            groups = match.groups()
            if len(groups) == 2:
                meta['season'], meta['episode'] = int(groups[0]), int(groups[1])
            elif len(groups) == 1:
                meta['episode'] = int(groups[0])
            text_to_parse = pattern.sub(' ', text_to_parse).strip()
            if meta.get('season') and meta.get('episode'):
                break

    lang_match = LANGUAGE_REGEX.search(text_to_parse)
    if lang_match:
        found_token = lang_match.group(1).lower()
        for lang, tokens in LANGUAGES.items():
            if found_token in tokens:
                meta['language'] = lang
                break
        if meta['language']:
            text_to_parse = LANGUAGE_REGEX.sub(' ', text_to_parse).strip()

    year_match = re.search(r'\b((?:19|20)\d{2})\b', text_to_parse)
    if year_match:
        meta['year'] = int(year_match.group(1))
        text_to_parse = text_to_parse.replace(year_match.group(1), ' ', 1).strip()

    meta['title_tokens'] = get_title_tokens(text_to_parse)
    return meta

# --- 3. Matching & Scoring ---

def compute_score(query_meta, file_meta):
    w = {'title': 0.40, 'season': 0.18, 'episode': 0.18, 'language': 0.12, 'caption': 0.06, 'exact_order': 0.06}
    score = 0.0
    query_title_tokens = set(query_meta['title_tokens'])
    file_title_tokens = set(file_meta['title_tokens'])

    if query_title_tokens:
        intersection = len(query_title_tokens.intersection(file_title_tokens))
        union = len(query_title_tokens.union(file_title_tokens))
        title_score = intersection / union if union > 0 else 0
        extra_words = len(file_title_tokens - query_title_tokens)
        title_score -= (extra_words * 0.05)
        score += w['title'] * max(0, title_score)

    if query_meta.get('season'):
        score += w['season'] if query_meta['season'] == file_meta['season'] else -0.5
    if query_meta.get('episode'):
        score += w['episode'] if query_meta['episode'] == file_meta['episode'] else 0
    if query_meta.get('language'):
        if query_meta['language'] == file_meta['language']:
            score += w['language']
        elif file_meta['language'] is not None:
            score -= 0.5
    return max(0, score)

# --- Other Helper Functions from utils.py ---

def get_size(size):
    units = ["Bytes", "KB", "MB", "GB", "TB", "PB", "EB"]
    size = float(size)
    i = 0
    while size >= 1024.0 and i < len(units):
        i += 1
        size /= 1024.0
    return "%.2f %s" % (size, units[i])

async def get_settings(group_id):
    return await db.get_settings(group_id)

async def save_group_settings(group_id, key, value):
    current = await get_settings(group_id)
    current.update({key: value})
    await db.update_settings(group_id, current)

async def is_subscribed(bot, query):
    # Simplified version for brevity
    try:
        user = await bot.get_chat_member(AUTH_CHANNEL, query.from_user.id)
        return user.status not in [enums.ChatMemberStatus.BANNED, enums.ChatMemberStatus.LEFT]
    except UserNotParticipant:
        return False
    except Exception:
        return True # Assume subscribed if there's an error to avoid blocking users

async def pub_is_subscribed(bot, query, channel):
    # This function seems to be for multiple force-subscribe channels
    # Re-implementing based on its original purpose
    btn = []
    for id in channel:
        chat = await bot.get_chat(int(id))
        try:
            await bot.get_chat_member(id, query.from_user.id)
        except UserNotParticipant:
            btn.append([InlineKeyboardButton(f'Join {chat.title}', url=chat.invite_link)])
    return btn
