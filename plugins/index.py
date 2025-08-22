# Don't Remove Credit @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot @Tech_VJ
# Ask Doubt on telegram @KingVJ01

import logging, re, asyncio
from utils import temp
from info import ADMINS
from pyrogram import Client, filters, enums
from pyrogram.errors import FloodWait, MessageNotModified
from pyrogram.errors.exceptions.bad_request_400 import ChannelInvalid, ChatAdminRequired, UsernameInvalid, UsernameNotModified, ChannelPrivate, MessageIdInvalid
from info import INDEX_REQ_CHANNEL as LOG_CHANNEL
from database.ia_filterdb import save_files, unpack_new_file_id, clean_file_name
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
lock = asyncio.Lock()

@Client.on_callback_query(filters.regex(r'^index'))
async def index_files_cb(bot, query):
    if query.data.startswith('index_cancel'):
        temp.CANCEL = True
        return await query.answer("Cancelling Indexing")
    _, raju, chat, lst_msg_id, from_user = query.data.split("#")
    if raju == 'reject':
        await query.message.delete()
        await bot.send_message(
            int(from_user),
            f'Your Submission for indexing {chat} has been decliened by our moderators.',
            reply_to_message_id=int(lst_msg_id)
        )
        return

    if lock.locked():
        return await query.answer('Wait until previous process complete.', show_alert=True)
    msg = query.message

    await query.answer('Processing...⏳', show_alert=True)
    if int(from_user) not in ADMINS:
        await bot.send_message(
            int(from_user),
            f'Your Submission for indexing {chat} has been accepted by our moderators and will be added soon.',
            reply_to_message_id=int(lst_msg_id)
        )
    try:
        await msg.edit(
            "Starting Indexing...",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton('Cancel', callback_data='index_cancel')]]
            )
        )
    except MessageIdInvalid:
        logger.warning("Message to edit was deleted.")
    try:
        chat = int(chat)
    except:
        chat = chat

    # Pre-flight check to see if the bot can access messages
    try:
        await bot.get_messages(chat, 1)
    except Exception as e:
        try:
            await msg.edit(f"Could not fetch messages from the channel.\n\n**Error:** `{e}`\n\nPlease make sure the bot is an admin in the channel and has the permission to read message history.")
        except MessageIdInvalid:
            logger.warning("Message to edit was deleted.")
        return

    await index_files_to_db(int(lst_msg_id), chat, msg, bot)


