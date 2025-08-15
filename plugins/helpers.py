import re

# --- 1. Preprocessing & Normalization ---

def normalize_query(text):
    """Normalizes a query string for searching."""
    if not text: return ""
    text = text.lower()
    # Replace dots, underscores, etc., with spaces
    text = re.sub(r'[\.\_\-\(\)\[\]]+', ' ', text)
    # Remove extra spaces
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
SE_REGEX = re.compile(r'\b(s|season)\s?0*(\d{1,2})\b', re.IGNORECASE)
EP_REGEX = re.compile(r'\b(e|ep|episode)\s?0*(\d{1,3})\b', re.IGNORECASE)

def extract_filters(query):
    """Extracts filters (year, language, season, episode) from a normalized query."""
    filters = {'year': None, 'language': None, 'season': None, 'episode': None}

    # Extract year
    year_match = re.search(r'\b((?:19|20)\d{2})\b', query)
    if year_match:
        filters['year'] = year_match.group(1)
        query = query.replace(year_match.group(1), '', 1).strip()

    # Extract language
    lang_match = LANGUAGE_REGEX.search(query)
    if lang_match:
        found_token = lang_match.group(1).lower()
        for lang, tokens in LANGUAGES.items():
            if found_token in tokens:
                filters['language'] = lang
                break
        if filters['language']:
            query = LANGUAGE_REGEX.sub('', query).strip()

    # Extract season
    season_match = SE_REGEX.search(query)
    if season_match:
        filters['season'] = season_match.group(2)
        query = SE_REGEX.sub('', query).strip()

    # Extract episode
    episode_match = EP_REGEX.search(query)
    if episode_match:
        filters['episode'] = episode_match.group(2)
        query = EP_REGEX.sub('', query).strip()

    # The rest is the base title
    base_query = ' '.join([word for word in query.split() if word not in NOISE_TOKENS])

    return base_query, filters

# --- 3. Matching & Scoring ---

def calculate_score(file_name, filters):
    """Calculates a relevance score for a file based on the user's filters."""
    normalized_file_name = normalize_query(file_name)
    score = 0
    matched_filters = []

    # Base title match (Jaccard similarity)
    query_title_tokens = set(filters.get('title', '').split())
    file_title_tokens = set(normalized_file_name.split())

    # Remove noise from file title tokens for a cleaner match
    file_title_tokens = {token for token in file_title_tokens if token not in NOISE_TOKENS and not token.isdigit()}

    if query_title_tokens:
        intersection = len(query_title_tokens.intersection(file_title_tokens))
        union = len(query_title_tokens.union(file_title_tokens))
        title_score = intersection / union if union > 0 else 0

        # Penalize for extra words in the file name
        extra_words_penalty = len(file_title_tokens - query_title_tokens) * 0.05
        title_score = max(0, title_score - extra_words_penalty)

        if title_score > 0.1: # Threshold to consider it a match
            score += title_score * 0.5 # Title match is 50% of the score
            matched_filters.append('title')

    # Filter matching
    # Year
    if filters.get('year'):
        if filters['year'] in normalized_file_name:
            score += 0.2
            matched_filters.append('year')
        else:
            score -= 0.5 # Heavy penalty if year is specified but doesn't match

    # Language
    if filters.get('language'):
        lang_tokens = LANGUAGES.get(filters['language'], [])
        if any(token in normalized_file_name for token in lang_tokens):
            score += 0.15
            matched_filters.append('language')
        else:
            # Check if any other language is present
            if LANGUAGE_REGEX.search(normalized_file_name):
                 score -= 0.5 # Heavy penalty if another language is present

    # Season
    if filters.get('season'):
        se_str = f"s{int(filters['season']):02d}"
        if se_str in normalized_file_name:
            score += 0.15
            matched_filters.append('season')
        else:
            score -= 0.5

    # Episode
    if filters.get('episode'):
        ep_str = f"e{int(filters['episode']):02d}"
        if ep_str in normalized_file_name:
            score += 0.15
            matched_filters.append('episode')
        else:
            score -= 0.5

    return max(0, score), matched_filters
