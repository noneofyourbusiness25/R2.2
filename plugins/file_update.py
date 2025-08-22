import asyncio
import re
import os
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from info import ADMINS, UPDATE_INTERVAL
from database.users_chats_db import db
from utils import get_size, is_subscribed
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class PrettifyManager:
    def __init__(self):
        self.series_pattern = re.compile(r'\b((s|season)\s?(\d{1,2})[\s\._-]*(\[)?(e|ep|episode)\]?\s?(\d{1,3})|\d{1,2}x\d{1,2})\b', re.IGNORECASE)
        self.year_pattern = re.compile(r'\b(19|20)\d{2}\b')
        self.delimiter_pattern = re.compile(r'[-._(\[]|1080p|720p')

    def prettify_filename(self, filename):
        # Remove file extension
        filename, _ = os.path.splitext(filename)

        # Remove @ tags
        filename = re.sub(r'^@\w+\s*', '', filename)

        # Normalize: replace . and _ with space, collapse multiple spaces
        filename = re.sub(r'[._]', ' ', filename)
        filename = re.sub(r'\s+', ' ', filename).strip()

        # Remove special characters
        filename = re.sub(r'''[_"':+-/()]''', '', filename)

        # Extraction based on series pattern
        series_match = self.series_pattern.search(filename)
        if series_match:
            return filename[:series_match.end()].strip()

        # Extraction based on year pattern
        year_match = self.year_pattern.search(filename)
        if year_match:
            return filename[:year_match.end()].strip()

        # Fallback 1: cut at first delimiter
        delimiter_match = self.delimiter_pattern.search(filename)
        if delimiter_match:
            return filename[:delimiter_match.start()].strip()

        # Fallback 2: use full normalized filename
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
        text += "\n\n🤔 How to get these files ❔\n✅ Copy the text by tapping on text\n✅ Use this Link\n✅ Select any group and paste it there\n🍿 Enjoy @R_Bots_Updates 🍿"

        try:
            logger.info(f"Sending announcement to channel {channel_id}")
            await self.bot.send_message(chat_id=channel_id, text=text)
            logger.info("Announcement sent successfully.")
        except Exception as e:
            logger.error(f"Error sending announcement: {e}", exc_info=True)

@Client.on_message(filters.command('add_update_channel') & filters.user(ADMINS))
async def add_update_channel(bot, message):
    if len(message.command) != 2:
        return await message.reply_text("Usage: /add_update_channel <channel_id>")

    channel_id = int(message.command[1])
    await db.update_channel_id(channel_id)
    await message.reply_text(f"Update channel set to {channel_id}")

@Client.on_message(filters.command('rm_update_channel') & filters.user(ADMINS))
async def rm_update_channel(bot, message):
    await db.update_channel_id(None)
    await message.reply_text("Update channel removed.")

@Client.on_message(filters.command('update_on') & filters.user(ADMINS))
async def update_on(bot, message):
    await db.update_feature_status(True)
    await message.reply_text("File update announcements are now ON.")

@Client.on_message(filters.command('update_off') & filters.user(ADMINS))
async def update_off(bot, message):
    await db.update_feature_status(False)
    await message.reply_text("File update announcements are now OFF.")
