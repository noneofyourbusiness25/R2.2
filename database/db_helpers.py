import re
from utils import extract_year, extract_s_e_numbers, extract_languages

def get_available_seasons(results):
    """Extracts unique season numbers from a list of file results."""
    seasons = set()
    for result in results:
        text_to_parse = result.get('file_name', '')
        if result.get('caption'):
            text_to_parse += " " + result.get('caption')

        season, _ = extract_s_e_numbers(text_to_parse)
        if season is not None:
            seasons.add(season)
    return sorted(list(seasons))

def get_available_episodes(results, season_number):
    """Extracts unique episode numbers for a given season from a list of file results."""
    episodes = set()
    for result in results:
        text_to_parse = result.get('file_name', '')
        if result.get('caption'):
            text_to_parse += " " + result.get('caption')

        season, episode = extract_s_e_numbers(text_to_parse)
        if season == season_number and episode is not None:
            episodes.add(episode)
    return sorted(list(episodes))

def get_available_years(results):
    """Extracts unique years from a list of file results."""
    years = set()
    for result in results:
        text_to_parse = result.get('file_name', '')
        if result.get('caption'):
            text_to_parse += " " + result.get('caption')

        year = extract_year(text_to_parse)
        if year:
            years.add(int(year))
    return sorted(list(years), reverse=True)

def get_available_languages(results):
    """Extracts unique languages from a list of file results."""
    languages = set()
    for result in results:
        text_to_parse = result.get('file_name', '')
        if result.get('caption'):
            text_to_parse += " " + result.get('caption')

        langs = extract_languages(text_to_parse)
        if langs:
            for lang in langs:
                languages.add(lang.lower())
    return sorted(list(languages))
