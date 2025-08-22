from pyrogram import Client, filters
from pyrogram.types import Message
from info import ADMINS
from database.announcement_db import (
    set_announcement_channel, get_announcement_channel,
    announcement_on, announcement_off, get_announcement_status
)

@Client.on_message(filters.command("set_announcement_channel") & filters.user(ADMINS))
async def set_announcement_channel_handler(bot: Client, message: Message):
    try:
        channel_id = int(message.text.split(" ", 1)[1])
        set_announcement_channel(channel_id)
        await message.reply_text(f"Announcement channel has been set to `{channel_id}`.")
    except (IndexError, ValueError):
        await message.reply_text("Please provide a valid channel ID.")

@Client.on_message(filters.command("announcement_on") & filters.user(ADMINS))
async def announcement_on_handler(bot: Client, message: Message):
    announcement_on()
    await message.reply_text("File update announcements have been turned ON.")

@Client.on_message(filters.command("announcement_off") & filters.user(ADMINS))
async def announcement_off_handler(bot: Client, message: Message):
    announcement_off()
    await message.reply_text("File update announcements have been turned OFF.")

@Client.on_message(filters.command("announcement_status") & filters.user(ADMINS))
async def announcement_status_handler(bot: Client, message: Message):
    enabled = get_announcement_status()
    channel_id = get_announcement_channel()
    status = "ON" if enabled else "OFF"
    await message.reply_text(
        f"**Announcement System Status:**\n\n"
        f"Announcements: **{status}**\n"
        f"Announcement Channel: `{channel_id}`"
    )
