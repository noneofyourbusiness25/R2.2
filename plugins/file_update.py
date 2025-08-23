import asyncio
import re
import os
from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from info import ADMINS, UPDATE_INTERVAL, CHANNELS
from database.users_chats_db import db
from utils import get_size, is_subscribed
from database.ia_filterdb import save_file
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class PrettifyManager:
    def __init__(self):
        self.series_pattern = re.compile(r'\b((s|season)\s?(\d{1,2})[\s\._-]*(\[)?(e|ep|episode)\]?\s?(\d{1,3})|\d{1,2}x\d{1,2})\b', re.IGNORECASE)
        self.year_pattern = re.compile(r'\b(19|20)\d{2}\b')
        self.delimiter_pattern = re.compile(r'[-._(\[]|1080p|720p')

    def prettify_filename(self, filename):
        # 1. Remove file extension
        filename, _ = os.path.splitext(filename)

        # 2. Handle series content
        series_match = self.series_pattern.search(filename)
        if series_match:
            # Keep only the part of the filename before and including the series match
            filename = filename[:series_match.end()]

        # 3. Normalize separators
        # Replace dots, underscores, hyphens, and brackets with spaces
        filename = re.sub(r'[._\-[\]()]', ' ', filename)

        # 4. Remove common noise/quality keywords
        noise = ['1080p', '720p', '480p', '360p', 'bluray', 'web-dl', 'web', 'hdrip', 'dvdrip',
                 'x264', 'x265', 'h264', 'h265', 'aac', 'dts', 'ac3', 'dd5 1',
                 'proper', 'internal', 'repack', 'subs', 'dual audio']
        # Build a regex to find whole words from the noise list
        noise_pattern = r'\b(' + '|'.join(re.escape(n) for n in noise) + r')\b'
        filename = re.sub(noise_pattern, '', filename, flags=re.IGNORECASE)

        # 5. Final cleanup
        # Collapse multiple spaces and strip leading/trailing space
        filename = re.sub(r'\s+', ' ', filename).strip()

        return filename

class AnnouncementManager:
    def __init__(self, bot):
        self.bot = bot
        self.buffer = []
        self.lock = asyncio.Lock()
        self.task = asyncio.create_task(self.periodic_check())
        logger.info("AnnouncementManager initialized.")

    async def periodic_check(self):
        while True:
            await asyncio.sleep(UPDATE_INTERVAL)
            logger.info("Periodic check running...")
            await self.process_buffer(force=True)

    async def add_file(self, filename):
        async with self.lock:
            if filename not in self.buffer:
                self.buffer.append(filename)
                logger.info(f"Added file to buffer: {filename}")
                logger.info(f"Buffer size: {len(self.buffer)}")
        await self.process_buffer()

    async def process_buffer(self, force=False):
        logger.info("Processing buffer...")
        async with self.lock:
            if len(self.buffer) >= 10 or (force and self.buffer):
                if len(self.buffer) >= 10:
                    logger.info("Buffer size >= 10, sending announcement.")
                if force and self.buffer:
                    logger.info("Forcing announcement.")
                await self.send_announcement()

    async def send_announcement(self):
        logger.info("Sending announcement...")
        if not self.buffer:
            logger.info("Buffer is empty, not sending.")
            return

        settings = await db.get_update_settings()
        logger.info(f"Update settings: {settings}")
        if not settings.get('file_updates_on'):
            logger.info("File updates are off.")
            return

        channel_id = settings.get('channel_id')
        if not channel_id:
            logger.info("Update channel not set.")
            return

        prettify_manager = PrettifyManager()
        filenames = [prettify_manager.prettify_filename(f) for f in self.buffer[:10]]
        self.buffer = self.buffer[10:]

        # Ensure unique filenames
        filenames = list(dict.fromkeys(filenames))

        text = "📂 New files indexed:\n\n"
        text += "\n".join([f"`{name}` - ✅" for name in filenames])
        text += "\n\n🤔 How to get these files ❔\n✅ Copy the text by tapping on text\n✅ [Use this Link](https://t.me/R_Bots_Updates/18)\n✅ Select any group and paste it there\n🍿 Enjoy @R_Bots_Updates 🍿"

        try:
            logger.info(f"Sending announcement to channel {channel_id}")
            await self.bot.send_message(
                chat_id=channel_id,
                text=text,
                parse_mode=enums.ParseMode.MARKDOWN,
                disable_web_page_preview=True
            )
            logger.info("Announcement sent successfully.")
        except Exception as e:
            logger.error(f"Error sending announcement: {e}", exc_info=True)

@Client.on_message(filters.command('announcement_settings') & filters.user(ADMINS))
async def announcement_settings(bot, message):
    settings = await db.get_update_settings()
    buttons = [
        [InlineKeyboardButton("Announcements: " + ("On" if settings.get('file_updates_on') else "Off"), callback_data="toggle_announcements")],
        [InlineKeyboardButton("Set Update Channel", callback_data="set_update_channel")],
        [InlineKeyboardButton("Set Monitored Channels", callback_data="set_monitored_channels")]
    ]
    await message.reply_text("Announcement Settings", reply_markup=InlineKeyboardMarkup(buttons))

@Client.on_callback_query(filters.regex(r"^(toggle_announcements|set_update_channel|set_monitored_channels)$"))
async def announcement_settings_cb(bot, query):
    data = query.data
    if data == "toggle_announcements":
        settings = await db.get_update_settings()
        new_status = not settings.get('file_updates_on')
        await db.update_feature_status(new_status)
        await query.message.edit_reply_markup(
            InlineKeyboardMarkup([
                [InlineKeyboardButton("Announcements: " + ("On" if new_status else "Off"), callback_data="toggle_announcements")],
                [InlineKeyboardButton("Set Update Channel", callback_data="set_update_channel")],
                [InlineKeyboardButton("Set Monitored Channels", callback_data="set_monitored_channels")]
            ])
        )
    elif data == "set_update_channel":
        ask = await query.message.chat.ask("Send me the ID of the new update channel.")
        if ask.text and ask.text.lstrip('-').isdigit():
            await db.update_channel_id(int(ask.text))
            await ask.reply_text("Update channel has been set.")
        else:
            await ask.reply_text("Invalid channel ID.")
    elif data == "set_monitored_channels":
        ask = await query.message.chat.ask("Send me the IDs of the channels to monitor, separated by spaces.")
        if ask.text:
            channels = [int(ch) for ch in ask.text.split()]
            await db.update_monitored_channels(channels)
            await ask.reply_text("Monitored channels have been set.")

async def monitored_channel_filter(_, __, message):
    settings = await db.get_update_settings()
    monitored_channels = settings.get('monitored_channels', [])
    return message.chat.id in monitored_channels

monitored_channel = filters.create(monitored_channel_filter)

@Client.on_message(monitored_channel & filters.media)
async def new_file_handler(bot, message):
    if hasattr(bot, 'announcement_manager'):
        media = getattr(message, message.media.value, None)
        if media and hasattr(media, "file_name"):
            saved, _ = await save_file(media)
            if saved:
                await bot.announcement_manager.add_file(media.file_name)
