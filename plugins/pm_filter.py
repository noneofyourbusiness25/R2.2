# Don't Remove Credit @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot @Tech_VJ
# Ask Doubt on telegram @KingVJ01

import os, logging, string, asyncio, time, re, ast, random, math, pytz, pyrogram, base64
from datetime import datetime, timedelta, date, time
from Script import script
from info import *
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, InputMediaPhoto, ChatPermissions, WebAppInfo
from pyrogram import Client, filters, enums
from pyrogram.errors import FloodWait, UserIsBlocked, MessageNotModified, PeerIdInvalid
from pyrogram.errors.exceptions.bad_request_400 import MediaEmpty, PhotoInvalidDimensions, WebpageMediaEmpty
from utils import get_size, is_subscribed, pub_is_subscribed, get_poster, search_gagala, temp, get_settings, save_group_settings, get_shortlink, get_tutorial, send_all, get_cap
from database.users_chats_db import db
from database.ia_filterdb import col, sec_col, db as vjdb, sec_db, get_file_details, get_search_results, get_bad_files, LANGUAGES
from database.filters_mdb import del_all, find_filter, get_filters
from database.connections_mdb import mydb, active_connection, all_connections, delete_connection, if_active, make_active, make_inactive
from database.gfilters_mdb import find_gfilter, get_gfilters, del_allg
from urllib.parse import quote_plus
from TechVJ.util.file_properties import get_name, get_hash, get_media_file_size

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
lock = asyncio.Lock()

BUTTON = {}
BUTTONS = {}
BUTTONS0 = {}
BUTTONS1 = {}
BUTTONS2 = {}
temp.ACTIVE_SEARCHES = {}

def parse_s_e_from_name(name):
    """Parses season and episode numbers from a file name."""
    name = name.lower()
    # Regular expression to find SxxExx or Sxx EPxx patterns
    match = re.search(r'\b(s|season)\s?(\d{1,2})[\s\._-]*(e|ep|episode)\s?(\d{1,3})\b', name)
    if match:
        return int(match.group(2)), int(match.group(4))
    # Fallback for Sxx only
    match = re.search(r'\b(s|season)\s?(\d{1,2})\b', name)
    if match:
        return int(match.group(2)), None
    return None, None

def calculate_match_score(file_name, query):
    """
    Calculates a score based on how closely the file name matches the query.
    Lower scores are better.
    """
    # Define stop words to ignore in the file name
    stop_words = [
        '1080p', '720p', '480p', 'bluray', 'x264', 'x265', 'webrip', 'hdrip',
        'hdcam', 'dvdrip', 'dual', 'audio', 'multi'
    ]
    # Add all language tokens from the LANGUAGES dict to stop words
    for lang_tokens in LANGUAGES.values():
        stop_words.extend(lang_tokens)

    # Clean the file name
    # Remove S/E and year patterns
    name = re.sub(r'\b(s|season)\s?\d{1,2}[\s\._-]*(e|ep|episode)\s?\d{1,3}\b', '', file_name, flags=re.IGNORECASE)
    name = re.sub(r'\b(19|20)\d{2}\b', '', name)
    # Remove any characters that are not letters, numbers, or spaces
    name = re.sub(r'[^\w\s]', '', name)

    # Tokenize and filter out stop words
    name_words = [word for word in name.lower().split() if word not in stop_words and not word.isdigit()]

    # Clean and tokenize the query
    query_words = query.lower().split()

    # Calculate the score as the number of extra words in the file name
    score = len(name_words) - len(query_words)

    # We only want to penalize extra words, so the score cannot be negative
    return max(0, score)


@Client.on_message(filters.group & filters.text & filters.incoming)
async def give_filter(client, message):
    if message.chat.id != SUPPORT_CHAT_ID:
        settings = await get_settings(message.chat.id)
        chatid = message.chat.id
        user_id = message.from_user.id if message.from_user else 0
        if settings.get('fsub') != None:
            try:
                btn = await pub_is_subscribed(client, message, settings['fsub'])
                if btn:
                    btn.append([InlineKeyboardButton("Unmute Me 🔕", callback_data=f"unmuteme#{int(user_id)}")])
                    await client.restrict_chat_member(chatid, message.from_user.id, ChatPermissions(can_send_messages=False))
                    await message.reply_photo(photo=random.choice(PICS), caption=f"👋 Hello {message.from_user.mention},\n\nPlease join the channel then click on unmute me button. 😇", reply_markup=InlineKeyboardMarkup(btn), parse_mode=enums.ParseMode.HTML)
                    return
            except Exception as e:
                print(e)

        manual = await manual_filters(client, message)
        if manual == False:
            settings = await get_settings(message.chat.id)
            try:
                if settings.get('auto_ffilter'):
                    ai_search = True
                    reply_msg = await message.reply_text(f"<b><i>Searching For {message.text} 🔍</i></b>")
                    await auto_filter(client, message.text, message, reply_msg, ai_search)
            except Exception as e:
                logger.exception(f"[GIVE_FILTER] An unexpected error occurred: {e}")
    else: #a better logic to avoid repeated lines of code in auto_filter function
        search = message.text
        logger.info(f"Support group quick count | chat_id={message.chat.id} | query='{search.lower()}'")
        temp_files, temp_offset, total_results, _ = await get_search_results(chat_id=message.chat.id, query=search.lower(), offset=0, filter=True)
        if total_results == 0:
            logger.error(f"Support group ZERO RESULTS | chat_id={message.chat.id} | query='{search.lower()}'")
            return
        else:
            logger.info(f"Support group RESULTS | chat_id={message.chat.id} | query='{search.lower()}' | total={total_results}")
            return await message.reply_text(f"<b>Hᴇʏ {message.from_user.mention}, {str(total_results)} ʀᴇsᴜʟᴛs ᴀʀᴇ ғᴏᴜɴᴅ ɪɴ ᴍʏ ᴅᴀᴛᴀʙᴀsᴇ ғᴏʀ ʏᴏᴜʀ ᴏ̨ᴜᴇʀʏ {search}. \n\nTʜɪs ɪs ᴀ sᴜᴘᴘᴏʀᴛ ɢʀᴏᴜᴘ sᴏ ᴛʜᴀᴛ ʏᴏᴜ ᴄᴀɴ'ᴛ ɢᴇᴛ ғɪʟᴇs ғʀᴏᴍ ʜᴇʀᴇ...\n\nJᴏɪɴ ᴀɴᴅ Sᴇᴀʀᴄʜ Hᴇʀᴇ - {GRP_LNK}</b>")

@Client.on_message(filters.private & filters.text & filters.incoming)
async def pm_text(bot, message):
    content = message.text
    user = message.from_user.first_name
    user_id = message.from_user.id
    if content.startswith("/") or content.startswith("#"): return  # ignore commands and hashtags
    if PM_SEARCH == True:
        ai_search = True
        reply_msg = await bot.send_message(message.from_user.id, f"<b><i>Searching For {content} 🔍</i></b>", reply_to_message_id=message.id)
        await auto_filter(bot, content, message, reply_msg, ai_search)

@Client.on_callback_query(filters.regex(r"^next"))
async def next_page(bot, query):
    ident, req, key, offset = query.data.split("_")
    try:
        offset = int(offset)
    except:
        offset = 0

    search = temp.ACTIVE_SEARCHES.get(key)
    if not search:
        return await query.answer("⚠️ This button has expired.", show_alert=True)

    files, n_offset, total, _ = await get_search_results(query.message.chat.id, search, offset=offset, filter=True)
    if not files:
        return await query.answer("No more files found on this page.", show_alert=True)

    # Score and sort the files
    scored_files = []
    for file in files:
        file_name = file.get("file_name", "")
        score = calculate_match_score(file_name, search) # Use `search` which is the clean query from ACTIVE_SEARCHES
        scored_files.append({'file': file, 'score': score})

    scored_files.sort(key=lambda x: x['score'])
    files = [item['file'] for item in scored_files]

    temp.GETALL[key] = files

    btn = []
    for file in files:
        file_id = file.get("file_id")
        title = file.get("file_name", "Unknown Title")
        size = get_size(file.get("file_size", 0))

        season, episode = parse_s_e_from_name(title)
        s_e_info = ""
        if season is not None:
            s_e_info = f"S{season:02d}"
            if episode is not None:
                s_e_info += f"E{episode:02d}"

        button_text = f"[{size}]"
        if s_e_info:
            button_text += f" [{s_e_info}]"
        button_text += f" {title}"

        btn.append([InlineKeyboardButton(text=button_text, callback_data=f"file#{file_id}")])

    if n_offset:
        btn.append([
            InlineKeyboardButton("⌫ ʙᴀᴄᴋ", callback_data=f"next_0_{key}_{int(offset)-10}" if offset else f"next_0_{key}_0"),
            InlineKeyboardButton(f"{math.ceil(int(offset)/10)+1} / {math.ceil(total/10)}", callback_data="pages"),
            InlineKeyboardButton("ɴᴇxᴛ ➪", callback_data=f"next_0_{key}_{n_offset}")
        ])

    btn.append([InlineKeyboardButton("🔎 Filter Results", callback_data=f"filter_results#{key}")])

    try:
        await query.message.edit_text(
            text=f"<b>Here are the results for your query.\nThis message will self-destruct in 10 minutes for privacy.</b>",
            reply_markup=InlineKeyboardMarkup(btn)
        )
    except MessageNotModified:
        pass

@Client.on_callback_query(filters.regex(r"^filter_results#"))
async def filter_results_cb_handler(client: Client, query: CallbackQuery):
    _, key = query.data.split("#")
    btn = [
        [InlineKeyboardButton("🎬 Movies", callback_data=f"movies#{key}")],
        [InlineKeyboardButton("📺 Series", callback_data=f"series#{key}")],
        [InlineKeyboardButton("⬅️ Back", callback_data=f"next_0_{key}_0")]
    ]
    await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(btn))

# Movies Flow
@Client.on_callback_query(filters.regex(r"^movies#"))
async def movies_cb_handler(client: Client, query: CallbackQuery):
    try:
        _, key, page = query.data.split("#")
        page = int(page)
    except:
        _, key = query.data.split("#")
        page = 1

    years_per_page = 18
    years = [str(y) for y in range(date.today().year, 1899, -1)]
    start_index = (page - 1) * years_per_page
    end_index = start_index + years_per_page
    page_years = years[start_index:end_index]

    btn = [InlineKeyboardButton(f"🗓️ {year}", callback_data=f"year#{year}#{key}") for year in page_years]
    btn = [btn[i:i+3] for i in range(0, len(btn), 3)]

    pagination_buttons = []
    if page > 1:
        pagination_buttons.append(InlineKeyboardButton("« Back", callback_data=f"movies#{key}#{page-1}"))
    if end_index < len(years):
        pagination_buttons.append(InlineKeyboardButton("Next »", callback_data=f"movies#{key}#{page+1}"))
    if pagination_buttons:
        btn.append(pagination_buttons)

    btn.append([InlineKeyboardButton("⬅️ Back", callback_data=f"filter_results#{key}")])
    await query.edit_message_text("Select Year:", reply_markup=InlineKeyboardMarkup(btn))

@Client.on_callback_query(filters.regex(r"^year#"))
async def year_select_cb_handler(client: Client, query: CallbackQuery):
    _, year, key = query.data.split("#")

    buttons = [
        InlineKeyboardButton(f"🌐 {lang.capitalize()}", callback_data=f"lang#{lang}#movie#{year}#None#{key}")
        for lang in LANGUAGES
    ]
    btn = [buttons[i:i+2] for i in range(0, len(buttons), 2)]
    btn.append([InlineKeyboardButton("⬅️ Back", callback_data=f"movies#{key}")])
    await query.edit_message_text("Select Language:", reply_markup=InlineKeyboardMarkup(btn))

