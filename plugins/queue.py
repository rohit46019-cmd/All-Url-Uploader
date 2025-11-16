import os
import asyncio
from collections import deque
from pyrogram import Client, filters
from pyrogram.types import Message
import aiohttp
from config import Config
import subprocess
from typing import Optional

# --------------------------
# Global Variables
# --------------------------
QUEUE = deque()  # Stores tasks: {"user_id": ..., "url": ...}
IS_DOWNLOADING = False
WAITING_FOR_LINKS = set()  # Users who triggered /queue
USER_CANCEL_FLAGS = {}      # Per-user cancel flags

DOWNLOAD_FOLDER = "downloads"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

# --------------------------
# /queue — Ask user to send links
# --------------------------
@Client.on_message(filters.command("queue") & filters.private)
async def queue_cmd(client: Client, message: Message):
    user_id = message.from_user.id
    WAITING_FOR_LINKS.add(user_id)
    await message.reply(
        "**Send all your links in ONE MESSAGE, separated by spaces.**\n\n"
        "Example:\n"
        "`https://a.com/1.mp4 https://b.com/2.mkv https://c.com/file.zip`"
    )

# --------------------------
# /cancel — Cancel all tasks for the user
# --------------------------
@Client.on_message(filters.command("cancel") & filters.private)
async def cancel_cmd(client: Client, message: Message):
    user_id = message.from_user.id
    USER_CANCEL_FLAGS[user_id] = True
    # Remove pending tasks from queue
    global QUEUE
    QUEUE = deque([t for t in QUEUE if t["user_id"] != user_id])
    await message.reply("🚫 Your downloads have been cancelled and queue cleared.")

# --------------------------
# /queue_status — Show queue condition
# --------------------------
@Client.on_message(filters.command("queue_status") & filters.private)
async def queue_status_cmd(client: Client, message: Message):
    user_id = message.from_user.id
    total = sum(1 for t in QUEUE if t["user_id"] == user_id)
    status = "🟢 Running" if IS_DOWNLOADING else "🔴 Idle"
    await message.reply(
        f"📊 **Queue Status**\n"
        f"• Status: **{status}**\n"
        f"• Your Pending Tasks: **{total}**"
    )

# --------------------------
# /clear — Clear all pending tasks for the user
# --------------------------
@Client.on_message(filters.command("clear") & filters.private)
async def clear_cmd(client: Client, message: Message):
    user_id = message.from_user.id
    global QUEUE
    QUEUE = deque([t for t in QUEUE if t["user_id"] != user_id])
    await message.reply("🧹 Your queue cleared! Pending tasks removed.")

# --------------------------
# Detect message with links after /queue
# --------------------------
@Client.on_message(
    filters.private & ~filters.command(["queue", "cancel", "clear", "queue_status"])
)
async def queue_add_links(client: Client, message: Message):
    user_id = message.from_user.id
    if user_id not in WAITING_FOR_LINKS:
        return

    links = message.text.strip().split()
    valid_links = [l for l in links if l.startswith("http")]

    if not valid_links:
        await message.reply("❌ No valid URLs found. Send again.")
        return

    for url in valid_links:
        QUEUE.append({"user_id": user_id, "url": url})

    WAITING_FOR_LINKS.remove(user_id)
    await message.reply(f"✅ Added **{len(valid_links)}** links. Processing...")

    global IS_DOWNLOADING
    if not IS_DOWNLOADING:
        asyncio.create_task(queue_worker(client))

# --------------------------
# Queue Worker — downloads & uploads files
# --------------------------
async def queue_worker(client: Client):
    global IS_DOWNLOADING
    IS_DOWNLOADING = True

    while QUEUE:
        task = QUEUE.popleft()
        user_id = task["user_id"]
        url = task["url"]

        # Check if user cancelled
        if USER_CANCEL_FLAGS.get(user_id, False):
            USER_CANCEL_FLAGS[user_id] = False
            await client.send_message(user_id, "❌ Download cancelled.")
            continue

        try:
            await client.send_message(user_id, f"⬇️ **Downloading:**\n{url}")
            file_path = await download_file(url)

            if not file_path:
                await client.send_message(user_id, "❌ Download failed!")
                continue

            # Detect video streaming support
            video_exts = (".mp4", ".mkv", ".mov", ".webm")
            if file_path.lower().endswith(video_exts):
                stream_path = await convert_to_mp4(file_path)
                await client.send_video(
                    chat_id=user_id,
                    video=stream_path,
                    supports_streaming=True,
                    caption=f"Uploaded:\n`{url}`"
                )
                os.remove(stream_path)
            else:
                await client.send_document(
                    chat_id=user_id,
                    document=file_path,
                    caption=f"Uploaded:\n`{url}`"
                )

            os.remove(file_path)
            await client.send_message(user_id, "✅ Done. Moving to next...")

        except Exception as e:
            await client.send_message(user_id, f"⚠️ Error: `{e}`")

    IS_DOWNLOADING = False

# --------------------------
# Download file using aiohttp
# --------------------------
async def download_file(url: str) -> Optional[str]:
    filename = url.split("/")[-1] or "file.bin"
    path = os.path.join(DOWNLOAD_FOLDER, filename)

    try:
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
    except Exception as e:
        print(f"Download failed: {e}")
        return None

# --------------------------
# Convert video to MP4 for streaming
# --------------------------
async def convert_to_mp4(file_path: str) -> str:
    if file_path.lower().endswith(".mp4"):
        return file_path

    new_path = os.path.splitext(file_path)[0] + ".mp4"
    cmd = [
        "ffmpeg", "-y", "-i", file_path,
        "-c:v", "libx264", "-c:a", "aac",
        "-preset", "fast",
        new_path
    ]
    process = await asyncio.create_subprocess_exec(*cmd)
    await process.communicate()
    return new_path