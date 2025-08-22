# Don't Remove Credit @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot @Tech_VJ
# Ask Doubt on telegram @KingVJ01

# Clone Code Credit : YT - @Tech_VJ / TG - @VJ_Bots / GitHub - @VJBots

import sys, glob, importlib, logging, logging.config, pytz, asyncio
from pathlib import Path

# Get logging configurations
logging.config.fileConfig('logging.conf')
logging.getLogger().setLevel(logging.INFO)
logging.getLogger("pyrogram").setLevel(logging.ERROR)
logging.getLogger("cinemagoer").setLevel(logging.ERROR)

from pyrogram import Client, idle
from database.users_chats_db import db
from info import *
from utils import temp
from typing import Union, Optional, AsyncGenerator
from Script import script
from datetime import date, datetime
from aiohttp import web
from plugins import web_server
from plugins.clone import restart_bots

# Import the specific function needed for the periodic saver
from plugins.channel import save_batch
from database.announcement_db import (
    get_announcement_status, get_announcement_channel,
    get_announcement_queue, clear_announcement_queue
)
import time

from TechVJ.bot import TechVJBot
from TechVJ.util.keepalive import ping_server
from TechVJ.bot.clients import initialize_clients

ppath = "plugins/*.py"
files = glob.glob(ppath)
# TechVJBot = TechVJBot()  <- This is the line that has been removed.
loop = asyncio.get_event_loop()

async def periodic_save():
    """Periodically save the file batch to the database every 60 seconds."""
    while True:
        await asyncio.sleep(60)
        await save_batch()

async def send_announcements():
    """Periodically send file update announcements."""
    while True:
        await asyncio.sleep(10)  # Check every 10 seconds
        if not get_announcement_status():
            continue

        announcement_channel = get_announcement_channel()
        if not announcement_channel:
            continue

        queue = get_announcement_queue(limit=100) # Get a larger batch to check for timeout
        if not queue:
            continue

        items_to_send = []
        if len(queue) >= 10:
            items_to_send = queue[:10]
        # If there are fewer than 10 items, check if the oldest has been waiting for more than 60 seconds
        elif time.time() - queue[0]['timestamp'] > 60:
            items_to_send = queue
        else:
            continue

        unique_filenames = set()
        message_lines = []
        item_ids_to_clear = []

        for item in items_to_send:
            if item['file_name'] not in unique_filenames:
                unique_filenames.add(item['file_name'])
                message_lines.append(f"`{item['file_name']}` - ✅")
            item_ids_to_clear.append(item['_id'])

        if not message_lines:
            clear_announcement_queue(item_ids_to_clear)
            continue

        message_text = "📂 **New files indexed:**\n\n" + "\n".join(message_lines)
        message_text += "\n\n🤔 **How to get these files ❔**\n✅ Copy the text by tapping on text\n✅ Use this [Link](https://t.me/R_Bots_Updates/18)\n✅ Select any group and paste it there🍿\nEnjoy **@R_Bots_Updates** 🍿"

        try:
            await TechVJBot.send_message(
                chat_id=announcement_channel,
                text=message_text,
                parse_mode="markdown",
                disable_web_page_preview=True
            )
            clear_announcement_queue(item_ids_to_clear)
        except Exception as e:
            logging.error(f"Failed to send announcement: {e}")


async def start():
    print('\n')
    print('Initalizing Your Bot')
    await TechVJBot.start()
    bot_info = await TechVJBot.get_me()
    await initialize_clients()
    for name in files:
        with open(name) as a:
            patt = Path(a.name)
            plugin_name = patt.stem.replace(".py", "")
            plugins_dir = Path(f"plugins/{plugin_name}.py")
            import_path = "plugins.{}".format(plugin_name)
            spec = importlib.util.spec_from_file_location(import_path, plugins_dir)
            load = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(load)
            sys.modules["plugins." + plugin_name] = load
            print("Tech VJ Imported => " + plugin_name)

    if ON_HEROKU:
        asyncio.create_task(ping_server())

    # Start the periodic saving task for channel files
    asyncio.create_task(periodic_save())
    asyncio.create_task(send_announcements())

    b_users, b_chats = await db.get_banned()
    temp.BANNED_USERS = b_users
    temp.BANNED_CHATS = b_chats
    me = await TechVJBot.get_me()
    temp.BOT = TechVJBot
    temp.ME = me.id
    temp.U_NAME = me.username
    temp.B_NAME = me.first_name
    logging.info(script.LOGO)
    tz = pytz.timezone('Asia/Kolkata')
    today = date.today()
    now = datetime.now(tz)
    time = now.strftime("%H:%M:%S %p")
    try:
        await TechVJBot.send_message(chat_id=LOG_CHANNEL, text=script.RESTART_TXT.format(today, time))
    except:
        print("Make Your Bot Admin In Log Channel With Full Rights")
    for ch in CHANNELS:
        try:
            k = await TechVJBot.send_message(chat_id=ch, text="**Bot Restarted**")
            await k.delete()
        except Exception as e:
            print(f"Error sending message to channel {ch}: {e}\nMake sure your bot is an admin in this channel with full rights.")
    try:
        k = await TechVJBot.send_message(chat_id=AUTH_CHANNEL, text="**Bot Restarted**")
        await k.delete()
    except:
        print("Make Your Bot Admin In Force Subscribe Channel With Full Rights")
    if CLONE_MODE == True:
        print("Restarting All Clone Bots.......")
        await restart_bots()
        print("Restarted All Clone Bots.")
    app = web.AppRunner(await web_server())
    await app.setup()
    bind_address = "0.0.0.0"
    await web.TCPSite(app, bind_address, PORT).start()
    await idle()


if __name__ == '__main__':
    try:
        loop.run_until_complete(start())
    except KeyboardInterrupt:
        logging.info('Service Stopped Bye 👋')
