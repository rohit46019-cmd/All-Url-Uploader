import os
import aiohttp
from pyrogram import Client
from plugins.upload import upload_file  # <- Only import, do not define again!

DOWNLOAD_FOLDER = "downloads"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

async def download_file(url: str) -> str | None:
    """Download a file and return local path or None if failed."""
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

async def process_url(client: Client, chat_id: int, url: str, cancel_flag_ref: dict):
    """Full process: download -> upload -> cleanup"""
    if cancel_flag_ref.get("cancel", False):
        cancel_flag_ref["cancel"] = False
        await client.send_message(chat_id, "❌ Download cancelled.")
        return

    # GOOD (triple-quote, if you want multi-line)
await client.send_message(chat_id, f"""⬇️ Downloading:
{url}""")
    file_path = await download_file(url)
    if not file_path:
        await client.send_message(chat_id, "❌ Download failed!")
        return

    # Use modular upload from plugins/upload.py
    await upload_file(client, chat_id, file_path, caption=f"Uploaded:
`{url}`")