# Don't Remove Credit @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot @Tech_VJ
# Ask Doubt on telegram @KingVJ01

import os
import sys
import shutil
from pyrogram import Client, filters
from pyrogram.types import Message
from functools import wraps
from info import ADMINS
from database.users_chats_db import db

# Decorator to check if the user is an admin
def admin_only(func):
    @wraps(func)
    async def wrapped(client, message):
        if message.from_user.id not in ADMINS:
            await message.reply_text("You are not authorized to use this command.")
            return
        await func(client, message)
    return wrapped

@Client.on_message(filters.command("adminhelp") & filters.user(ADMINS))
async def admin_help(client, message):
    await message.reply_text("""
**Admin Commands:**

- `/restart` - Restart the bot.
- `/verification <on|off>` - Enable or disable user verification.
- `/verifyshortener <url> <api>` - Set the verification shortener URL and API.
- `/bot_settings` - View the current bot settings.
""")

@Client.on_message(filters.command("bot_settings") & filters.user(ADMINS))
@admin_only
async def get_settings_handler(client, message):
    settings = await db.get_bot_settings()
    await message.reply_text(
        f"**Bot Settings:**\n\n"
        f"**Verification System:** `{'Enabled' if settings.get('verify') else 'Disabled'}`\n"
        f"**Verification Shortener URL:** `{settings.get('verify_shortlink_url')}`\n"
        f"**Verification Shortener API:** `{settings.get('verify_shortlink_api')}`"
    )

@Client.on_message(filters.command("restart") & filters.user(ADMINS))
@admin_only
async def restart_bot(client, message):
    await message.reply_text("Bot is restarting...")
    try:
        shutil.rmtree("downloads")
    except:
        pass
    os.execl(sys.executable, sys.executable, "-m", "bot")

@Client.on_message(filters.command("verification") & filters.user(ADMINS))
@admin_only
async def verification_toggle(client, message):
    try:
        _, status = message.text.split()
        if status.lower() == "on":
            await db.update_bot_settings("verify", True)
            await message.reply_text("Verification has been enabled.")
        elif status.lower() == "off":
            await db.update_bot_settings("verify", False)
            await message.reply_text("Verification has been disabled.")
        else:
            await message.reply_text("Invalid status. Use `/verification on` or `/verification off`.")
    except ValueError:
        await message.reply_text("Usage: `/verification <on|off>`")

@Client.on_message(filters.command("verifyshortener") & filters.user(ADMINS))
@admin_only
async def verification_shortener_settings(client, message):
    try:
        _, url, api = message.text.split()
        await db.update_bot_settings("verify_shortlink_url", url)
        await db.update_bot_settings("verify_shortlink_api", api)

        # Read the settings back from the database to confirm
        settings = await db.get_bot_settings()
        new_url = settings.get("verify_shortlink_url")
        new_api = settings.get("verify_shortlink_api")

        await message.reply_text(
            f"**Success! Verification shortener has been updated.**\n\n"
            f"**New URL:** `{new_url}`\n"
            f"**New API:** `{new_api}`"
        )
    except ValueError:
        await message.reply_text("Invalid format. Use `/verifyshortener <url> <api>`.")
    except Exception as e:
        await message.reply_text(f"An error occurred: {e}")
