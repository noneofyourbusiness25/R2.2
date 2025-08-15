# Don't Remove Credit @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot @Tech_VJ
# Ask Doubt on telegram @KingVJ01

import os, logging, base64, json
from collections import defaultdict
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram import Client, filters, enums
from pyrogram.errors import UserIsBlocked
from info import ADMINS, LOG_CHANNEL
from plugins.helpers import (
    get_size, temp, get_settings, is_subscribed,
    normalize_text, extract_metadata, compute_score
)
from database.ia_filterdb import get_search_results as get_initial_results

logger = logging.getLogger(__name__)

# In-memory cache for search results and user filters
temp.CACHED_RESULTS = {}

@Client.on_message((filters.group | filters.private) & filters.text & filters.incoming)
async def auto_filter_handler(client, message):
    if message.text.startswith("/"):
        return

    settings = await get_settings(message.chat.id)
    if not settings.get('auto_ffilter', True):
        return

    if settings.get('fsub') and not await is_subscribed(client, message):
        return await message.reply_text(
            "Please join our channel to use this bot.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Join Channel", url=f"https://t.me/{client.invitelink}")]
            ])
        )

    await run_search(client, message, message.text)


async def run_search(client, message, query):
    reply_msg = await message.reply_text("🔎 `Searching...`")

    normalized_query = normalize_text(query)
    query_meta = extract_metadata({'file_name': normalized_query})

    initial_files, total_results = await get_initial_results(normalized_query)
    if not initial_files:
        return await reply_msg.edit("🤷‍♂️ `No results found!`")

    processed_results = []
    for file in initial_files:
        file_meta = extract_metadata(file)
        score = compute_score(query_meta, file_meta)

        if score >= 0.35:
            processed_results.append({'file': file, 'meta': file_meta, 'score': score})

    processed_results.sort(key=lambda x: x['score'], reverse=True)

    if not processed_results:
        return await reply_msg.edit("🤷‍♂️ `No results found after filtering!`")

    search_key = base64.urlsafe_b64encode(os.urandom(8)).decode('utf-8')
    temp.CACHED_RESULTS[search_key] = {
        'results': processed_results,
        'user_filters': {}
    }

    await display_results(reply_msg, search_key)


async def display_results(message, search_key):
    cached_data = temp.CACHED_RESULTS.get(search_key)
    if not cached_data:
        return await message.edit("`Search expired, please try again.`")

    results = cached_data['results']
    user_filters = cached_data['user_filters']

    if user_filters:
        filtered_results = []
        for res in results:
            meta = res['meta']
            keep = True
            for key, value in user_filters.items():
                if meta.get(key) != value:
                    keep = False
                    break
            if keep:
                filtered_results.append(res)
    else:
        filtered_results = results

    if not filtered_results:
        return await message.edit("`No results match the selected filters.`")

    buttons = build_dynamic_ui(filtered_results, search_key, user_filters)

    total = len(filtered_results)
    file_list_text = []
    for i, res in enumerate(filtered_results[:10]):
        file_name = res['file'].get('file_name', 'Unknown File')
        file_list_text.append(f"**{i+1}.** `{file_name}` - `Score: {res['score']:.2f}`")

    text = f"**Total Results:** `{total}`\n\n" + "\n".join(file_list_text)

    await message.edit(text, reply_markup=InlineKeyboardMarkup(buttons))


