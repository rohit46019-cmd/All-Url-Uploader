import os
import asyncio
from collections import deque
from pyrogram import Client, filters
from pyrogram.types import Message
import aiohttp
from config import Config

# --------------------------
# Global Variables
# --------------------------
CANCEL_FLAG = False
QUEUE = deque()
IS_DOWNLOADING = False
WAITING_FOR_LINKS = set()

DOWNLOAD_FOLDER = "downloads"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)


# --------------------------
# /cancel — Cancel all tasks
# --------------------------
@Client.on_message(filters.command("cancel") & filters.private)
async def cancel_all_tasks(client, message: Message):
    global CANCEL_FLAG, IS_DOWNLOADING
    CANCEL_FLAG = True
    QUEUE.clear()
    IS_DOWNLOADING = False
    await message.reply(
        "🚫 All tasks cancelled!\nQueue cleared & current download stopped."
    )


# --------------------------
# /queue — Ask user to send links
# --------------------------
@Client.on_message(filters.command("queue") & filters.private)
async def queue_cmd(client, message: Message):
    WAITING_FOR_LINKS.add(message.from_user.id)
    await message.reply(
        "**Send all your links in ONE MESSAGE, separated by spaces.**\n\n"
        "Example:\n"
        "`https://a.com/1.mp4 https://b.com/2.mkv https://c.com/file.zip`"
    )


# --------------------------
# /queue_status — Show queue condition
# --------------------------
@Client.on_message(filters.command("queue_status") & filters.private)
async def queue_status_cmd(client, message: Message):
    total = len(QUEUE)
    status = "🟢 Running" if IS_DOWNLOADING else "🔴 Idle"
    await message.reply(
        f"📊 **Queue Status**\n"
        f"• Status: **{status}**\n"
        f"• Pending Tasks: **{total}**"
    )


# --------------------------
# /clear — Clear queue only
# --------------------------
@Client.on_message(filters.command("clear") & filters.private)
async def clear_cmd(client, message: Message):
    global IS_DOWNLOADING
    QUEUE.clear()
    IS_DOWNLOADING = False
    await message.reply("🧹 Queue cleared!\nAll pending tasks removed.")


# --------------------------
# Detect message with links
# --------------------------
@Client.on_message(
    filters.private & ~filters.command(["queue", "cancel", "clear", "queue_status"])
)
async def queue_add_links(client, message: Message):
    user_id = message.from_user.id

    if user_id not in WAITING_FOR_LINKS:
        return

    text = message.text.strip()
    links = text.split()
    valid_links = [link for link in links if link.startswith("http")]

    if not valid_links:
        await message.reply("❌ No valid URLs found. Send again.")
        return

    for url in valid_links:
        QUEUE.append({"user_id": user_id, "url": url})

    WAITING_FOR_LINKS.remove(user_id)
    await message.reply(f"✅ Added **{len(valid_links)}** links. Starting process...")

    global IS_DOWNLOADING
    if not IS_DOWNLOADING:
        asyncio.create_task(queue_worker(client))


# --------------------------
# Queue Worker — downloads & uploads files
# --------------------------
async def queue_worker(client: Client):
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
            await client.send_message(user_id, f"⬇️ **Downloading:**\n{url}")
            file_path = await download_url(url)

            if not file_path:
                await client.send_message(user_id, "❌ Download failed!")
                continue

            # Streamable video if MP4/MKV/MOV/WEBM
            video_exts = (".mp4", ".mkv", ".mov", ".webm")
            if file_path.lower().endswith(video_exts):
                await client.send_video(
                    chat_id=user_id,
                    video=file_path,
                    supports_streaming=True,
                    caption=f"Uploaded:\n`{url}`"
                )
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
# Download function using aiohttp
# --------------------------
async def download_url(url: str) -> str | None:
    try:
        filename = url.split("/")[-1] or "file.bin"
        path = os.path.join(DOWNLOAD_FOLDER, filename)

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