# Series Flow
@Client.on_callback_query(filters.regex(r"^series#"))
async def series_cb_handler(client: Client, query: CallbackQuery):
    _, key = query.data.split("#")
    seasons = [str(s) for s in range(1, 21)]
    btn = [InlineKeyboardButton(f"📁 Season {s}", callback_data=f"season#{s}#{key}") for s in seasons]
    btn = [btn[i:i+2] for i in range(0, len(btn), 2)]
    btn.append([InlineKeyboardButton("⬅️ Back", callback_data=f"filter_results#{key}")])
    await query.edit_message_text("Select Season:", reply_markup=InlineKeyboardMarkup(btn))

@Client.on_callback_query(filters.regex(r"^season#"))
async def season_select_cb_handler(client: Client, query: CallbackQuery):
    _, season, key = query.data.split("#")
    episodes = [str(e) for e in range(1, 21)] # Assuming max 20 episodes
    btn = [InlineKeyboardButton(f"Episode {e}", callback_data=f"episode#{season}#{e}#{key}") for e in episodes]
    btn = [btn[i:i+3] for i in range(0, len(btn), 3)]
    btn.append([InlineKeyboardButton("⬅️ Back", callback_data=f"series#{key}")])
    await query.edit_message_text("Select Episode:", reply_markup=InlineKeyboardMarkup(btn))

@Client.on_callback_query(filters.regex(r"^episode#"))
async def episode_select_cb_handler(client: Client, query: CallbackQuery):
    _, season, episode, key = query.data.split("#")

    buttons = [
        InlineKeyboardButton(f"🌐 {lang.capitalize()}", callback_data=f"lang#{lang}#series#{season}#{episode}#{key}")
        for lang in LANGUAGES
    ]
    btn = [buttons[i:i+2] for i in range(0, len(buttons), 2)]
    btn.append([InlineKeyboardButton("⬅️ Back", callback_data=f"season#{season}#{key}")])
    await query.edit_message_text("Select Language:", reply_markup=InlineKeyboardMarkup(btn))

# Final handler
@Client.on_callback_query(filters.regex(r"^lang#"))
async def lang_select_cb_handler(client: Client, query, lang=None, media_type=None, media_filter=None, media_filter2=None):
    if lang is None: # Called from button
        try:
            _, lang, media_type, media_filter, media_filter2, key = query.data.split("#")
        except:
            _, lang, media_type, media_filter, key = query.data.split("#")
            media_filter2 = "None"
    else: # Called directly
        key = query.data.split("#")[-1]

    search = temp.ACTIVE_SEARCHES.get(key)
    if not search:
        return await query.answer("⚠️ This button has expired.", show_alert=True)

    if media_type == "movie":
        search_query = f"{search} {media_filter} {lang}" # media_filter is year
    else: # series
        search_query = f"{search} s{int(media_filter):02d}e{int(media_filter2):02d} {lang}" # media_filter is season, media_filter2 is episode

    files, offset, total_results, clean_query = await get_search_results(query.message.chat.id, search_query, offset=0, filter=True)
    if not files:
        return await query.answer("🚫 𝗡𝗼 𝗙𝗶𝗹𝗲 𝗪𝗲𝗿𝗲 𝗙𝗼𝘂𝗻𝗱 🚫", show_alert=1)

    await auto_filter(client, search_query, query, query.message, True, spoll=(search_query, files, offset, total_results, clean_query))

async def spell_check_helper(client, message, reply_msg):
    query = message.text
    suggestions = await search_gagala(query)
    if not suggestions:
        return await reply_msg.edit("🤷‍♂️ No results found 🤷‍♂️")
    btn = [
        [InlineKeyboardButton(s.title(), callback_data=f"spol#{message.from_user.id}#{base64.urlsafe_b64encode(s.encode()).decode()}")]
        for s in suggestions[:5]
    ]
    btn.append([InlineKeyboardButton("Close", callback_data=f"spol#{message.from_user.id}#close_spellcheck")])
    await reply_msg.edit("I couldn't find anything for that. Did you mean one of these?", reply_markup=InlineKeyboardMarkup(btn))

async def auto_filter(client, msg, message, reply_msg, ai_search, spoll=None):
    if spoll:
        search, files, offset, total_results, clean_query = spoll
    else:
        search = msg
        files, offset, total_results, clean_query = await get_search_results(message.chat.id, search, offset=0, filter=True)

    if not files:
        if SPELL_CHECK_REPLY:
            return await spell_check_helper(client, message, reply_msg)
        else:
            return await reply_msg.edit("🤷‍♂️ No results found 🤷‍♂️")

    key = os.urandom(6).hex()
    temp.ACTIVE_SEARCHES[key] = clean_query

    # Score and sort the files
    scored_files = []
    for file in files:
        file_name = file.get("file_name", "")
        score = calculate_match_score(file_name, clean_query)
        scored_files.append({'file': file, 'score': score})

    scored_files.sort(key=lambda x: x['score'])
    files = [item['file'] for item in scored_files]

    temp.GETALL[key] = files

    btn = []
    for file in files:
        file_id = file.get("file_id")
        title = file.get("file_name", "Unknown Title")
        size = get_size(file.get("file_size", 0))

        season, episode = parse_s_e_from_name(title)
        s_e_info = ""
        if season is not None:
            s_e_info = f"S{season:02d}"
            if episode is not None:
                s_e_info += f"E{episode:02d}"

        button_text = f"[{size}]"
        if s_e_info:
            button_text += f" [{s_e_info}]"
        button_text += f" {title}"

        btn.append([InlineKeyboardButton(text=button_text, callback_data=f"file#{file_id}")])

    if total_results > len(files):
         btn.append([InlineKeyboardButton("ɴᴇxᴛ ➪", callback_data=f"next_0_{key}_{10}")])

    btn.append([InlineKeyboardButton("🔎 Filter Results", callback_data=f"filter_results#{key}")])

    try:
        await reply_msg.edit_text(
            text=f"<b>Here are the results for your query.\nThis message will self-destruct in 10 minutes for privacy.</b>",
            reply_markup=InlineKeyboardMarkup(btn)
        )
    except Exception as e:
        logger.exception(f"Error editing message in auto_filter: {e}")

async def manual_filters(client, message, text=False):
    group_id = message.chat.id
    name = text or message.text
    reply_id = message.reply_to_message.id if message.reply_to_message else message.id
    keywords = await get_filters(group_id)
    for keyword in reversed(sorted(keywords, key=len)):
        pattern = r"( |^|[^\w])" + re.escape(keyword) + r"( |$|[^\w])"
        if re.search(pattern, name, re.IGNORECASE):
            reply_text, btn, alert, fileid = await find_filter(group_id, keyword)
            if reply_text:
                reply_text = reply_text.replace
            if btn is not None:
                btn = eval(btn)
            if fileid == "None":
                if btn is not None:
                    await client.send_message(group_id, reply_text, reply_markup=InlineKeyboardMarkup(btn), reply_to_message_id=reply_id)
                else:
                    await client.send_message(group_id, reply_text, reply_to_message_id=reply_id)
            else:
                if btn is not None:
                    await client.send_cached_media(group_id, fileid, caption=reply_text, reply_markup=InlineKeyboardMarkup(btn), reply_to_message_id=reply_id)
                else:
                    await client.send_cached_media(group_id, fileid, caption=reply_text, reply_to_message_id=reply_id)
            return True
    return False

async def global_filters(client, message, text=False):
    group_id = message.chat.id
    name = text or message.text
    reply_id = message.reply_to_message.id if message.reply_to_message else message.id
    keywords = await get_gfilters('gfilters')
    for keyword in reversed(sorted(keywords, key=len)):
        pattern = r"( |^|[^\w])" + re.escape(keyword) + r"( |$|[^\w])"
        if re.search(pattern, name, re.IGNORECASE):
            reply_text, btn, alert, fileid = await find_gfilter('gfilters', keyword)
            if reply_text:
                reply_text = reply_text.replace
            if btn is not None:
                btn = eval(btn)
            if fileid == "None":
                if btn is not None:
                    await client.send_message(group_id, reply_text, reply_markup=InlineKeyboardMarkup(btn), reply_to_message_id=reply_id)
                else:
                    await client.send_message(group_id, reply_text, reply_to_message_id=reply_id)
            else:
                if btn is not None:
                    await client.send_cached_media(group_id, fileid, caption=reply_text, reply_markup=InlineKeyboardMarkup(btn), reply_to_message_id=reply_id)
                else:
                    await client.send_cached_media(group_id, fileid, caption=reply_text, reply_to_message_id=reply_id)
            return True
    return False

@Client.on_callback_query(filters.regex(r"^spol"))
async def advantage_spoll_choker(bot, query):
    _, user, encoded_suggestion = query.data.split('#')
    if int(user) != 0 and query.from_user.id != int(user):
        return await query.answer(script.ALRT_TXT.format(query.from_user.first_name), show_alert=True)
    if encoded_suggestion == "close_spellcheck":
        return await query.message.delete()
    movie = base64.urlsafe_b64decode(encoded_suggestion).decode()
    movie = re.sub(r"[:\-]", " ", movie)
    movie = re.sub(r"\s+", " ", movie).strip()
    await query.answer(script.TOP_ALRT_MSG)
    gl = await global_filters(bot, query.message, text=movie)
    if gl == False:
        k = await manual_filters(bot, query.message, text=movie)
        if k == False:
            files, offset, total_results, clean_query = await get_search_results(query.message.chat.id, movie, offset=0, filter=True)
            if files:
                k = (movie, files, offset, total_results, clean_query)
                ai_search = True
                reply_msg = await query.message.edit_text(f"<b><i>Searching For {movie} 🔍</i></b>")
                await auto_filter(bot, movie, query, reply_msg, ai_search, k)
            else:
                reqstr1 = query.from_user.id if query.from_user else 0
                reqstr = await bot.get_users(reqstr1)
                if NO_RESULTS_MSG:
                    await bot.send_message(chat_id=LOG_CHANNEL, text=(script.NORSLTS.format(reqstr.id, reqstr.mention, movie)))
                k = await query.message.edit(script.MVE_NT_FND)
                await asyncio.sleep(10)
                await k.delete()