def build_dynamic_ui(results, search_key, user_filters):
    buttons = []
    seasons, episodes, languages, years = defaultdict(int), defaultdict(int), defaultdict(int), defaultdict(int)

    season_filter = user_filters.get('s')

    for res in results:
        meta = res['meta']
        if meta.get('season'):
            seasons[meta['season']] += 1
        if season_filter and meta.get('season') == season_filter and meta.get('episode'):
            episodes[meta['episode']] += 1
        if meta.get('year'):
            years[meta['year']] += 1
        if meta.get('language'):
            languages[meta['language']] += 1

    filter_row = []
    if seasons:
        filter_row.append(InlineKeyboardButton(f"📺 Seasons ({len(seasons)})", callback_data=f"ft_s#{search_key}"))
    if years and not seasons:
        filter_row.append(InlineKeyboardButton(f"🎬 Years ({len(years)})", callback_data=f"ft_y#{search_key}"))
    if languages:
        filter_row.append(InlineKeyboardButton(f"🌐 Languages ({len(languages)})", callback_data=f"ft_l#{search_key}"))
    if episodes:
        filter_row.append(InlineKeyboardButton(f"🎬 Episodes ({len(episodes)})", callback_data=f"ft_e#{search_key}"))

    if filter_row:
        buttons.append(filter_row)

    active_filters_row = []
    if 's' in user_filters:
        active_filters_row.append(InlineKeyboardButton(f"✅ S{user_filters['s']:02d}", callback_data=f"ft_s#{search_key}"))
    if 'e' in user_filters:
        active_filters_row.append(InlineKeyboardButton(f"✅ E{user_filters['e']:02d}", callback_data=f"ft_e#{search_key}"))
    if 'y' in user_filters:
        active_filters_row.append(InlineKeyboardButton(f"✅ {user_filters['y']}", callback_data=f"ft_y#{search_key}"))
    if 'l' in user_filters:
        active_filters_row.append(InlineKeyboardButton(f"✅ {user_filters['l'].title()}", callback_data=f"ft_l#{search_key}"))

    if active_filters_row:
        buttons.append(active_filters_row)
        buttons.append([InlineKeyboardButton("🔄 Reset Filters", callback_data=f"flt_reset#{search_key}")])

    return buttons


@Client.on_callback_query(filters.regex(r"^ft_"))
async def on_filter_type_cb(client, query):
    _, filter_type, search_key = query.data.split('#')
    cached_data = temp.CACHED_RESULTS.get(search_key)
    if not cached_data: return await query.answer("Search expired.", show_alert=True)

    results = cached_data['results']
    user_filters = cached_data['user_filters']

    options = defaultdict(int)
    if filter_type == 's':
        for res in results:
            if res['meta']['season']: options[res['meta']['season']] += 1
    elif filter_type == 'y':
        for res in results:
            if res['meta']['year']: options[res['meta']['year']] += 1
    elif filter_type == 'l':
        for res in results:
            if res['meta']['language']: options[res['meta']['language']] += 1
    elif filter_type == 'e':
        season_filter = user_filters.get('s')
        if not season_filter: return await query.answer("Please select a season first.", show_alert=True)
        for res in results:
            if res['meta'].get('season') == season_filter and res['meta'].get('episode'):
                options[res['meta']['episode']] += 1

    buttons = []
    row = []
    for key, count in sorted(options.items()):
        label = f"S{key:02d}" if filter_type == 's' else f"E{key:02d}" if filter_type == 'e' else str(key).title()
        row.append(InlineKeyboardButton(f"{label} ({count})", callback_data=f"flt_{filter_type}#{search_key}#{key}"))
        if len(row) >= 3:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    buttons.append([InlineKeyboardButton("⬅️ Back", callback_data=f"back_{search_key}")])
    await query.message.edit_reply_markup(InlineKeyboardMarkup(buttons))


@Client.on_callback_query(filters.regex(r"^(flt_|back_)"))
async def on_filter_value_cb(client, query):
    if query.data.startswith('back_'):
        search_key = query.data.split('_')[1]
        return await display_results(query.message, search_key)

    _, filter_type_val = query.data.split('#', 1)
    filter_type, search_key, value = filter_type_val.split('#', 2)

    cached_data = temp.CACHED_RESULTS.get(search_key)
    if not cached_data: return await query.answer("Search expired.", show_alert=True)

    if filter_type == 'reset':
        cached_data['user_filters'] = {}
    else:
        try: value = int(value)
        except ValueError: pass
        cached_data['user_filters'][filter_type] = value
        if filter_type == 's':
            cached_data['user_filters'].pop('e', None)

    await display_results(query.message, search_key)
