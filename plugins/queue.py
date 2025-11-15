import asyncio
from collections import deque
from pyrogram import Client, filters
from pyrogram.types import Message
from helper_funcs.help_uploadbot import humanbytes
from translation import Translation
import aiohttp
import os

# Global shared queue
QUEUE = deque()
IS_DOWNLOADING = False

# Track users who sent /queue and are expected to send links next
WAITING_FOR_LINKS = set()


# ---------------------------------------------------------
# /queue command — Ask user to send space-separated links
# ---------------------------------------------------------
@Client.on_message(filters.command("queue") & filters.private)
async def queue_cmd(bot, message: Message):

    WAITING_FOR_LINKS.add(message.from_user.id)

    await message.reply_text(
        "**Send me all your links in one message, separated by space.**\n\n"
        "Example:\n"
        "`https://a.com/1.mp4 https://b.com/2.mkv https://c.com/file.zip`"
    )

# ---------------------------------------------------------
# /queue_status — Show how many tasks are pending
# ---------------------------------------------------------
@Client.on_message(filters.command("queue_status") & filters.private)
async def queue_status_cmd(bot, message: Message):
    total = len(QUEUE)
    status = "🟢 Running" if IS_DOWNLOADING else "🔴 Idle"

    await message.reply_text(
        f"📊 **Queue Status**\n"
        f"• Status: **{status}**\n"
        f"• Pending Tasks: **{total}**",
        quote=True
    )


# ---------------------------------------------------------
# /clear — Clear the queue & stop downloads
# ---------------------------------------------------------
@Client.on_message(filters.command("clear") & filters.private)
async def clear_cmd(bot, message: Message):
    global IS_DOWNLOADING

    QUEUE.clear()
    IS_DOWNLOADING = False

    await message.reply_text(
        "🧹 **Queue cleared successfully!**\n"
        "All pending tasks removed.",
        quote=True
    )

# ---------------------------------------------------------
# Detect & Add Links
# ---------------------------------------------------------
@Client.on_message(filters.private & ~filters.command("queue"))
async def queue_add_links(bot, message: Message):

    user_id = message.from_user.id

    # User is NOT expected to send links
    if user_id not in WAITING_FOR_LINKS:
        return

    text = message.text.strip()
    links = text.split()

    valid = [i for i in links if i.startswith("http")]

    if not valid:
        await message.reply_text("❌ No valid URLs found. Send again.")
        return

    # Add to queue
    for url in valid:
        QUEUE.append({"user_id": user_id, "url": url})

    WAITING_FOR_LINKS.remove(user_id)

    await message.reply_text(f"✅ Added **{len(valid)}** links to queue. Processing…")

    # Start queue worker
    global IS_DOWNLOADING
    if not IS_DOWNLOADING:
        asyncio.create_task(queue_worker(bot))


# ---------------------------------------------------------
# Main Queue Worker
# ---------------------------------------------------------
async def queue_worker(bot):

    global IS_DOWNLOADING
    IS_DOWNLOADING = True

    while QUEUE:
        task = QUEUE.popleft()
        user_id = task["user_id"]
        url = task["url"]

        try:
            await bot.send_message(user_id, f"⬇️ **Downloading:**\n{url}")

            # Download file locally
            file_path = await download_url(url)

            if not file_path:
                await bot.send_message(user_id, "❌ Download failed!")
                continue

            # Upload to Telegram
            await bot.send_document(
                chat_id=user_id,
                document=file_path,
                caption=f"Uploaded:\n`{url}`"
            )

            # Cleanup
            os.remove(file_path)

            await bot.send_message(user_id, "✅ Done. Moving to next...")

        except Exception as e:
            await bot.send_message(user_id, f"⚠️ Error: `{e}`")

    IS_DOWNLOADING = False



# ---------------------------------------------------------
# Simple Downloader (similar style to repo)
# ---------------------------------------------------------
async def download_url(url):
    """ Download file from URL (aiohttp) """
    try:
        fname = url.split("/")[-1] or "file.bin"
        path = f"downloads/{fname}"

        os.makedirs("downloads", exist_ok=True)

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    return None

                with open(path, "wb") as f:
                    while True:
                        chunk = await resp.content.read(1024 * 64)
                        if not chunk:
                            break
                        f.write(chunk)

        return path

    except:
        return None
