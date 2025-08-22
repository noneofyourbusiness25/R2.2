import re
import os

def parse_filename(original_filename):
    """
    Parses and cleans a filename based on a set of rules.
    """
    # 1. Normalization (initial) - remove file extension
    name, _ = os.path.splitext(original_filename)

    # Replace separators with spaces
    name = re.sub(r'[\._]', ' ', name)

    # 2. Match Detection
    series_pattern = r'\b[Ss]\d{1,2}[Ee]\d{1,2}\b'
    year_pattern = r'\b(19|20)\d{2}\b'

    series_match = re.search(series_pattern, name)
    year_match = re.search(year_pattern, name)

    # 3. Extraction & Priority
    if series_match:
        # Series match takes priority
        end_pos = series_match.end()
        name = name[:end_pos]
    elif year_match:
        # Year match
        end_pos = year_match.end()
        name = name[:end_pos]
    else:
        # 4. Fallbacks
        # Fallback 1: cut at first delimiter
        delimiters = [r'\(', r'\[', '1080p', '720p', '480p', '360p']
        first_pos = -1
        for d in delimiters:
            match = re.search(d, name, re.IGNORECASE)
            if match and (first_pos == -1 or match.start() < first_pos):
                first_pos = match.start()

        if first_pos != -1:
            name = name[:first_pos]
        # Fallback 2 is the full normalized name, which is the default if no delimiters are found

    # 5. Final Normalization & Trimming
    # Trim trailing separators and whitespace
    name = name.strip(' ._-')
    # Collapse multiple spaces
    name = re.sub(r'\s+', ' ', name).strip()

    return name
