import re

# --- 1. Preprocessing & Normalization ---

def normalize_text(text):
    """
    Lowercase, replace separators, and normalize punctuation.
    """
    if not text:
        return ""
    # Lowercase
    text = text.lower()
    # Replace separators and runs of punctuation/multiple spaces with a single space
    text = re.sub(r'[\.\_ \-]+', ' ', text)
    # A simple way to handle some unicode punctuation, can be expanded
    text = text.replace('‘', "'").replace('’', "'").replace('“', '"').replace('”', '"')
    return text.strip()

# --- 2. Extraction Rules ---

# Using the regexes from the spec
REGEXES = {
    "s_ep": re.compile(r'\bS(?:eason)?[ ._\-]?0*(\d{1,2})[ ._\-]?[Ee](?:P|p)?0*(\d{1,3})\b', re.IGNORECASE),
    "season_ep": re.compile(r'\bSeason[ ._\-]?0*(\d{1,2})[ ._\-]?Episode[ ._\-]?0*(\d{1,3})\b', re.IGNORECASE),
    "x_style": re.compile(r'\b0*(\d{1,2})x0*(\d{1,3})\b', re.IGNORECASE),
    "ep_only": re.compile(r'\bEP(?:isode)?[ ._\-]?0*(\d{1,3})\b', re.IGNORECASE),
}

LANGUAGES = {
    "hindi": ["hindi", "hin"],
    "english": ["english", "eng"],
    "tamil": ["tamil", "tam"],
    "telugu": ["telugu", "tel"],
    "malayalam": ["malayalam", "mala", "mal"],
    "kannada": ["kannada", "kan"],
    "japanese": ["japanese", "jap"],
    "korean": ["korean", "ko"],
    "bengali": ["bengali", "ben"],
    "urdu": ["urdu", "urd"],
    "spanish": ["spanish", "spa"],
    "french": ["french", "fre"],
}

# Create a single regex for all language tokens
ALL_LANG_TOKENS = [token for lang_tokens in LANGUAGES.values() for token in lang_tokens]
LANG_REGEX = re.compile(r'\b(' + '|'.join(ALL_LANG_TOKENS) + r')\b', re.IGNORECASE)

NOISE_TOKENS = [
    'download', 'movie', '720p', '1080p', '1440p', '2160p', '4k', '8k',
    'web-dl', 'webrip', 'bluray', 'blu-ray', 'x265', 'hevc', '10bit',
    'true', 'hdrip', 'remux', 'proper', 'internal', 'x264', 'ddp', '5.1'
]

def extract_metadata(text):
    """
    Extracts season, episode, language, and quality from normalized text.
    """
    meta = {
        'season': None,
        'episode': None,
        'year': None,
        'languages': [],
        'quality': None,
        'title_candidate': text
    }

    # Extract Season/Episode
    for key, regex in REGEXES.items():
        match = regex.search(text)
        if match:
            meta['season'] = int(match.group(1))
            if len(match.groups()) > 1:
                meta['episode'] = int(match.group(2))
            meta['title_candidate'] = regex.sub('', meta['title_candidate']).strip()
            # Stop after the first successful S/E match
            if meta['season'] and meta['episode']:
                break

    # Extract Year
    year_match = re.search(r'\b(19|20)\d{2}\b', meta['title_candidate'])
    if year_match:
        meta['year'] = int(year_match.group(0))
        meta['title_candidate'] = meta['title_candidate'].replace(year_match.group(0), '').strip()

    # Extract Language
    lang_matches = LANG_REGEX.findall(meta['title_candidate'])
    if lang_matches:
        for lang_match in lang_matches:
            for lang, tokens in LANGUAGES.items():
                if lang_match.lower() in tokens:
                    if lang not in meta['languages']:
                        meta['languages'].append(lang)

    # Clean title candidate by removing noise
    for token in NOISE_TOKENS + ALL_LANG_TOKENS:
        meta['title_candidate'] = re.sub(r'\b' + re.escape(token) + r'\b', '', meta['title_candidate'], flags=re.IGNORECASE)

    meta['title_candidate'] = re.sub(r'\s+', ' ', meta['title_candidate']).strip()

    return meta

# --- 3. Matching & Scoring Algorithm ---

WEIGHTS = {
    'title': 0.40,
    'season': 0.18,
    'episode': 0.18,
    'language': 0.12,
    'caption': 0.06,
    'exact_order': 0.06,
    'penalty': -0.5
}

def compute_score(query_meta, file_meta):
    """
    Computes the match score between a user query and a file.
    """
    score = 0.0

    # Title Score (simple token overlap for now)
    query_tokens = set(query_meta['title_candidate'].split())
    file_tokens = set(file_meta['title_candidate'].split())
    if not query_tokens or not file_tokens:
        title_score = 0
    else:
        intersection = len(query_tokens.intersection(file_tokens))
        union = len(query_tokens.union(file_tokens))
        title_score = intersection / union if union > 0 else 0
    score += WEIGHTS['title'] * title_score

    # Season Score
    if query_meta['season'] is not None:
        if query_meta['season'] == file_meta['season']:
            score += WEIGHTS['season']

    # Episode Score
    if query_meta['episode'] is not None:
        if query_meta['episode'] == file_meta['episode']:
            score += WEIGHTS['episode']

    # Language Score
    if query_meta['languages']:
        if any(lang in file_meta['languages'] for lang in query_meta['languages']):
            score += WEIGHTS['language']

    # Exact Order Bonus
    if query_meta['title_candidate'] in file_meta['title_candidate']:
        score += WEIGHTS['exact_order']

    return score
