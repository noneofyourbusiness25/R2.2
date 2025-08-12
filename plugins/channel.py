# Don't Remove Credit @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot @Tech_VJ
# Ask Doubt on telegram @KingVJ01

from pyrogram import Client, filters
from info import CHANNELS
from database.ia_filterdb import save_files, unpack_new_file_id, clean_file_name
import asyncio

media_filter = filters.document | filters.video

files_batch = []
lock = asyncio.Lock()
BATCH_SIZE = 50 

async def save_batch():
    async with lock:
        if files_batch:
            await save_files(files_batch)
            files_batch.clear()

async def periodic_save():
    while True:
        await asyncio.sleep(60) # Save every 60 seconds
        await save_batch()

@Client.on_message(filters.chat(CHANNELS) & media_filter)
async def media(bot, message):
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
            'file_type': media.file_type,
            'mime_type': media.mime_type,
            'caption': message.caption.html if message.caption else None,
            'file_id': file_id
        })

    if len(files_batch) >= BATCH_SIZE:
        await save_batch()

# Start the periodic save task when the client starts
@Client.on_event("startup")
async def on_startup(client):
    asyncio.create_task(periodic_save())
