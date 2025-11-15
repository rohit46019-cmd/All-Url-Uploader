import os
import threading
from flask import Flask
from pyrogram import Client, idle

app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is running"

def run_flask():
    port = int(os.environ.get("PORT", 5000))  # Use environment PORT or default 5000
    app.run(host="0.0.0.0", port=port)

# Start Flask server in a separate thread
threading.Thread(target=run_flask).start()

# Initialize your bot client here
bot = Client(
    "All-Url-Uploader",
    api_id=Config.API_ID,
    api_hash=Config.API_HASH,
    bot_token=Config.BOT_TOKEN,
    workers=50,
    plugins=dict(root="plugins"),
)

bot.start()
print("Bot started")

idle()  # keep the bot running

bot.stop()
print("Bot stopped")
