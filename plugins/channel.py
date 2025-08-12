# Don't Remove Credit @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot @Tech_VJ
# Ask Doubt on telegram @KingVJ01

from pyrogram import Client, filters, enums
from info import CHANNELS
from database.ia_filterdb import save_files, unpack_new_file_id, clean_file_name
import asyncio

media_filter = filters.document | filters.video

# These will be accessed from bot.py to run the periodic saver
files_batch = []
lock = asyncio.Lock()
BATCH_SIZE = 50 

async def save_batch():
    """Saves the collected files to the database and clears the batch."""
    async with lock:
        if files_batch:
            await save_files(files_batch)
            files_batch.clear()

@Client.on_message(filters.chat(CHANNELS) & media_filter)
async def media(bot, message):
    """Adds new media from specified channels to the batch."""
    media = getattr(message, message.media.value, None)
    if not media:
        return

    file_id, file_ref = unpack_new_file_id(media.file_id)
    file_name = clean_file_name(media.file_name)
    
    async with lock:
        files_batch.append({
            '_id': file_id,
            'file_ref': file_ref,
            'file_name': file_name,
            'file_size': media.file_size,
            'file_type': message.media.value,
            'mime_type': media.mime_type,
            'caption': message.caption.html if message.caption else None,
            'file_id': file_id
        })

    if len(files_batch) >= BATCH_SIZE:
        await save_batch()