@Client.on_message(filters.private & filters.command('index'))
async def send_for_index(bot, message):
    vj = await bot.ask(message.chat.id, "**Now Send Me Your Channel Last Post Link Or Forward A Last Message From Your Index Channel.\n\nAnd You Can Set Skip Number By - /setskip yourskipnumber**")
    if vj.forward_from_chat and vj.forward_from_chat.type == enums.ChatType.CHANNEL:
        last_msg_id = vj.forward_from_message_id
        chat_id = vj.forward_from_chat.username or vj.forward_from_chat.id
    elif vj.text:
        regex = re.compile("(https://)?(t\.me/|telegram\.me/|telegram\.dog/)(c/)?(\d+|[a-zA-Z_0-9]+)/(\d+)$")
        match = regex.match(vj.text)
        if not match:
            return await vj.reply('Invalid link\n\nTry again by /index')
        chat_id = match.group(4)
        last_msg_id = int(match.group(5))
        if chat_id.isnumeric():
            chat_id  = int(("-100" + chat_id))
    else:
        return
    try:
        await bot.get_chat(chat_id)
    except ChannelInvalid:
        return await vj.reply('This may be a private channel / group. Make me an admin over there to index the files.')
    except (UsernameInvalid, UsernameNotModified):
        return await vj.reply('Invalid Link specified.')
    except Exception as e:
        logger.exception(e)
        return await vj.reply(f'Errors - {e}')
    try:
        k = await bot.get_messages(chat_id, last_msg_id)
    except:
        return await message.reply('Make Sure That Iam An Admin In The Channel, if channel is private')
    if k.empty:
        return await message.reply('This may be group and iam not a admin of the group.')

    if message.from_user.id in ADMINS:
        buttons = [[
            InlineKeyboardButton('Yes', callback_data=f'index#accept#{chat_id}#{last_msg_id}#{message.from_user.id}')
        ],[
            InlineKeyboardButton('close', callback_data='close_data')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        return await message.reply(
            f'Do you Want To Index This Channel/ Group ?\n\nChat ID/ Username: <code>{chat_id}</code>\nLast Message ID: <code>{last_msg_id}</code>',
            reply_markup=reply_markup
        )

    if type(chat_id) is int:
        try:
            link = (await bot.create_chat_invite_link(chat_id)).invite_link
        except ChatAdminRequired:
            return await message.reply('Make sure iam an admin in the chat and have permission to invite users.')
    else:
        link = f"@{vj.forward_from_chat.username}"
    buttons = [[
        InlineKeyboardButton('Accept Index', callback_data=f'index#accept#{chat_id}#{last_msg_id}#{message.from_user.id}')
    ],[
        InlineKeyboardButton('Reject Index', callback_data=f'index#reject#{chat_id}#{message.id}#{message.from_user.id}'),
    ]]
    reply_markup = InlineKeyboardMarkup(buttons)
    await bot.send_message(
        LOG_CHANNEL,
        f'#IndexRequest\n\nBy : {message.from_user.mention} (<code>{message.from_user.id}</code>)\nChat ID/ Username - <code> {chat_id}</code>\nLast Message ID - <code>{last_msg_id}</code>\nInviteLink - {link}',
        reply_markup=reply_markup
    )
    await message.reply('ThankYou For the Contribution, Wait For My Moderators to verify the files.')


@Client.on_message(filters.command('setskip') & filters.user(ADMINS))
async def set_skip_number(bot, message):
    if ' ' in message.text:
        _, skip = message.text.split(" ")
        try:
            skip = int(skip)
        except:
            return await message.reply("Skip number should be an integer.")
        await message.reply(f"Successfully set SKIP number as {skip}")
        temp.CURRENT = int(skip)
    else:
        await message.reply("Give me a skip number")


async def index_files_to_db(lst_msg_id, chat, msg, bot):
    total_files = 0
    duplicate = 0
    errors = 0
    deleted = 0
    no_media = 0
    unsupported = 0
    fetched_messages = 0
    files_batch = []
    batch_size = 200
    max_retries = 3
    retries = 0
    error_occured = False
    current = temp.CURRENT

    async with lock:
        while retries < max_retries:
            try:
                temp.CANCEL = False
                logger.info(f"Starting indexing from message ID: {current}")
                async for message in bot.iter_messages(chat, lst_msg_id, current):
                    if temp.CANCEL:
                        if files_batch:
                            saved, dup = await save_files(files_batch)
                            total_files += saved
                            duplicate += dup
                            files_batch.clear()
                        try:
                            await msg.edit(f"Successfully Cancelled!!\n\nSaved <code>{total_files}</code> files to dataBase!\nDuplicate Files Skipped: <code>{duplicate}</code>\nDeleted Messages Skipped: <code>{deleted}</code>\nNon-Media messages skipped: <code>{no_media + unsupported}</code>(Unsupported Media - `{unsupported}` )\nErrors Occurred: <code>{errors}</code>")
                        except MessageIdInvalid:
                            logger.warning("Message to edit was deleted.")
                        break

                    current = message.id
                    fetched_messages += 1

                    # Sleep for a short time to avoid flooding the API
                    await asyncio.sleep(1)

                    if fetched_messages % 30 == 0:
                        can = [[InlineKeyboardButton('Cancel', callback_data='index_cancel')]]
                        reply = InlineKeyboardMarkup(can)
                        try:
                            await msg.edit_text(
                                text=f"Total messages fetched: <code>{fetched_messages}</code>\nTotal messages saved: <code>{total_files}</code>\nDuplicate Files Skipped: <code>{duplicate}</code>\nDeleted Messages Skipped: <code>{deleted}</code>\nNon-Media messages skipped: <code>{no_media + unsupported}</code>(Unsupported Media - `{unsupported}` )\nErrors Occurred: <code>{errors}</code>",
                                reply_markup=reply
                            )
                        except (MessageNotModified, MessageIdInvalid):
                            pass

                    if message.empty:
                        deleted += 1
                        continue
                    elif not message.media:
                        no_media += 1
                        continue
                    elif message.media not in [enums.MessageMediaType.VIDEO, enums.MessageMediaType.AUDIO, enums.MessageMediaType.DOCUMENT]:
                        unsupported += 1
                        continue

                    media = getattr(message, message.media.value, None)
                    if not media:
                        unsupported += 1
                        continue

                    file_id, file_ref = unpack_new_file_id(media.file_id)
                    file_name = clean_file_name(media.file_name)

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

                    if len(files_batch) >= batch_size:
                        saved, dup = await save_files(files_batch)
                        total_files += saved
                        duplicate += dup
                        files_batch.clear()

                # If loop completes without error, break the while loop
                break

            except FloodWait as e:
                logger.warning(f"FloodWait error at message ID {current}. Waiting for {e.value} seconds.")
                try:
                    await msg.edit(f"Telegram is slowing me down. Waiting {e.value} seconds...")
                except MessageIdInvalid:
                    logger.warning("Message to edit was deleted.")
                await asyncio.sleep(e.value)

            except ChannelPrivate:
                retries += 1
                logger.warning(f"ChannelPrivate error at message ID {current}. Retrying in 60 seconds... (Attempt {retries}/{max_retries})")
                try:
                    await msg.edit(f"Telegram is slowing me down. Waiting 60 seconds... (Attempt {retries}/{max_retries})")
                except MessageIdInvalid:
                    logger.warning("Message to edit was deleted.")
                await asyncio.sleep(60)

            except Exception as e:
                logger.exception(f"An error occurred at message ID {current}: {e}")
                try:
                    await msg.edit(f'Error: {e}')
                except MessageIdInvalid:
                    logger.warning("Message to edit was deleted.")
                error_occured = True
                break

        if retries >= max_retries:
            try:
                await msg.edit("Failed to index files after multiple retries due to repeated channel access errors. Please try again later.")
            except MessageIdInvalid:
                logger.warning("Message to edit was deleted.")
            error_occured = True

        if not error_occured:
            if files_batch:
                saved, dup = await save_files(files_batch)
                total_files += saved
                duplicate += dup
            try:
                await msg.edit(f'Succesfully saved <code>{total_files}</code> to dataBase!\nDuplicate Files Skipped: <code>{duplicate}</code>\nDeleted Messages Skipped: <code>{deleted}</code>\nNon-Media messages skipped: <code>{no_media + unsupported}</code>(Unsupported Media - `{unsupported}` )\nErrors Occurred: <code>{errors}</code>')
            except MessageIdInvalid:
                logger.warning("Message to edit was deleted.")
