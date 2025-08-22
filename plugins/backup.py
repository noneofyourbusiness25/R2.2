import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import FloodWait
from info import ADMINS
from database.backup_db import (
    set_backup_channel, get_backup_channel, backup_on, backup_off, get_backup_status,
    update_last_backed_up_file, get_last_backed_up_file, pause_backup, resume_backup, is_backup_paused
)
from database.ia_filterdb import get_all_files, count_all_files

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
    last_backed_up = get_last_backed_up_file()
    paused = is_backup_paused()

    text = f"**Backup System Status:**\n\n"
    text += f"Automatic Backup: **{status}**\n"
    text += f"Backup Channel: `{channel_id}`\n"
    text += f"Last Backed Up File ID: `{last_backed_up}`\n"
    text += f"Backup Paused: **{paused}**"

    await message.reply_text(text)

async def send_file_safely(bot, chat_id, file_id, caption, file_type):
    """A helper function to send files and handle different media types."""
    try:
        if file_type == "video":
            await bot.send_video(chat_id=chat_id, video=file_id, caption=caption)
        elif file_type == "audio":
            await bot.send_audio(chat_id=chat_id, audio=file_id, caption=caption)
        else:
            await bot.send_document(chat_id=chat_id, document=file_id, caption=caption)
        return True
    except FloodWait as e:
        await asyncio.sleep(e.value)
        return await send_file_safely(bot, chat_id, file_id, caption, file_type)  # Retry after waiting
    except Exception as e:
        # Log the error but don't stop the backup process
        print(f"An error occurred while sending file {file_id}: {e}")
        return False


@Client.on_message(filters.command("backup_pause") & filters.user(ADMINS))
async def pause_backup_handler(bot: Client, message: Message):
    pause_backup()
    await message.reply_text("Backup process has been paused.")

@Client.on_message(filters.command("backup_resume") & filters.user(ADMINS))
async def resume_backup_handler(bot: Client, message: Message):
    resume_backup()
    await message.reply_text("Backup process has been resumed.")

@Client.on_message(filters.command("backup_all") & filters.user(ADMINS))
async def backup_all_handler(bot: Client, message: Message):
    backup_channel = get_backup_channel()
    if not backup_channel:
        await message.reply_text("Please set a backup channel first using /set_backup_channel.")
        return

    last_backed_up = get_last_backed_up_file()
    total_files = await count_all_files()

    if total_files == 0:
        await message.reply_text("There are no files in the database to backup.")
        return

    if last_backed_up:
        await message.reply_text(f"Resuming backup from the last saved point. Total files: {total_files}")
    else:
        await message.reply_text(f"Starting backup of {total_files} files. This may take a while...")

    backed_up_count = 0
    progress_update_interval = 500  # Update progress every 500 files

    async for file in get_all_files(last_id=last_backed_up):
        while is_backup_paused():
            await asyncio.sleep(10)  # Check every 10 seconds if backup is resumed

        file_id = file["file_id"]
        caption = file.get("caption", "")
        file_type = file.get("file_type")

        if await send_file_safely(bot, backup_channel, file_id, caption, file_type):
            backed_up_count += 1
            update_last_backed_up_file(file['_id'])

        if backed_up_count % progress_update_interval == 0:
            await message.reply_text(f"Backed up {backed_up_count} / {total_files} files.")

    await message.reply_text(f"Backup completed successfully! Total files backed up: {backed_up_count}")