@Client.on_callback_query()
async def cb_handler(client: Client, query: CallbackQuery):
    if query.data == "close_data":
        await query.message.delete()
    elif query.data == "get_trail":
        user_id = query.from_user.id
        free_trial_status = await db.get_free_trial_status(user_id)
        if not free_trial_status:
            await db.give_free_trail(user_id)
            new_text = "**ʏᴏᴜ ᴄᴀɴ ᴜsᴇ ꜰʀᴇᴇ ᴛʀᴀɪʟ ꜰᴏʀ 5 ᴍɪɴᴜᴛᴇs ꜰʀᴏᴍ ɴᴏᴡ 😀\n\nआप अब से 5 मिनट के लिए निःशुल्क ट्रायल का उपयोग कर सकते हैं 😀**"
            await query.message.edit_text(text=new_text)
            return
        else:
            new_text= "**🤣 you already used free now no more free trail. please buy subscription here are our 👉 /plans**"
            await query.message.edit_text(text=new_text)
            return
    elif query.data == "buy_premium":
        btn = [[InlineKeyboardButton("✅sᴇɴᴅ ʏᴏᴜʀ ᴘᴀʏᴍᴇɴᴛ ʀᴇᴄᴇɪᴘᴛ ʜᴇʀᴇ ✅", url = OWNER_LINK)] for admin in ADMINS]
        btn.append([InlineKeyboardButton("⚠️ᴄʟᴏsᴇ / ᴅᴇʟᴇᴛᴇ⚠️", callback_data="close_data")])
        reply_markup = InlineKeyboardMarkup(btn)
        await query.message.reply_photo(photo=PAYMENT_QR, caption=PAYMENT_TEXT, reply_markup=reply_markup)
        return
    elif query.data == "gfiltersdeleteallconfirm":
        await del_allg(query.message, 'gfilters')
        await query.answer("Done !")
        return
    elif query.data == "gfiltersdeleteallcancel":
        await query.message.reply_to_message.delete()
        await query.message.delete()
        await query.answer("Process Cancelled !")
        return
    elif query.data == "delallconfirm":
        userid = query.from_user.id
        chat_type = query.message.chat.type
        if chat_type == enums.ChatType.PRIVATE:
            grpid = await active_connection(str(userid))
            if grpid is not None:
                grp_id = grpid
                try:
                    chat = await client.get_chat(grpid)
                    title = chat.title
                except:
                    await query.message.edit_text("Mᴀᴋᴇ sᴜʀᴇ I'ᴍ ᴘʀᴇsᴇɴᴛ ɪɴ ʏᴏᴜʀ ɢʀᴏᴜᴘ!!", quote=True)
                    return await query.answer(MSG_ALRT)
            else:
                await query.message.edit_text("I'ᴍ ɴᴏᴛ ᴄᴏɴɴᴇᴄᴛᴇᴅ ᴛᴏ ᴀɴʏ ɢʀᴏᴜᴘs!\nCʜᴇᴄᴋ /connections ᴏʀ ᴄᴏɴɴᴇᴄᴛ ᴛᴏ ᴀɴʏ ɢʀᴏᴜᴘs", quote=True)
                return await query.answer(MSG_ALRT)
        elif chat_type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
            grp_id = query.message.chat.id
            title = query.message.chat.title
        else:
            return await query.answer(MSG_ALRT)
        st = await client.get_chat_member(grp_id, userid)
        if (st.status == enums.ChatMemberStatus.OWNER) or (str(userid) in ADMINS):
            await del_all(query.message, grp_id, title)
        else:
            await query.answer("Yᴏᴜ ɴᴇᴇᴅ ᴛᴏ ʙᴇ Gʀᴏᴜᴘ Oᴡɴᴇʀ ᴏʀ ᴀɴ Aᴜᴛʜ Usᴇʀ ᴛᴏ ᴅᴏ ᴛʜᴀᴛ!", show_alert=True)
    elif query.data == "delallcancel":
        userid = query.from_user.id
        chat_type = query.message.chat.type
        if chat_type == enums.ChatType.PRIVATE:
            await query.message.reply_to_message.delete()
            await query.message.delete()
        elif chat_type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
            grp_id = query.message.chat.id
            st = await client.get_chat_member(grp_id, userid)
            if (st.status == enums.ChatMemberStatus.OWNER) or (str(userid) in ADMINS):
                await query.message.delete()
                try:
                    await query.message.reply_to_message.delete()
                except:
                    pass
            else:
                await query.answer("Tʜᴀᴛ's ɴᴏᴛ ғᴏʀ ʏᴏᴜ!!", show_alert=True)
    elif "groupcb" in query.data:
        await query.answer()
        group_id = query.data.split(":")[1]
        act = query.data.split(":")[2]
        hr = await client.get_chat(int(group_id))
        title = hr.title
        user_id = query.from_user.id
        if act == "":
            stat = "CONNECT"
            cb = "connectcb"
        else:
            stat = "DISCONNECT"
            cb = "disconnect"
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton(f"{stat}", callback_data=f"{cb}:{group_id}"), InlineKeyboardButton("DELETE", callback_data=f"deletecb:{group_id}")], [InlineKeyboardButton("BACK", callback_data="backcb")]])
        await query.message.edit_text(f"Gʀᴏᴜᴘ Nᴀᴍᴇ : **{title}**\nGʀᴏᴜᴘ ID : `{group_id}`", reply_markup=keyboard, parse_mode=enums.ParseMode.MARKDOWN)
        return await query.answer(MSG_ALRT)
    elif "connectcb" in query.data:
        await query.answer()
        group_id = query.data.split(":")[1]
        hr = await client.get_chat(int(group_id))
        title = hr.title
        user_id = query.from_user.id
        mkact = await make_active(str(user_id), str(group_id))
        if mkact:
            await query.message.edit_text(f"Cᴏɴɴᴇᴄᴛᴇᴅ ᴛᴏ **{title}**", parse_mode=enums.ParseMode.MARKDOWN)
        else:
            await query.message.edit_text('Sᴏᴍᴇ ᴇʀʀᴏʀ ᴏᴄᴄᴜʀʀᴇᴅ!!', parse_mode=enums.ParseMode.MARKDOWN)
        return await query.answer(MSG_ALRT)
    elif "disconnect" in query.data:
        await query.answer()
        group_id = query.data.split(":")[1]
        hr = await client.get_chat(int(group_id))
        title = hr.title
        user_id = query.from_user.id
        mkinact = await make_inactive(str(user_id))
        if mkinact:
            await query.message.edit_text(f"Dɪsᴄᴏɴɴᴇᴄᴛᴇᴅ ғʀᴏᴍ **{title}**", parse_mode=enums.ParseMode.MARKDOWN)
        else:
            await query.message.edit_text(f"Sᴏᴍᴇ ᴇʀʀᴏʀ ᴏᴄᴄᴜʀʀᴇᴅ!!", parse_mode=enums.ParseMode.MARKDOWN)
        return await query.answer(MSG_ALRT)
    elif "deletecb" in query.data:
        await query.answer()
        user_id = query.from_user.id
        group_id = query.data.split(":")[1]
        delcon = await delete_connection(str(user_id), str(group_id))
        if delcon:
            await query.message.edit_text("Sᴜᴄᴄᴇssғᴜʟʟʏ ᴅᴇʟᴇᴛᴇᴅ ᴄᴏɴɴᴇᴄᴛɪᴏɴ !")
        else:
            await query.message.edit_text(f"Sᴏᴍᴇ ᴇʀʀᴏʀ ᴏᴄᴄᴜʀʀᴇᴅ!!", parse_mode=enums.ParseMode.MARKDOWN)
        return await query.answer(MSG_ALRT)
    elif query.data == "backcb":
        await query.answer()
        userid = query.from_user.id
        groupids = await all_connections(str(userid))
        if groupids is None:
            await query.message.edit_text("Tʜᴇʀᴇ ᴀʀᴇ ɴᴏ ᴀᴄᴛɪᴠᴇ ᴄᴏɴɴᴇᴄᴛɪᴏɴs!! Cᴏɴɴᴇᴄᴛ ᴛᴏ sᴏᴍᴇ ɢʀᴏᴜᴘs ғɪʀsᴛ.")
            return await query.answer(MSG_ALRT)
        buttons = []
        for groupid in groupids:
            try:
                ttl = await client.get_chat(int(groupid))
                title = ttl.title
                active = await if_active(str(userid), str(groupid))
                act = " - ACTIVE" if active else ""
                buttons.append([InlineKeyboardButton(text=f"{title}{act}", callback_data=f"groupcb:{groupid}:{act}")])
            except:
                pass
        if buttons:
            await query.message.edit_text("Yᴏᴜʀ ᴄᴏɴɴᴇᴄᴛᴇᴅ ɢʀᴏᴜᴘ ᴅᴇᴛᴀɪʟs ;\n\n", reply_markup=InlineKeyboardMarkup(buttons))
    elif "gfilteralert" in query.data:
        grp_id = query.message.chat.id
        i = query.data.split(":")[1]
        keyword = query.data.split(":")[2]
        reply_text, btn, alerts, fileid = await find_gfilter('gfilters', keyword)
        if alerts is not None:
            alerts = ast.literal_eval(alerts)
            alert = alerts[int(i)]
            alert = alert.replace("\\n", "\n").replace("\\t", "\t")
            await query.answer(alert, show_alert=True)
    elif "alertmessage" in query.data:
        grp_id = query.message.chat.id
        i = query.data.split(":")[1]
        keyword = query.data.split(":")[2]
        reply_text, btn, alerts, fileid = await find_filter(grp_id, keyword)
        if alerts is not None:
            alerts = ast.literal_eval(alerts)
            alert = alerts[int(i)]
            alert = alert.replace("\\n", "\n").replace("\\t", "\t")
            await query.answer(alert, show_alert=True)
    if query.data.startswith("file"):
        ident, file_id = query.data.split("#")
        files_ = await get_file_details(file_id)
        if not files_:
            return await query.answer('Nᴏ sᴜᴄʜ ғɪʟᴇ ᴇxɪsᴛ.')
        files = files_
        title = files["file_name"]
        size = get_size(files["file_size"])
        f_caption = files["caption"]
        settings = await get_settings(query.message.chat.id)
        if CUSTOM_FILE_CAPTION:
            try:
                f_caption = CUSTOM_FILE_CAPTION.format(file_name='' if title is None else title, file_size='' if size is None else size, file_caption='' if f_caption is None else f_caption)
            except Exception as e:
                logger.exception(e)
            f_caption = f_caption
        if f_caption is None:
            f_caption = f"{files['file_name']}"
        try:
            if settings['is_shortlink'] and not await db.has_premium_access(query.from_user.id):
                temp.SHORT[query.from_user.id] = query.message.chat.id
                await query.answer(url=f"https://telegram.me/{temp.U_NAME}?start=short_{file_id}")
            else:
                await query.answer(url=f"https://telegram.me/{temp.U_NAME}?start={ident}_{file_id}")
        except UserIsBlocked:
            await query.answer('Uɴʙʟᴏᴄᴋ ᴛʜᴇ ʙᴏᴛ ᴍᴀʜɴ !', show_alert=True)
        except PeerIdInvalid:
            await query.answer(url=f"https://telegram.me/{temp.U_NAME}?start={ident}_{file_id}")
        except Exception as e:
            await query.answer(url=f"https://telegram.me/{temp.U_NAME}?start={ident}_{file_id}")
    elif query.data.startswith("sendfiles"):
        ident, key = query.data.split("#")
        settings = await get_settings(query.message.chat.id)
        pre = 'allfilesp' if settings['file_secure'] else 'allfiles'
        try:
            if settings['is_shortlink'] and not await db.has_premium_access(query.from_user.id):
                await query.answer(url=f"https://telegram.me/{temp.U_NAME}?start=sendfiles1_{key}")
            else:
                await query.answer(url=f"https://telegram.me/{temp.U_NAME}?start={pre}_{key}")
        except UserIsBlocked:
            await query.answer('Uɴʙʟᴏᴄᴋ ᴛʜᴇ ʙᴏᴛ ᴍᴀʜɴ !', show_alert=True)
        except PeerIdInvalid:
            await query.answer(url=f"https://telegram.me/{temp.U_NAME}?start=sendfiles3_{key}")
        except Exception as e:
            logger.exception(e)
            await query.answer(url=f"https://telegram.me/{temp.U_NAME}?start=sendfiles4_{key}")
    elif query.data.startswith("unmuteme"):
        ident, userid = query.data.split("#")
        user_id = query.from_user.id
        settings = await get_settings(int(query.message.chat.id))
        if userid == 0:
            return await query.answer("You are anonymous admin !", show_alert=True)
        try:
            btn = await pub_is_subscribed(client, query, settings['fsub'])
            if btn:
                await query.answer("Kindly Join Given Channel Then Click On Unmute Button", show_alert=True)
            else:
                await client.unban_chat_member(query.message.chat.id, user_id)
                await query.answer("Unmuted Successfully !", show_alert=True)
                await query.message.delete()
        except:
            await query.answer("Not For Your My Dear", show_alert=True)
    elif query.data.startswith("del"):
        ident, file_id = query.data.split("#")
        files_ = await get_file_details(file_id)
        if not files_:
            return await query.answer('Nᴏ sᴜᴄʜ ғɪʟᴇ ᴇxɪsᴛ.')
        await query.answer(url=f"https://telegram.me/{temp.U_NAME}?start=file_{file_id}")
    elif query.data.startswith("checksub"):
        if AUTH_CHANNEL and not await is_subscribed(client, query):
            return await query.answer("Jᴏɪɴ ᴏᴜʀ Bᴀᴄᴋ-ᴜᴘ ᴄʜᴀɴɴᴇʟ ᴍᴀʜɴ! 😒", show_alert=True)
        ident, kk, file_id = query.data.split("#")
        await query.answer(url=f"https://t.me/{temp.U_NAME}?start={kk}_{file_id}")
    elif query.data == "pages":
        await query.answer()
    elif query.data.startswith("send_fsall"):
        temp_var, ident, key, offset = query.data.split("#")
        search = BUTTON0.get(key)
        files, n_offset, total, _ = await get_search_results(query.message.chat.id, search, offset=int(offset), filter=True)
        await send_all(client, query.from_user.id, files, ident, query.message.chat.id, query.from_user.first_name, query)
        search = BUTTONS1.get(key)
        files, n_offset, total, _ = await get_search_results(query.message.chat.id, search, offset=int(offset), filter=True)
        await send_all(client, query.from_user.id, files, ident, query.message.chat.id, query.from_user.first_name, query)
        search = BUTTONS2.get(key)
        files, n_offset, total, _ = await get_search_results(query.message.chat.id, search, offset=int(offset), filter=True)
        await send_all(client, query.from_user.id, files, ident, query.message.chat.id, query.from_user.first_name, query)
        await query.answer(f"Hey {query.from_user.first_name}, All files on this page has been sent successfully to your PM !", show_alert=True)
    elif query.data.startswith("send_fall"):
        temp_var, ident, key, offset = query.data.split("#")
        search = FRESH.get(key)
        files, n_offset, total, _ = await get_search_results(query.message.chat.id, search, offset=int(offset), filter=True)
        await send_all(client, query.from_user.id, files, ident, query.message.chat.id, query.from_user.first_name, query)
        await query.answer(f"Hey {query.from_user.first_name}, All files on this page has been sent successfully to your PM !", show_alert=True)
    elif query.data.startswith("killfilesdq"):
        ident, keyword = query.data.split("#")
        files, total = await get_bad_files(keyword)
        await query.message.edit_text("<b>File deletion process will start in 5 seconds !</b>")
        await asyncio.sleep(5)
        deleted = 0
        async with lock:
            try:
                for file in files:
                    file_ids = file["file_id"]
                    file_name = file["file_name"]
                    result = col.delete_one({'file_id': file_ids})
                    if not result.deleted_count:
                        result = sec_col.delete_one({'file_id': file_ids})
                    if result.deleted_count:
                        logger.info(f'File Found for your query {keyword}! Successfully deleted {file_name} from database.')
                    deleted += 1
                    if deleted % 50 == 0:
                        await query.message.edit_text(f"<b>Process started for deleting files from DB. Successfully deleted {str(deleted)} files from DB for your query {keyword} !\n\nPlease wait...</b>")
            except Exception as e:
                logger.exception(e)
                await query.message.edit_text(f'Error: {e}')
            else:
                await query.message.edit_text(f"<b>Process Completed for file deletion !\n\nSuccessfully deleted {str(deleted)} files from database for your query {keyword}.</b>")
    elif query.data.startswith("opnsetgrp"):
        ident, grp_id = query.data.split("#")
        userid = query.from_user.id if query.from_user else None
        st = await client.get_chat_member(grp_id, userid)
        if (st.status != enums.ChatMemberStatus.ADMINISTRATOR and st.status != enums.ChatMemberStatus.OWNER and str(userid) not in ADMINS):
            return await query.answer("Yᴏᴜ Dᴏɴ'ᴛ Hᴀᴠᴇ Tʜᴇ Rɪɢʜᴛs Tᴏ Dᴏ Tʜɪs !", show_alert=True)
        title = query.message.chat.title
        settings = await get_settings(grp_id)
        if settings is not None:
            buttons = [[InlineKeyboardButton('Rᴇsᴜʟᴛ Pᴀɢᴇ', callback_data=f'setgs#button#{settings["button"]}#{str(grp_id)}'), InlineKeyboardButton('Bᴜᴛᴛᴏɴ' if settings["button"] else 'Tᴇxᴛ', callback_data=f'setgs#button#{settings["button"]}#{str(grp_id)}')], [InlineKeyboardButton('Pʀᴏᴛᴇᴄᴛ Cᴏɴᴛᴇɴᴛ', callback_data=f'setgs#file_secure#{settings["file_secure"]}#{str(grp_id)}'), InlineKeyboardButton('✔ Oɴ' if settings["file_secure"] else '✘ Oғғ', callback_data=f'setgs#file_secure#{settings["file_secure"]}#{str(grp_id)}')], [InlineKeyboardButton('Iᴍᴅʙ', callback_data=f'setgs#imdb#{settings["imdb"]}#{str(grp_id)}'), InlineKeyboardButton('✔ Oɴ' if settings["imdb"] else '✘ Oғғ', callback_data=f'setgs#imdb#{settings["imdb"]}#{str(grp_id)}')], [InlineKeyboardButton('Sᴘᴇʟʟ Cʜᴇᴄᴋ', callback_data=f'setgs#spell_check#{settings["spell_check"]}#{str(grp_id)}'), InlineKeyboardButton('✔ Oɴ' if settings["spell_check"] else '✘ Oғғ', callback_data=f'setgs#spell_check#{settings["spell_check"]}#{str(grp_id)}')], [InlineKeyboardButton('Wᴇʟᴄᴏᴍᴇ Msɢ', callback_data=f'setgs#welcome#{settings["welcome"]}#{str(grp_id)}'), InlineKeyboardButton('✔ Oɴ' if settings["welcome"] else '✘ Oғғ', callback_data=f'setgs#welcome#{settings["welcome"]}#{str(grp_id)}')], [InlineKeyboardButton('Aᴜᴛᴏ-Dᴇʟᴇᴛᴇ', callback_data=f'setgs#auto_delete#{settings["auto_delete"]}#{str(grp_id)}'), InlineKeyboardButton('5 Mɪɴs' if settings["auto_delete"] else '✘ Oғғ', callback_data=f'setgs#auto_delete#{settings["auto_delete"]}#{str(grp_id)}')], [InlineKeyboardButton('Aᴜᴛᴏ-Fɪʟᴛᴇʀ', callback_data=f'setgs#auto_ffilter#{settings["auto_ffilter"]}#{str(grp_id)}'), InlineKeyboardButton('✔ Oɴ' if settings["auto_ffilter"] else '✘ Oғғ', callback_data=f'setgs#auto_ffilter#{settings["auto_ffilter"]}#{str(grp_id)}')], [InlineKeyboardButton('Mᴀx Bᴜᴛᴛᴏɴs', callback_data=f'setgs#max_btn#{settings["max_btn"]}#{str(grp_id)}'), InlineKeyboardButton('10' if settings["max_btn"] else f'{MAX_B_TN}', callback_data=f'setgs#max_btn#{settings["max_btn"]}#{str(grp_id)}')], [InlineKeyboardButton('SʜᴏʀᴛLɪɴᴋ', callback_data=f'setgs#is_shortlink#{settings["is_shortlink"]}#{str(grp_id)}'), InlineKeyboardButton('✔ Oɴ' if settings["is_shortlink"] else '✘ Oғғ', callback_data=f'setgs#is_shortlink#{settings["is_shortlink"]}#{str(grp_id)}')]]
            reply_markup = InlineKeyboardMarkup(buttons)
            await query.message.edit_text(text=f"<b>Cʜᴀɴɢᴇ Yᴏᴜʀ Sᴇᴛᴛɪɴɢs Fᴏʀ {title} As Yᴏᴜʀ Wɪsʜ ⚙</b>", disable_web_page_preview=True, parse_mode=enums.ParseMode.HTML)
            await query.message.edit_reply_markup(reply_markup)
    elif query.data.startswith("opnsetpm"):
        ident, grp_id = query.data.split("#")
        userid = query.from_user.id if query.from_user else None
        st = await client.get_chat_member(grp_id, userid)
        if (st.status != enums.ChatMemberStatus.ADMINISTRATOR and st.status != enums.ChatMemberStatus.OWNER and str(userid) not in ADMINS):
            return await query.answer("Yᴏᴜ Dᴏɴ'ᴛ Hᴀᴠᴇ Tʜᴇ Rɪɢʜᴛs Tᴏ Dᴏ Tʜɪs !", show_alert=True)
        title = query.message.chat.title
        settings = await get_settings(grp_id)
        btn2 = [[InlineKeyboardButton("Cʜᴇᴄᴋ PM", url=f"telegram.me/{temp.U_NAME}")]]
        reply_markup = InlineKeyboardMarkup(btn2)
        await query.message.edit_text(f"<b>Yᴏᴜʀ sᴇᴛᴛɪɴɢs ᴍᴇɴᴜ ғᴏʀ {title} ʜᴀs ʙᴇᴇɴ sᴇɴᴛ ᴛᴏ ʏᴏᴜʀ PM</b>")
        await query.message.edit_reply_markup(reply_markup)
        if settings is not None:
            buttons = [[InlineKeyboardButton('Rᴇsᴜʟᴛ Pᴀɢᴇ', callback_data=f'setgs#button#{settings["button"]}#{str(grp_id)}'), InlineKeyboardButton('Bᴜᴛᴛᴏɴ' if settings["button"] else 'Tᴇxᴛ', callback_data=f'setgs#button#{settings["button"]}#{str(grp_id)}')], [InlineKeyboardButton('Pʀᴏᴛᴇᴄᴛ Cᴏɴᴛᴇɴᴛ', callback_data=f'setgs#file_secure#{settings["file_secure"]}#{str(grp_id)}'), InlineKeyboardButton('✔ Oɴ' if settings["file_secure"] else '✘ Oғғ', callback_data=f'setgs#file_secure#{settings["file_secure"]}#{str(grp_id)}')], [InlineKeyboardButton('Iᴍᴅʙ', callback_data=f'setgs#imdb#{settings["imdb"]}#{str(grp_id)}'), InlineKeyboardButton('✔ Oɴ' if settings["imdb"] else '✘ Oғғ', callback_data=f'setgs#imdb#{settings["imdb"]}#{str(grp_id)}')], [InlineKeyboardButton('Sᴘᴇʟʟ Cʜᴇᴄᴋ', callback_data=f'setgs#spell_check#{settings["spell_check"]}#{str(grp_id)}'), InlineKeyboardButton('✔ Oɴ' if settings["spell_check"] else '✘ Oғғ', callback_data=f'setgs#spell_check#{settings["spell_check"]}#{str(grp_id)}')], [InlineKeyboardButton('Wᴇʟᴄᴏᴍᴇ Msɢ', callback_data=f'setgs#welcome#{settings["welcome"]}#{str(grp_id)}'), InlineKeyboardButton('✔ Oɴ' if settings["welcome"] else '✘ Oғғ', callback_data=f'setgs#welcome#{settings["welcome"]}#{str(grp_id)}')], [InlineKeyboardButton('Aᴜᴛᴏ-Dᴇʟᴇᴛᴇ', callback_data=f'setgs#auto_delete#{settings["auto_delete"]}#{str(grp_id)}'), InlineKeyboardButton('5 Mɪɴs' if settings["auto_delete"] else '✘ Oғғ', callback_data=f'setgs#auto_delete#{settings["auto_delete"]}#{str(grp_id)}')], [InlineKeyboardButton('Aᴜᴛᴏ-Fɪʟᴛᴇʀ', callback_data=f'setgs#auto_ffilter#{settings["auto_ffilter"]}#{str(grp_id)}'), InlineKeyboardButton('✔ Oɴ' if settings["auto_ffilter"] else '✘ Oғғ', callback_data=f'setgs#auto_ffilter#{settings["auto_ffilter"]}#{str(grp_id)}')], [InlineKeyboardButton('Mᴀx Bᴜᴛᴛᴏɴs', callback_data=f'setgs#max_btn#{settings["max_btn"]}#{str(grp_id)}'), InlineKeyboardButton('10' if settings["max_btn"] else f'{MAX_B_TN}', callback_data=f'setgs#max_btn#{settings["max_btn"]}#{str(grp_id)}')], [InlineKeyboardButton('SʜᴏʀᴛLɪɴᴋ', callback_data=f'setgs#is_shortlink#{settings["is_shortlink"]}#{str(grp_id)}'), InlineKeyboardButton('✔ Oɴ' if settings["is_shortlink"] else '✘ Oғғ', callback_data=f'setgs#is_shortlink#{settings["is_shortlink"]}#{str(grp_id)}')]]
            reply_markup = InlineKeyboardMarkup(buttons)
            await client.send_message(chat_id=userid, text=f"<b>Cʜᴀɴɢᴇ Yᴏᴜʀ Sᴇᴛᴛɪɴɢs Fᴏʀ {title} As Yᴏᴜʀ Wɪsʜ ⚙</b>", reply_markup=reply_markup, disable_web_page_preview=True, parse_mode=enums.ParseMode.HTML, reply_to_message_id=query.message.id)
    elif query.data.startswith("show_option"):
        ident, from_user = query.data.split("#")
        btn = [[InlineKeyboardButton("Uɴᴀᴠᴀɪʟᴀʙʟᴇ", callback_data=f"unavailable#{from_user}"), InlineKeyboardButton("Uᴘʟᴏᴀᴅᴇᴅ", callback_data=f"uploaded#{from_user}")], [InlineKeyboardButton("Aʟʀᴇᴀᴅʏ Aᴠᴀɪʟᴀʙʟᴇ", callback_data=f"already_available#{from_user}")]]
        btn2 = [[InlineKeyboardButton("Vɪᴇᴡ Sᴛᴀᴛᴜs", url=f"{query.message.link}")]]
        if query.from_user.id in ADMINS:
            user = await client.get_users(from_user)
            reply_markup = InlineKeyboardMarkup(btn)
            await query.message.edit_reply_markup(reply_markup)
            await query.answer("Hᴇʀᴇ ᴀʀᴇ ᴛʜᴇ ᴏᴘᴛɪᴏɴs !")
        else:
            await query.answer("Yᴏᴜ ᴅᴏɴ'ᴛ ʜᴀᴠᴇ sᴜғғɪᴄɪᴀɴᴛ ʀɪɢʜᴛs ᴛᴏ ᴅᴏ ᴛʜɪs !", show_alert=True)
    elif query.data.startswith("unavailable"):
        ident, from_user = query.data.split("#")
        btn = [[InlineKeyboardButton("⚠️ Uɴᴀᴠᴀɪʟᴀʙʟᴇ ⚠️", callback_data=f"unalert#{from_user}")]]
        btn2 = [[InlineKeyboardButton('Jᴏɪɴ Cʜᴀɴɴᴇʟ', url=link.invite_link), InlineKeyboardButton("Vɪᴇᴡ Sᴛᴀᴛᴜs", url=f"{query.message.link}")]]
        if query.from_user.id in ADMINS:
            user = await client.get_users(from_user)
            reply_markup = InlineKeyboardMarkup(btn)
            content = query.message.text
            await query.message.edit_text(f"<b><strike>{content}</strike></b>")
            await query.message.edit_reply_markup(reply_markup)
            await query.answer("Sᴇᴛ ᴛᴏ Uɴᴀᴠᴀɪʟᴀʙʟᴇ !")
            try:
                await client.send_message(chat_id=int(from_user), text=f"<b>Hᴇʏ {user.mention}, Sᴏʀʀʏ Yᴏᴜʀ ʀᴇᴏ̨ᴜᴇsᴛ ɪs ᴜɴᴀᴠᴀɪʟᴀʙʟᴇ. Sᴏ ᴏᴜʀ ᴍᴏᴅᴇʀᴀᴛᴏʀs ᴄᴀɴ'ᴛ ᴜᴘʟᴏᴀᴅ ɪᴛ.</b>", reply_markup=InlineKeyboardMarkup(btn2))
            except UserIsBlocked:
                await client.send_message(chat_id=int(SUPPORT_CHAT_ID), text=f"<b>Hᴇʏ {user.mention}, Sᴏʀʀʏ Yᴏᴜʀ ʀᴇᴏ̨ᴜᴇsᴛ ɪs ᴜɴᴀᴠᴀɪʟᴀʙʟᴇ. Sᴏ ᴏᴜʀ ᴍᴏᴅᴇʀᴀᴛᴏʀs ᴄᴀɴ'ᴛ ᴜᴘʟᴏᴀᴅ ɪᴛ.\n\nNᴏᴛᴇ: Tʜɪs ᴍᴇssᴀɢᴇ ɪs sᴇɴᴛ ᴛᴏ ᴛʜɪs ɢʀᴏᴜᴘ ʙᴇᴄᴀᴜsᴇ ʏᴏᴜ'ᴠᴇ ʙʟᴏᴄᴋᴇᴅ ᴛʜᴇ ʙᴏᴛ. Tᴏ sᴇɴᴅ ᴛʜɪs ᴍᴇssᴀɢᴇ ᴛᴏ ʏᴏᴜʀ PM, Mᴜsᴛ ᴜɴʙʟᴏᴄᴋ ᴛʜᴇ ʙᴏᴛ.</b>", reply_markup=InlineKeyboardMarkup(btn2))
        else:
            await query.answer("Yᴏᴜ ᴅᴏɴ'ᴛ ʜᴀᴠᴇ sᴜғғɪᴄɪᴀɴᴛ ʀɪɢʜᴛs ᴛᴏ ᴅᴏ ᴛʜɪs !", show_alert=True)
    elif query.data.startswith("uploaded"):
        ident, from_user = query.data.split("#")
        btn = [[InlineKeyboardButton("✅ Uᴘʟᴏᴀᴅᴇᴅ ✅", callback_data=f"upalert#{from_user}")]]
        btn2 = [[InlineKeyboardButton('Jᴏɪɴ Cʜᴀɴɴᴇʟ', url=link.invite_link), InlineKeyboardButton("Vɪᴇᴡ Sᴛᴀᴛᴜs", url=f"{query.message.link}")], [InlineKeyboardButton("Rᴇᴏ̨ᴜᴇsᴛ Gʀᴏᴜᴘ Lɪɴᴋ", url="https://t.me/+KzbVzahVdqQ3MmM1")]]
        if query.from_user.id in ADMINS:
            user = await client.get_users(from_user)
            reply_markup = InlineKeyboardMarkup(btn)
            content = query.message.text
            await query.message.edit_text(f"<b><strike>{content}</strike></b>")
            await query.message.edit_reply_markup(reply_markup)
            await query.answer("Sᴇᴛ ᴛᴏ Uᴘʟᴏᴀᴅᴇᴅ !")
            try:
                await client.send_message(chat_id=int(from_user), text=f"<b>Hᴇʏ {user.mention}, Yᴏᴜʀ ʀᴇᴏ̨ᴜᴇsᴛ ʜᴀs ʙᴇᴇɴ ᴜᴘʟᴏᴀᴅᴇᴅ ʙʏ ᴏᴜʀ ᴍᴏᴅᴇʀᴀᴛᴏʀs. Kɪɴᴅʟʏ sᴇᴀʀᴄʜ ɪɴ ᴏᴜʀ Gʀᴏᴜᴘ.</b>", reply_markup=InlineKeyboardMarkup(btn2))
            except UserIsBlocked:
                await client.send_message(chat_id=int(SUPPORT_CHAT_ID), text=f"<b>Hᴇʏ {user.mention}, Yᴏᴜʀ ʀᴇᴏ̨ᴜᴇsᴛ ʜᴀs ʙᴇᴇɴ ᴜᴘʟᴏᴀᴅᴇᴅ ʙʏ ᴏᴜʀ ᴍᴏᴅᴇʀᴀᴛᴏʀs. Kɪɴᴅʟʏ sᴇᴀʀᴄʜ ɪɴ ᴏᴜʀ Gʀᴏᴜᴘ.\n\nNᴏᴛᴇ: Tʜɪs ᴍᴇssᴀɢᴇ ɪs sᴇɴᴛ ᴛᴏ ᴛʜɪs ɢʀᴏᴜᴘ ʙᴇᴄᴀᴜsᴇ ʏᴏᴜ'ᴠᴇ ʙʟᴏᴄᴋᴇᴅ ᴛʜᴇ ʙᴏᴛ. Tᴏ sᴇɴᴅ ᴛʜɪs ᴍᴇssᴀɢᴇ ᴛᴏ ʏᴏᴜʀ PM, Mᴜsᴛ ᴜɴʙʟᴏᴄᴋ ᴛʜᴇ ʙᴏᴛ.</b>", reply_markup=InlineKeyboardMarkup(btn2))
        else:
            await query.answer("Yᴏᴜ ᴅᴏɴ'ᴛ ʜᴀᴠᴇ sᴜғғɪᴄɪᴀɴᴛ ʀɪɢʜᴛs ᴛᴏ ᴅᴏ ᴛʜɪs !", show_alert=True)
    elif query.data.startswith("already_available"):
        ident, from_user = query.data.split("#")
        btn = [[InlineKeyboardButton("🟢 Aʟʀᴇᴀᴅʏ Aᴠᴀɪʟᴀʙʟᴇ 🟢", callback_data=f"alalert#{from_user}")]]
        btn2 = [[InlineKeyboardButton('Jᴏɪɴ Cʜᴀɴɴᴇʟ', url=link.invite_link), InlineKeyboardButton("Vɪᴇᴡ Sᴛᴀᴛᴜs", url=f"{query.message.link}")], [InlineKeyboardButton("Rᴇᴏ̨ᴜᴇsᴛ Gʀᴏᴜᴘ Lɪɴᴋ", url="https.me/vj_bots")]]
        if query.from_user.id in ADMINS:
            user = await client.get_users(from_user)
            reply_markup = InlineKeyboardMarkup(btn)
            content = query.message.text
            await query.message.edit_text(f"<b><strike>{content}</strike></b>")
            await query.message.edit_reply_markup(reply_markup)
            await query.answer("Sᴇᴛ ᴛᴏ Aʟʀᴇᴀᴅʏ Aᴠᴀɪʟᴀʙʟᴇ !")
            try:
                await client.send_message(chat_id=int(from_user), text=f"<b>Hᴇʏ {user.mention}, Yᴏᴜʀ ʀᴇᴏ̨ᴜᴇsᴛ ɪs ᴀʟʀᴇᴀᴅʏ ᴀᴠᴀɪʟᴀʙʟᴇ ᴏɴ ᴏᴜʀ ʙᴏᴛ's ᴅᴀᴛᴀʙᴀsᴇ. Kɪɴᴅʟʏ sᴇᴀʀᴄʜ ɪɴ ᴏᴜʀ Gʀᴏᴜᴘ.</b>", reply_markup=InlineKeyboardMarkup(btn2))
            except UserIsBlocked:
                await client.send_message(chat_id=int(SUPPORT_CHAT_ID), text=f"<b>Hᴇʏ {user.mention}, Yᴏᴜʀ ʀᴇᴏ̨ᴜᴇsᴛ ɪs ᴀʟʀᴇᴀᴅʏ ᴀᴠᴀɪʟᴀʙʟᴇ ᴏɴ ᴏᴜʀ ʙᴏᴛ's ᴅᴀᴛᴀʙᴀsᴇ. Kɪɴᴅʟʏ sᴇᴀʀᴄʜ ɪɴ ᴏᴜʀ Gʀᴏᴜᴘ.\n\nNᴏᴛᴇ: Tʜɪs ᴍᴇssᴀɢᴇ ɪs sᴇɴᴛ ᴛᴏ ᴛʜɪs ɢʀᴏᴜᴘ ʙᴇᴄᴀᴜsᴇ ʏᴏᴜ'ᴠᴇ ʙʟᴏᴄᴋᴇᴅ ᴛʜᴇ ʙᴏᴛ. Tᴏ sᴇɴᴅ ᴛʜɪs ᴍᴇssᴀɢᴇ ᴛᴏ ʏᴏᴜʀ PM, Mᴜsᴛ ᴜɴʙʟᴏᴄᴋ ᴛʜᴇ ʙᴏᴛ.</b>", reply_markup=InlineKeyboardMarkup(btn2))
        else:
            await query.answer("Yᴏᴜ ᴅᴏɴ'ᴛ ʜᴀᴠᴇ sᴜғғɪᴄɪᴀɴᴛ ʀɪɢʜᴛs ᴛᴏ ᴅᴏ ᴛʜɪs !", show_alert=True)
    elif query.data.startswith("alalert"):
        ident, from_user = query.data.split("#")
        if int(query.from_user.id) == int(from_user):
            user = await client.get_users(from_user)
            await query.answer(f"Hᴇʏ {user.first_name}, Yᴏᴜʀ Rᴇᴏ̨ᴜᴇsᴛ ɪs Aʟʀᴇᴀᴅʏ Aᴠᴀɪʟᴀʙʟᴇ !", show_alert=True)
        else:
            await query.answer("Yᴏᴜ ᴅᴏɴ'ᴛ ʜᴀᴠᴇ sᴜғғɪᴄɪᴀɴᴛ ʀɪɢᴛs ᴛᴏ ᴅᴏ ᴛʜɪs !", show_alert=True)
    elif query.data.startswith("upalert"):
        ident, from_user = query.data.split("#")
        if int(query.from_user.id) == int(from_user):
            user = await client.get_users(from_user)
            await query.answer(f"Hᴇʏ {user.first_name}, Yᴏᴜʀ Rᴇᴏ̨ᴜᴇsᴛ ɪs Uᴘʟᴏᴀᴅᴇᴅ !", show_alert=True)
        else:
            await query.answer("Yᴏᴜ ᴅᴏɴ'ᴛ ʜᴀᴠᴇ sᴜғғɪᴄɪᴀɴᴛ ʀɪɢᴛs ᴛᴏ ᴅᴏ ᴛʜɪs !", show_alert=True)
    elif query.data.startswith("unalert"):
        ident, from_user = query.data.split("#")
        if int(query.from_user.id) == int(from_user):
            user = await client.get_users(from_user)
            await query.answer(f"Hᴇʏ {user.first_name}, Yᴏᴜʀ Rᴇᴏ̨ᴜᴇsᴛ ɪs Uɴᴀᴠᴀɪʟᴀʙʟᴇ !", show_alert=True)
        else:
            await query.answer("Yᴏᴜ ᴅᴏɴ'ᴛ ʜᴀᴠᴇ sᴜғғɪᴄɪᴀɴᴛ ʀɪɢᴛs ᴛᴏ ᴅᴏ ᴛʜɪs !", show_alert=True)
    elif query.data.startswith("generate_stream_link"):
        _, file_id = query.data.split(":")
        try:
            log_msg = await client.send_cached_media(chat_id=LOG_CHANNEL, file_id=file_id)
            fileName = {quote_plus(get_name(log_msg))}
            stream = f"{URL}watch/{str(log_msg.id)}/{quote_plus(get_name(log_msg))}?hash={get_hash(log_msg)}"
            download = f"{URL}{str(log_msg.id)}/{quote_plus(get_name(log_msg))}?hash={get_hash(log_msg)}"
            button = [[InlineKeyboardButton("• ᴅᴏᴡɴʟᴏᴀᴅ •", url=download), InlineKeyboardButton('• ᴡᴀᴛᴄʜ •', url=stream)], [InlineKeyboardButton("• ᴡᴀᴛᴄʜ ɪɴ ᴡᴇʙ ᴀᴘᴘ •", web_app=WebAppInfo(url=stream))]]
            await query.message.edit_reply_markup(InlineKeyboardMarkup(button))
        except Exception as e:
            print(e)
            await query.answer(f"something went wrong\n\n{e}", show_alert=True)
            return
    elif query.data == "reqinfo":
        await query.answer(text=script.REQINFO, show_alert=True)
    elif query.data == "select":
        await query.answer(text=script.SELECT, show_alert=True)
    elif query.data == "sinfo":
        await query.answer(text=script.SINFO, show_alert=True)
    elif query.data == "start":
        if PREMIUM_AND_REFERAL_MODE == True:
            buttons = [[InlineKeyboardButton('⤬ ᴀᴅᴅ ᴍᴇ ᴛᴏ ʏᴏᴜʀ ɢʀᴏᴜᴘ ⤬', url=f'http://t.me/{temp.U_NAME}?startgroup=true')], [InlineKeyboardButton('ᴇᴀʀɴ ᴍᴏɴᴇʏ', callback_data="shortlink_info"), InlineKeyboardButton('ᴍᴏᴠɪᴇ ɢʀᴏᴜᴘ', url=GRP_LNK)], [InlineKeyboardButton('ʜᴇʟᴘ', callback_data='help'), InlineKeyboardButton('ᴀʙᴏᴜᴛ', callback_data='about')], [InlineKeyboardButton('ᴘʀᴇᴍɪᴜᴍ ᴀɴᴅ ʀᴇғᴇʀʀᴀʟ', callback_data='subscription')], [InlineKeyboardButton('ᴊᴏɪɴ ᴜᴘᴅᴀᴛᴇ ᴄʜᴀɴɴᴇʟ', url=CHNL_LNK)]]
        else:
            buttons = [[InlineKeyboardButton('⤬ ᴀᴅᴅ ᴍᴇ ᴛᴏ ʏᴏᴜʀ ɢʀᴏᴜᴘ ⤬', url=f'http://t.me/{temp.U_NAME}?startgroup=true')], [InlineKeyboardButton('ᴇᴀʀɴ ᴍᴏɴᴇʏ', callback_data="shortlink_info"), InlineKeyboardButton('ᴍᴏᴠɪᴇ ɢʀᴏᴜᴘ', url=GRP_LNK)], [InlineKeyboardButton('ʜᴇʟᴘ', callback_data='help'), InlineKeyboardButton('ᴀʙᴏᴜᴛ', callback_data='about')], [InlineKeyboardButton('ᴊᴏɪɴ ᴜᴘᴅᴀᴛᴇ ᴄʜᴀɴɴᴇʟ', url=CHNL_LNK)]]
        if CLONE_MODE == True:
            buttons.append([InlineKeyboardButton('ᴄʀᴇᴀᴛᴇ ᴏᴡɴ ᴄʟᴏɴᴇ ʙᴏᴛ', callback_data='clone')])
        reply_markup = InlineKeyboardMarkup(buttons)
        await client.edit_message_media(query.message.chat.id, query.message.id, InputMediaPhoto(random.choice(PICS)))
        await query.message.edit_text(text=script.START_TXT.format(query.from_user.mention, temp.U_NAME, temp.B_NAME), reply_markup=reply_markup, parse_mode=enums.ParseMode.HTML)
        await query.answer(MSG_ALRT)
    elif query.data == "clone":
        buttons = [[InlineKeyboardButton('⟸ Bᴀᴄᴋ', callback_data='start')]]
        await client.edit_message_media(query.message.chat.id, query.message.id, InputMediaPhoto(random.choice(PICS)))
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(text=script.CLONE_TXT, reply_markup=reply_markup, parse_mode=enums.ParseMode.HTML)
    elif query.data == "filters":
        buttons = [[InlineKeyboardButton('Mᴀɴᴜᴀʟ FIʟᴛᴇʀ', callback_data='manuelfilter'), InlineKeyboardButton('Aᴜᴛᴏ FIʟᴛᴇʀ', callback_data='autofilter')], [InlineKeyboardButton('⟸ Bᴀᴄᴋ', callback_data='help'), InlineKeyboardButton('Gʟᴏʙᴀʟ Fɪʟᴛᴇʀs', callback_data='global_filters')]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await client.edit_message_media(query.message.chat.id, query.message.id, InputMediaPhoto(random.choice(PICS)))
        await query.message.edit_text(text=script.ALL_FILTERS.format(query.from_user.mention), reply_markup=reply_markup, parse_mode=enums.ParseMode.HTML)
    elif query.data == "global_filters":
        buttons = [[InlineKeyboardButton('⟸ Bᴀᴄᴋ', callback_data='filters')]]
        await client.edit_message_media(query.message.chat.id, query.message.id, InputMediaPhoto(random.choice(PICS)))
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(text=script.GFILTER_TXT, reply_markup=reply_markup, parse_mode=enums.ParseMode.HTML)
    elif query.data == "help":
        buttons = [[InlineKeyboardButton('⚙️ ᴀᴅᴍɪɴ ᴏɴʟʏ 🔧', callback_data='admin')], [InlineKeyboardButton('ʀᴇɴᴀᴍᴇ', callback_data='r_txt'), InlineKeyboardButton('sᴛʀᴇᴀᴍ/ᴅᴏᴡɴʟᴏᴀᴅ', callback_data='s_txt')], [InlineKeyboardButton('ꜰɪʟᴇ ꜱᴛᴏʀᴇ', callback_data='store_file'), InlineKeyboardButton('ᴛᴇʟᴇɢʀᴀᴘʜ', callback_data='tele')], [InlineKeyboardButton('ᴄᴏɴɴᴇᴄᴛɪᴏɴꜱ', callback_data='coct'), InlineKeyboardButton('ꜰɪʟᴛᴇʀꜱ', callback_data='filters')], [InlineKeyboardButton('ʏᴛ-ᴅʟ', callback_data='ytdl'), InlineKeyboardButton('ꜱʜᴀʀᴇ ᴛᴇxᴛ', callback_data='share')], [InlineKeyboardButton('ꜱᴏɴɢ', callback_data='song'), InlineKeyboardButton('ᴇᴀʀɴ ᴍᴏɴᴇʏ', callback_data='shortlink_info')], [InlineKeyboardButton('ꜱᴛɪᴄᴋᴇʀ-ɪᴅ', callback_data='sticker'), InlineKeyboardButton('ᴊ-ꜱᴏɴ', callback_data='json')], [InlineKeyboardButton('🏠 𝙷𝙾𝙼𝙴 🏠', callback_data='start')]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await client.edit_message_media(query.message.chat.id, query.message.id, InputMediaPhoto(random.choice(PICS)))
        await query.message.edit_text(text=script.HELP_TXT.format(query.from_user.mention), reply_markup=reply_markup, parse_mode=enums.ParseMode.HTML)
    elif query.data == "about":
        buttons = [[InlineKeyboardButton('Sᴜᴘᴘᴏʀᴛ Gʀᴏᴜᴘ', url=GRP_LNK), InlineKeyboardButton('Sᴏᴜʀᴄᴇ Cᴏᴅᴇ', url="https://github.com/VJBots/VJ-FILTER-BOT")], [InlineKeyboardButton('Hᴏᴍᴇ', callback_data='start'), InlineKeyboardButton('Cʟᴏsᴇ', callback_data='close_data')]]
        await client.edit_message_media(query.message.chat.id, query.message.id, InputMediaPhoto(random.choice(PICS)))
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(text=script.ABOUT_TXT.format(temp.U_NAME, temp.B_NAME, OWNER_LNK), reply_markup=reply_markup, parse_mode=enums.ParseMode.HTML)
    elif query.data == "subscription":
        buttons = [[InlineKeyboardButton('⇚Back', callback_data='start')]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await client.edit_message_media(query.message.chat.id, query.message.id, InputMediaPhoto(random.choice(PICS)))
        await query.message.edit_text(text=script.SUBSCRIPTION_TXT.format(REFERAL_PREMEIUM_TIME, temp.U_NAME, query.from_user.id, REFERAL_COUNT), reply_markup=reply_markup, parse_mode=enums.ParseMode.HTML)
    elif query.data == "manuelfilter":
        buttons = [[InlineKeyboardButton('⟸ Bᴀᴄᴋ', callback_data='filters'), InlineKeyboardButton('Bᴜᴛᴛᴏɴs', callback_data='button')]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await client.edit_message_media(query.message.chat.id, query.message.id, InputMediaPhoto(random.choice(PICS)))
        await query.message.edit_text(text=script.MANUELFILTER_TXT, reply_markup=reply_markup, parse_mode=enums.ParseMode.HTML)
    elif query.data == "button":
        buttons = [[InlineKeyboardButton('⟸ Bᴀᴄᴋ', callback_data='manuelfilter')]]
        await client.edit_message_media(query.message.chat.id, query.message.id, InputMediaPhoto(random.choice(PICS)))
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(text=script.BUTTON_TXT, reply_markup=reply_markup, parse_mode=enums.ParseMode.HTML)
    elif query.data == "autofilter":
        buttons = [[InlineKeyboardButton('⟸ Bᴀᴄᴋ', callback_data='filters')]]
        await client.edit_message_media(query.message.chat.id, query.message.id, InputMediaPhoto(random.choice(PICS)))
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(text=script.AUTOFILTER_TXT, reply_markup=reply_markup, parse_mode=enums.ParseMode.HTML)
    elif query.data == "coct":
        buttons = [[InlineKeyboardButton('⟸ Bᴀᴄᴋ', callback_data='help')]]
        await client.edit_message_media(query.message.chat.id, query.message.id, InputMediaPhoto(random.choice(PICS)))
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(text=script.CONNECTION_TXT, reply_markup=reply_markup, parse_mode=enums.ParseMode.HTML)
    elif query.data == "admin":
        buttons = [[InlineKeyboardButton('⟸ Bᴀᴄᴋ', callback_data='help'), InlineKeyboardButton('ᴇxᴛʀᴀ', callback_data='extra')]]
        await client.edit_message_media(query.message.chat.id, query.message.id, InputMediaPhoto(random.choice(PICS)))
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(text=script.ADMIN_TXT, reply_markup=reply_markup, parse_mode=enums.ParseMode.HTML)
    elif query.data == "store_file":
        buttons = [[InlineKeyboardButton('⟸ Bᴀᴄᴋ', callback_data='help')]]
        await client.edit_message_media(query.message.chat.id, query.message.id, InputMediaPhoto(random.choice(PICS)))
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(text=script.FILE_STORE_TXT, reply_markup=reply_markup, parse_mode=enums.ParseMode.HTML)
    elif query.data == "r_txt":
        buttons = [[InlineKeyboardButton('⟸ Bᴀᴄᴋ', callback_data='help')]]
        await client.edit_message_media(query.message.chat.id, query.message.id, InputMediaPhoto(random.choice(PICS)))
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(text=script.RENAME_TXT, reply_markup=reply_markup, parse_mode=enums.ParseMode.HTML)
    elif query.data == "s_txt":
        buttons = [[InlineKeyboardButton('⟸ Bᴀᴄᴋ', callback_data='help')]]
        await client.edit_message_media(query.message.chat.id, query.message.id, InputMediaPhoto(random.choice(PICS)))
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(text=script.STREAM_TXT, reply_markup=reply_markup, parse_mode=enums.ParseMode.HTML)
    elif query.data == "extra":
        buttons = [[InlineKeyboardButton('⟸ Bᴀᴄᴋ', callback_data='admin')]]
        await client.edit_message_media(query.message.chat.id, query.message.id, InputMediaPhoto(random.choice(PICS)))
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(text=script.EXTRAMOD_TXT.format(OWNER_LNK, CHNL_LNK), reply_markup=reply_markup, parse_mode=enums.ParseMode.HTML)
    elif query.data == "stats":
        buttons = [[InlineKeyboardButton('⟸ Bᴀᴄᴋ', callback_data='help'), InlineKeyboardButton('⟲ Rᴇғʀᴇsʜ', callback_data='rfrsh')]]
        await client.edit_message_media(query.message.chat.id, query.message.id, InputMediaPhoto(random.choice(PICS)))
        reply_markup = InlineKeyboardMarkup(buttons)
        total_users = await db.total_users_count()
        totl_chats = await db.total_chat_count()
        filesp = col.count_documents({})
        totalsec = sec_col.count_documents({})
        stats = vjdb.command('dbStats')
        used_dbSize = (stats['dataSize']/(1024*1024))+(stats['indexSize']/(1024*1024))
        free_dbSize = 512-used_dbSize
        stats2 = sec_db.command('dbStats')
        used_dbSize2 = (stats2['dataSize']/(1024*1024))+(stats2['indexSize']/(1024*1024))
        free_dbSize2 = 512-used_dbSize2
        stats3 = mydb.command('dbStats')
        used_dbSize3 = (stats3['dataSize']/(1024*1024))+(stats3['indexSize']/(1024*1024))
        free_dbSize3 = 512-used_dbSize3
        await query.message.edit_text(text=script.STATUS_TXT.format((int(filesp)+int(totalsec)), total_users, totl_chats, filesp, round(used_dbSize, 2), round(free_dbSize, 2), totalsec, round(used_dbSize2, 2), round(free_dbSize2, 2), round(used_dbSize3, 2), round(free_dbSize3, 2)), reply_markup=reply_markup, parse_mode=enums.ParseMode.HTML)
    elif query.data == "rfrsh":
        await query.answer("Fetching MongoDb DataBase")
        buttons = [[InlineKeyboardButton('⟸ Bᴀᴄᴋ', callback_data='help'), InlineKeyboardButton('⟲ Rᴇғʀᴇsʜ', callback_data='rfrsh')]]
        await client.edit_message_media(query.message.chat.id, query.message.id, InputMediaPhoto(random.choice(PICS)))
        reply_markup = InlineKeyboardMarkup(buttons)
        total_users = await db.total_users_count()
        totl_chats = await db.total_chat_count()
        filesp = col.count_documents({})
        totalsec = sec_col.count_documents({})
        stats = vjdb.command('dbStats')
        used_dbSize = (stats['dataSize']/(1024*1024))+(stats['indexSize']/(1024*1024))
        free_dbSize = 512-used_dbSize
        stats2 = sec_db.command('dbStats')
        used_dbSize2 = (stats2['dataSize']/(1024*1024))+(stats2['indexSize']/(1024*1024))
        free_dbSize2 = 512-used_dbSize2
        stats3 = mydb.command('dbStats')
        used_dbSize3 = (stats3['dataSize']/(1024*1024))+(stats3['indexSize']/(1024*1024))
        free_dbSize3 = 512-used_dbSize3
        await query.message.edit_text(text=script.STATUS_TXT.format((int(filesp)+int(totalsec)), total_users, totl_chats, filesp, round(used_dbSize, 2), round(free_dbSize, 2), totalsec, round(used_dbSize2, 2), round(free_dbSize2, 2), round(used_dbSize3, 2), round(free_dbSize3, 2)), reply_markup=reply_markup, parse_mode=enums.ParseMode.HTML)
    elif query.data == "shortlink_info":
        btn = [[InlineKeyboardButton("👇Select Your Language 👇", callback_data="laninfo")], [InlineKeyboardButton("Tamil", callback_data="tamil_info"), InlineKeyboardButton("English", callback_data="english_info"), InlineKeyboardButton("Hindi", callback_data="hindi_info")], [InlineKeyboardButton("Malayalam", callback_data="malayalam_info"), InlineKeyboardButton("Urdu", callback_data="urdu_info"), InlineKeyboardButton("Bangla", callback_data="bangladesh_info")], [InlineKeyboardButton("Telugu", callback_data="telugu_info"), InlineKeyboardButton("Kannada", callback_data="kannada_info"), InlineKeyboardButton("Gujarati", callback_data="gujarati_info")], [InlineKeyboardButton("⟸ Bᴀᴄᴋ", callback_data="start")]]
        await client.edit_message_media(query.message.chat.id, query.message.id, InputMediaPhoto(random.choice(PICS)))
        reply_markup = InlineKeyboardMarkup(btn)
        await query.message.edit_text(text=(script.SHORTLINK_INFO), reply_markup=reply_markup, parse_mode=enums.ParseMode.HTML)
    elif query.data == "tele":
        btn = [[InlineKeyboardButton("⟸ Bᴀᴄᴋ", callback_data="help"), InlineKeyboardButton("Cᴏɴᴛᴀᴄᴛ", url="telegram.me/KingVJ01")]]
        await client.edit_message_media(query.message.chat.id, query.message.id, InputMediaPhoto(random.choice(PICS)))
        reply_markup = InlineKeyboardMarkup(btn)
        await query.message.edit_text(text=(script.TELE_TXT), reply_markup=reply_markup, parse_mode=enums.ParseMode.HTML)
    elif query.data == "ytdl":
        buttons = [[InlineKeyboardButton('⇍ ʙᴀᴄᴋ ⇏', callback_data='help')]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(text="● ◌ ◌")
        await query.message.edit_text(text="● ● ◌")
        await query.message.edit_text(text="● ● ●")
        reply_markup = InlineKeyboardMarkup(buttons)
        await client.edit_message_media(query.message.chat.id, query.message.id, InputMediaPhoto(random.choice(PICS)))
        await query.message.edit_text(text=script.YTDL_TXT, reply_markup=reply_markup, parse_mode=enums.ParseMode.HTML)
    elif query.data == "share":
        btn = [[InlineKeyboardButton("⟸ Bᴀᴄᴋ", callback_data="help"), InlineKeyboardButton("Cᴏɴᴛᴀᴄᴛ", url="telegram.me/KingVj01")]]
        await client.edit_message_media(query.message.chat.id, query.message.id, InputMediaPhoto(random.choice(PICS)))
        reply_markup = InlineKeyboardMarkup(btn)
        await query.message.edit_text(text=(script.SHARE_TXT), reply_markup=reply_markup, parse_mode=enums.ParseMode.HTML)
    elif query.data == "song":
        btn = [[InlineKeyboardButton("⟸ Bᴀᴄᴋ", callback_data="help"), InlineKeyboardButton("Cᴏɴᴛᴀᴄᴛ", url="telegram.me/KingVj01")]]
        await client.edit_message_media(query.message.chat.id, query.message.id, InputMediaPhoto(random.choice(PICS)))
        reply_markup = InlineKeyboardMarkup(btn)
        await query.message.edit_text(text=(script.SONG_TXT), reply_markup=reply_markup, parse_mode=enums.ParseMode.HTML)
    elif query.data == "json":
        buttons = [[InlineKeyboardButton('⇍ ʙᴀᴄᴋ ⇏', callback_data='help')]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(text="● ◌ ◌")
        await query.message.edit_text(text="● ● ◌")
        await query.message.edit_text(text="● ● ●")
        reply_markup = InlineKeyboardMarkup(buttons)
        await client.edit_message_media(query.message.chat.id, query.message.id, InputMediaPhoto(random.choice(PICS)))
        await query.message.edit_text(text=script.JSON_TXT, reply_markup=reply_markup, parse_mode=enums.ParseMode.HTML)
    elif query.data == "sticker":
        btn = [[InlineKeyboardButton("⟸ Bᴀᴄᴋ", callback_data="help"), InlineKeyboardButton("Cᴏɴᴛᴀᴄᴛ", url="telegram.me/KingVj01")]]
        await client.edit_message_media(query.message.chat.id, query.message.id, InputMediaPhoto(random.choice(PICS)))
        reply_markup = InlineKeyboardMarkup(btn)
        await query.message.edit_text(text=(script.STICKER_TXT), reply_markup=reply_markup, parse_mode=enums.ParseMode.HTML)
    elif query.data == "tamil_info":
        btn = [[InlineKeyboardButton("⟸ Bᴀᴄᴋ", callback_data="start"), InlineKeyboardButton("Cᴏɴᴛᴀᴄᴛ", url="telegram.me/KingVj01")]]
        await client.edit_message_media(query.message.chat.id, query.message.id, InputMediaPhoto(random.choice(PICS)))
        reply_markup = InlineKeyboardMarkup(btn)
        await query.message.edit_text(text=(script.TAMIL_INFO), reply_markup=reply_markup, parse_mode=enums.ParseMode.HTML)
    elif query.data == "english_info":
        btn = [[InlineKeyboardButton("⟸ Bᴀᴄᴋ", callback_data="start"), InlineKeyboardButton("Cᴏɴᴛᴀᴄᴛ", url="telegram.me/KingVj01")]]
        await client.edit_message_media(query.message.chat.id, query.message.id, InputMediaPhoto(random.choice(PICS)))
        reply_markup = InlineKeyboardMarkup(btn)
        await query.message.edit_text(text=(script.ENGLISH_INFO), reply_markup=reply_markup, parse_mode=enums.ParseMode.HTML)
    elif query.data == "hindi_info":
        btn = [[InlineKeyboardButton("⟸ Bᴀᴄᴋ", callback_data="start"), InlineKeyboardButton("Cᴏɴᴛᴀᴄᴛ", url="telegram.me/KingVj01")]]
        await client.edit_message_media(query.message.chat.id, query.message.id, InputMediaPhoto(random.choice(PICS)))
        reply_markup = InlineKeyboardMarkup(btn)
        await query.message.edit_text(text=(script.HINDI_INFO), reply_markup=reply_markup, parse_mode=enums.ParseMode.HTML)
    elif query.data == "telugu_info":
        btn = [[InlineKeyboardButton("⟸ Bᴀᴄᴋ", callback_data="start"), InlineKeyboardButton("Cᴏɴᴛᴀᴄᴛ", url="telegram.me/KingVj01")]]
        await client.edit_message_media(query.message.chat.id, query.message.id, InputMediaPhoto(random.choice(PICS)))
        reply_markup = InlineKeyboardMarkup(btn)
        await query.message.edit_text(text=(script.TELUGU_INFO), reply_markup=reply_markup, parse_mode=enums.ParseMode.HTML)
    elif query.data == "malayalam_info":
        btn = [[InlineKeyboardButton("⟸ Bᴀᴄᴋ", callback_data="start"), InlineKeyboardButton("Cᴏɴᴛᴀᴄᴛ", url="telegram.me/KingVj01")]]
        await client.edit_message_media(query.message.chat.id, query.message.id, InputMediaPhoto(random.choice(PICS)))
        reply_markup = InlineKeyboardMarkup(btn)
        await query.message.edit_text(text=(script.MALAYALAM_INFO), reply_markup=reply_markup, parse_mode=enums.ParseMode.HTML)
    elif query.data == "urdu_info":
        btn = [[InlineKeyboardButton("⟸ Bᴀᴄᴋ", callback_data="start"), InlineKeyboardButton("Cᴏɴᴛᴀᴄᴛ", url="telegram.me/KingVj01")]]
        await client.edit_message_media(query.message.chat.id, query.message.id, InputMediaPhoto(random.choice(PICS)))
        reply_markup = InlineKeyboardMarkup(btn)
        await query.message.edit_text(text=(script.URDU_INFO), reply_markup=reply_markup, parse_mode=enums.ParseMode.HTML)
    elif query.data == "bangladesh_info":
        btn = [[InlineKeyboardButton("⟸ Bᴀᴄᴋ", callback_data="start"), InlineKeyboardButton("Cᴏɴᴛᴀᴄᴛ", url="telegram.me/KingVj01")]]
        await client.edit_message_media(query.message.chat.id, query.message.id, InputMediaPhoto(random.choice(PICS)))
        reply_markup = InlineKeyboardMarkup(btn)
        await query.message.edit_text(text=(script.BANGLADESH_INFO), reply_markup=reply_markup, parse_mode=enums.ParseMode.HTML)
    elif query.data == "kannada_info":
        btn = [[InlineKeyboardButton("⟸ Bᴀᴄᴋ", callback_data="start"), InlineKeyboardButton("Cᴏɴᴛᴀᴄᴛ", url="telegram.me/KingVj01")]]
        await client.edit_message_media(query.message.chat.id, query.message.id, InputMediaPhoto(random.choice(PICS)))
        reply_markup = InlineKeyboardMarkup(btn)
        await query.message.edit_text(text=(script.KANNADA_INFO), reply_markup=reply_markup, parse_mode=enums.ParseMode.HTML)
    elif query.data == "gujarati_info":
        btn = [[InlineKeyboardButton("⟸ Bᴀᴄᴋ", callback_data="start"), InlineKeyboardButton("Cᴏɴᴛᴀᴄᴛ", url="telegram.me/KingVj01")]]
        await client.edit_message_media(query.message.chat.id, query.message.id, InputMediaPhoto(random.choice(PICS)))
        reply_markup = InlineKeyboardMarkup(btn)
        await query.message.edit_text(text=(script.GUJARATI_INFO), reply_markup=reply_markup, parse_mode=enums.ParseMode.HTML)
    elif query.data.startswith("setgs"):
        ident, set_type, status, grp_id = query.data.split("#")
        grpid = await active_connection(str(query.from_user.id))
        if str(grp_id) != str(grpid):
            await query.message.edit("Yᴏᴜʀ Aᴄᴛɪᴠᴇ Cᴏɴɴᴇᴄᴛɪᴏɴ Hᴀs Bᴇᴇɴ Cʜᴀɴɢᴇᴅ. Gᴏ Tᴏ /connections ᴀɴᴅ ᴄʜᴀɴɢᴇ ʏᴏᴜʀ ᴀᴄᴛɪᴠᴇ ᴄᴏɴɴᴇᴄᴛɪᴏɴ.")
            return await query.answer(MSG_ALRT)
        if status == "True":
            await save_group_settings(grpid, set_type, False)
        else:
            settings = await get_settings(grpid)
            if set_type == "is_shortlink" and not settings['shortlink']:
                return await query.answer(text = "First Add Your Shortlink Url And Api By /shortlink Command, Then Turn Me On.", show_alert = True)
            await save_group_settings(grpid, set_type, True)
        settings = await get_settings(grpid)
        if settings is not None:
            buttons = [[InlineKeyboardButton('Rᴇsᴜʟᴛ Pᴀɢᴇ', callback_data=f'setgs#button#{settings["button"]}#{str(grp_id)}'), InlineKeyboardButton('Bᴜᴛᴛᴏɴ' if settings["button"] else 'Tᴇxᴛ', callback_data=f'setgs#button#{settings["button"]}#{str(grp_id)}')], [InlineKeyboardButton('Pʀᴏᴛᴇᴄᴛ Cᴏɴᴛᴇɴᴛ', callback_data=f'setgs#file_secure#{settings["file_secure"]}#{str(grp_id)}'), InlineKeyboardButton('✔ Oɴ' if settings["file_secure"] else '✘ Oғғ', callback_data=f'setgs#file_secure#{settings["file_secure"]}#{str(grp_id)}')], [InlineKeyboardButton('Iᴍᴅʙ', callback_data=f'setgs#imdb#{settings["imdb"]}#{str(grp_id)}'), InlineKeyboardButton('✔ Oɴ' if settings["imdb"] else '✘ Oғғ', callback_data=f'setgs#imdb#{settings["imdb"]}#{str(grp_id)}')], [InlineKeyboardButton('Sᴘᴇʟʟ Cʜᴇᴄᴋ', callback_data=f'setgs#spell_check#{settings["spell_check"]}#{str(grp_id)}'), InlineKeyboardButton('✔ Oɴ' if settings["spell_check"] else '✘ Oғғ', callback_data=f'setgs#spell_check#{settings["spell_check"]}#{str(grp_id)}')], [InlineKeyboardButton('Wᴇʟᴄᴏᴍᴇ Msɢ', callback_data=f'setgs#welcome#{settings["welcome"]}#{str(grp_id)}'), InlineKeyboardButton('✔ Oɴ' if settings["welcome"] else '✘ Oғғ', callback_data=f'setgs#welcome#{settings["welcome"]}#{str(grp_id)}')], [InlineKeyboardButton('Aᴜᴛᴏ-Dᴇʟᴇᴛᴇ', callback_data=f'setgs#auto_delete#{settings["auto_delete"]}#{str(grp_id)}'), InlineKeyboardButton('5 Mɪɴs' if settings["auto_delete"] else '✘ Oғғ', callback_data=f'setgs#auto_delete#{settings["auto_delete"]}#{str(grp_id)}')], [InlineKeyboardButton('Aᴜᴛᴏ-Fɪʟᴛᴇʀ', callback_data=f'setgs#auto_ffilter#{settings["auto_ffilter"]}#{str(grp_id)}'), InlineKeyboardButton('✔ Oɴ' if settings["auto_ffilter"] else '✘ Oғғ', callback_data=f'setgs#auto_ffilter#{settings["auto_ffilter"]}#{str(grp_id)}')], [InlineKeyboardButton('Mᴀx Bᴜᴛᴛᴏɴs', callback_data=f'setgs#max_btn#{settings["max_btn"]}#{str(grp_id)}'), InlineKeyboardButton('10' if settings["max_btn"] else f'{MAX_B_TN}', callback_data=f'setgs#max_btn#{settings["max_btn"]}#{str(grp_id)}')], [InlineKeyboardButton('SʜᴏʀᴛLɪɴᴋ', callback_data=f'setgs#is_shortlink#{settings["is_shortlink"]}#{str(grp_id)}'), InlineKeyboardButton('✔ Oɴ' if settings["is_shortlink"] else '✘ Oғғ', callback_data=f'setgs#is_shortlink#{settings["is_shortlink"]}#{str(grp_id)}')]]
            reply_markup = InlineKeyboardMarkup(buttons)
            await query.message.edit_reply_markup(reply_markup)
    await query.answer(MSG_ALRT)
