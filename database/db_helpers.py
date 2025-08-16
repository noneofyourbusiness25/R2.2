import re
from utils import extract_year, extract_season_episode, extract_languages

def get_available_seasons(results):
    """Extracts unique season numbers from a list of file results."""
    seasons = set()
    for result in results:
        text_to_parse = result.get('file_name', '')
        if result.get('caption'):
            text_to_parse += " " + result.get('caption')

        season_episode_match, _ = extract_season_episode(text_to_parse)
        if season_episode_match:
            # "Season X Episode Y" -> "Season X" -> "X"
            season_str = season_episode_match.split(' Episode ')[0]
            season_num = re.findall(r'\d+', season_str)
            if season_num:
                seasons.add(int(season_num[0]))
    return sorted(list(seasons))

def get_available_episodes(results, season_number):
    """Extracts unique episode numbers for a given season from a list of file results."""
    episodes = set()
    for result in results:
        text_to_parse = result.get('file_name', '')
        if result.get('caption'):
            text_to_parse += " " + result.get('caption')

        season_episode_match, _ = extract_season_episode(text_to_parse)
        if season_episode_match:
            # "Season X Episode Y"
            try:
                season_part, episode_part = season_episode_match.split(' Episode ')
                current_season_num = int(re.findall(r'\d+', season_part)[0])
                if current_season_num == season_number:
                    episode_num = int(re.findall(r'\d+', episode_part)[0])
                    episodes.add(episode_num)
            except (ValueError, IndexError):
                continue
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
