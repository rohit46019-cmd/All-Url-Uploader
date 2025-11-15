import os
import logging
from pyrogram.raw.all import layer
from pyrogram import Client, idle, __version__

from config import Config

logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

logging.getLogger("pyrogram").setLevel(logging.WARNING)

# -----------------------------
# ✔ NO CHANGE — Directory check
# -----------------------------
if not os.path.isdir(Config.DOWNLOAD_LOCATION):
    os.makedirs(Config.DOWNLOAD_LOCATION)

# -----------------------------
# ✔ NO CHANGE — Config validation
# -----------------------------
if not Config.BOT_TOKEN:
    logger.error("Please set BOT_TOKEN in config.py or as env var")
    quit(1)

if not Config.API_ID:
    logger.error("Please set API_ID in config.py or as env var")
    quit(1)

if not Config.API_HASH:
    logger.error("Please set API_HASH in config.py or as env var")
    quit(1)


# -----------------------------------------------------
# 🟩 CHANGE / ADD — Cleaner plugin loading (recommended)
# Old: plugins=dict(root="plugins"),
# New: plugins={"root": "plugins"},
# -----------------------------------------------------
bot = Client(
    "All-Url-Uploader",
    api_id=Config.API_ID,
    api_hash=Config.API_HASH,
    bot_token=Config.BOT_TOKEN,
    workers=50,
    plugins={"root": "plugins"},  # 🟩 UPDATED
)


# -----------------------------------------------------
# ✔ NO DELETE — START BOT
# -----------------------------------------------------
bot.start()
logger.info("Bot has started.")

# -----------------------------------------------------
# ✔ NO CHANGE — Logging Bot Info
# -----------------------------------------------------
logger.info("**Bot Started**\n\n**Pyrogram Version:** %s \n**Layer:** %s", __version__, layer)
logger.info("Developed by github.com/kalanakt Sponsored by www.netronk.com")

# -----------------------------------------------------
# ✔ NO CHANGE — keep idle()
# -----------------------------------------------------
idle()

# -----------------------------------------------------
# ✔ NO CHANGE — Stop bot
# -----------------------------------------------------
bot.stop()
logger.info("Bot Stopped ;)")
