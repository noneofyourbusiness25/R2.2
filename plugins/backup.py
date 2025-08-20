import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import FloodWait
from info import ADMINS
from database.backup_db import set_backup_channel, get_backup_channel, backup_on, backup_off, get_backup_status
from database.ia_filterdb import get_all_files

@Client.on_message(filters.command("set_backup_channel") & filters.user(ADMINS))
async def set_backup_channel_handler(bot: Client, message: Message):
    try:
        channel_id = int(message.text.split(" ", 1)[1])
        set_backup_channel(channel_id)
        await message.reply_text(f"Backup channel has been set to `{channel_id}`.")
    except (IndexError, ValueError):
        await message.reply_text("Please provide a valid channel ID.")

@Client.on_message(filters.command("backup_on") & filters.user(ADMINS))
async def backup_on_handler(bot: Client, message: Message):
    backup_on()
    await message.reply_text("Automatic backup has been turned ON.")

@Client.on_message(filters.command("backup_off") & filters.user(ADMINS))
async def backup_off_handler(bot: Client, message: Message):
    backup_off()
    await message.reply_text("Automatic backup has been turned OFF.")

@Client.on_message(filters.command("backup_status") & filters.user(ADMINS))
async def backup_status_handler(bot: Client, message: Message):
    enabled, channel_id = get_backup_status()
    status = "ON" if enabled else "OFF"
    await message.reply_text(
        f"**Backup System Status:**\n\n"
        f"Automatic Backup: **{status}**\n"
        f"Backup Channel: `{channel_id}`"
    )

@Client.on_message(filters.command("backup_all") & filters.user(ADMINS))
async def backup_all_handler(bot: Client, message: Message):
    backup_channel = get_backup_channel()
    if not backup_channel:
        await message.reply_text("Please set a backup channel first using /set_backup_channel.")
        return

    files = await get_all_files()
    total_files = len(files)
    if total_files == 0:
        await message.reply_text("There are no files in the database to backup.")
        return

    await message.reply_text(f"Starting backup of {total_files} files. This may take a while...")

    for i, file in enumerate(files):
        try:
            await bot.send_document(
                chat_id=backup_channel,
                document=file["file_id"],
                caption=file.get("caption", "")
            )
            if (i + 1) % 100 == 0:
                await message.reply_text(f"Backed up {i + 1} / {total_files} files.")
            await asyncio.sleep(1)
        except FloodWait as e:
            await asyncio.sleep(e.x)
            await bot.send_document(
                chat_id=backup_channel,
                document=file["file_id"],
                caption=file.get("caption", "")
            )
        except Exception as e:
            await message.reply_text(f"An error occurred while backing up file with ID `{file['_id']}`: {e}")

    await message.reply_text("Backup completed successfully!")
