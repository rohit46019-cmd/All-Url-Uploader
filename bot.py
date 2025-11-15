import os
import logging
import threading
from flask import Flask
from pyrogram.raw.all import layer
from pyrogram import Client, idle, __version__

from config import Config

# Configure logging first
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)
logging.getLogger("pyrogram").setLevel(logging.WARNING)

# Check config before anything else
if not Config.BOT_TOKEN:
    logger.error("Please set BOT_TOKEN in config.py or as env var")
    quit(1)
if not Config.API_ID:
    logger.error("Please set API_ID in config.py or as env var")
    quit(1)
if not Config.API_HASH:
    logger.error("Please set API_HASH in config.py or as env var")
    quit(1)

if not os.path.isdir(Config.DOWNLOAD_LOCATION):
    os.makedirs(Config.DOWNLOAD_LOCATION)

# Flask web server to satisfy deployment port requirement
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is running"

def run_flask():
    port = int(os.environ.get("PORT", 5000))  # default to 5000 if not set
    app.run(host="0.0.0.0", port=port)

# Start Flask server in a separate thread
threading.Thread(target=run_flask, daemon=True).start()

# Initialize Pyrogram Client only once
bot = Client(
    "All-Url-Uploader",
    api_id=Config.API_ID,
    api_hash=Config.API_HASH,
    bot_token=Config.BOT_TOKEN,
    workers=50,
    plugins=dict(root="plugins"),
)

# Start the bot
bot.start()
logger.info("Bot has started.")
logger.info("**Bot Started**\n\n**Pyrogram Version:** %s \n**Layer:** %s", __version__, layer)
logger.info("Developed by github.com/kalanakt Sponsored by www.netronk.com")

# Run idle to keep it alive until interrupted
idle()

# Stop the bot gracefully
bot.stop()
logger.info("Bot Stopped ;)")
