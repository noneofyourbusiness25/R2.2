#!/bin/bash

export API_ID="12345"
export API_HASH="dummy_api_hash"
export BOT_TOKEN="dummy_bot_token"
export CHANNELS="-1001234567890"
export ADMINS="123456789"
export DATABASE_URI="mongodb://localhost:27017/"
export LOG_CHANNEL="-1001234567890"
export SESSION="test_session"

python3 bot.py
