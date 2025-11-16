import os
import asyncio
from collections import deque
from pyrogram import Client, filters
from pyrogram.types import Message
from typing import Optional
from helper_funcs.download import process_url, download_file

CANCEL_FLAG = False
QUEUE = deque()
IS_DOWNLOADING = False
WAITING_FOR_LINKS = set()

DOWNLOAD_FOLDER = "downloads"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)


@Client.on_message(filters.command("cancel") & filters.private)
async def cancel_all_tasks(client, message: Message):
    global CANCEL_FLAG, IS_DOWNLOADING
    CANCEL_FLAG = True
    QUEUE.clear()
    IS_DOWNLOADING = False
    await message.reply("🚫 All tasks cancelled!\nQueue cleared & current download stopped.")


@Client.on_message(filters.command("queue") & filters.private)
async def queue_cmd(client, message: Message):
    WAITING_FOR_LINKS.add(message.from_user.id)
    await message.reply(
        "**Send all your links in ONE MESSAGE, separated by spaces.**\n"
        "Example:\n"
        "`https://a.com/1.mp4 https://b.com/2.mkv https://c.com/file.zip`"
    )


@Client.on_message(filters.command("queue_status") & filters.private)
async def queue_status_cmd(client, message: Message):
    total = len(QUEUE)
    status = "🟢 Running" if IS_DOWNLOADING else "🔴 Idle"
    await message.reply(f"📊 **Queue Status**\n• Status: **{status}**\n• Pending Tasks: **{total}**")


@Client.on_message(filters.command("clear") & filters.private)
async def clear_cmd(client, message: Message):
    global IS_DOWNLOADING
    QUEUE.clear()
    IS_DOWNLOADING = False
    await message.reply("🧹 Queue cleared!\nAll pending tasks removed.")


@Client.on_message(filters.private & ~filters.command(["queue", "cancel", "clear", "queue_status"]))
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
            await process_url(client, user_id, url, {"cancel": CANCEL_FLAG})
        except Exception as e:
            await client.send_message(user_id, f"⚠️ Error: `{e}`")

    IS_DOWNLOADING = False