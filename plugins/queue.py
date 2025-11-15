import os
import asyncio
from collections import deque
from pyrogram import Client, filters
from pyrogram.types import Message
import aiohttp
from config import Config

# Global flags
CANCEL_FLAG = False

# Global shared queue
QUEUE = deque()
IS_DOWNLOADING = False

# Track users waiting to send links
WAITING_FOR_LINKS = set()

# ---------------------------------------------------------
# /cancel — Cancel all tasks + stop download
# ---------------------------------------------------------
@Client.on_message(filters.command(["cancel"]) & filters.private)
async def cancel_all_tasks(client, message):
    global CANCEL_FLAG, IS_DOWNLOADING
    CANCEL_FLAG = True
    QUEUE.clear()
    IS_DOWNLOADING = False

    await message.reply("🚫 All tasks cancelled!\nQueue cleared & current download stopped.")


# ---------------------------------------------------------
# /queue — Ask user to send links
# ---------------------------------------------------------
@Client.on_message(filters.command("queue") & filters.private)
async def queue_cmd(bot, message: Message):

    WAITING_FOR_LINKS.add(message.from_user.id)

    await message.reply_text(
        "**Send all your links in ONE MESSAGE, separated by spaces.**\n\n"
        "Example:\n"
        "`https://a.com/1.mp4 https://b.com/2.mkv https://c.com/file.zip`"
    )


# ---------------------------------------------------------
# /queue_status — Show queue condition
# ---------------------------------------------------------
@Client.on_message(filters.command("queue_status") & filters.private)
async def queue_status_cmd(bot, message: Message):
    total = len(QUEUE)
    status = "🟢 Running" if IS_DOWNLOADING else "🔴 Idle"

    await message.reply_text(
        f"📊 **Queue Status**\n"
        f"• Status: **{status}**\n"
        f"• Pending Tasks: **{total}**",
    )


# ---------------------------------------------------------
# /clear – Clear queue
# ---------------------------------------------------------
@Client.on_message(filters.command("clear") & filters.private)
async def clear_cmd(bot, message: Message):
    global IS_DOWNLOADING
    QUEUE.clear()
    IS_DOWNLOADING = False

    await message.reply_text(
        "🧹 Queue cleared!\nAll tasks removed."
    )


# ---------------------------------------------------------
# Detect link message after /queue
# ---------------------------------------------------------
@Client.on_message(filters.private & ~filters.command(["queue", "cancel", "clear", "queue_status"]))
async def queue_add_links(bot, message: Message):

    user_id = message.from_user.id

    # Only accept links if user has triggered /queue
    if user_id not in WAITING_FOR_LINKS:
        return

    text = message.text.strip()
    links = text.split()

    valid = [i for i in links if i.startswith("http")]

    if not valid:
        await message.reply_text("❌ No valid links found. Try again.")
        return

    # Add each link to queue
    for url in valid:
        QUEUE.append({"user_id": user_id, "url": url})

    WAITING_FOR_LINKS.remove(user_id)

    await message.reply_text(f"✅ Added **{len(valid)}** links. Starting process...")

    # Start queue worker
    global IS_DOWNLOADING
    if not IS_DOWNLOADING:
        asyncio.create_task(queue_worker(bot))


# ---------------------------------------------------------
# Queue Worker — Processes links one-by-one
# ---------------------------------------------------------
async def queue_worker(bot):
    global IS_DOWNLOADING, CANCEL_FLAG
    IS_DOWNLOADING = True

    while QUEUE:
        if CANCEL_FLAG:
            CANCEL_FLAG = False
            IS_DOWNLOADING = False
            return

        task = QUEUE.popleft()
        user_id = task["user_id"]
        url = task["url"]

        try:
            await bot.send_message(user_id, f"⬇️ **Downloading:**\n{url}")

            file_path = await download_url(url)

            if not file_path:
                await bot.send_message(user_id, "❌ Download failed!")
                continue

            await bot.send_document(
                chat_id=user_id,
                document=file_path,
                caption=f"Uploaded:\n`{url}`"
            )

            os.remove(file_path)

            await bot.send_message(user_id, "✅ Done. Moving to next...")

        except Exception as e:
            await bot.send_message(user_id, f"⚠️ Error: `{e}`")

    IS_DOWNLOADING = False


# ---------------------------------------------------------
# Simple Downloader
# ---------------------------------------------------------
async def download_url(url):
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
