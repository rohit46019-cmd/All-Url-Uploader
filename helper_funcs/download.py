import os
import aiohttp
import asyncio
from pyrogram import Client
from pyrogram.errors import RPCError


# -------------------------
# DOWNLOAD FILE FUNCTION
# -------------------------
async def download_file(url: str, output_folder: str = "downloads") -> str | None:
    """Downloads a file from a URL and returns its file path."""
    os.makedirs(output_folder, exist_ok=True)

    filename = url.split("/")[-1].split("?")[0] or "file"
    file_path = os.path.join(output_folder, filename)

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status != 200:
                    return None

                with open(file_path, "wb") as f:
                    while True:
                        chunk = await response.content.read(1024 * 64)
                        if not chunk:
                            break
                        f.write(chunk)

        return file_path

    except Exception:
        return None



# -------------------------
# UPLOAD FILE TO TELEGRAM
# -------------------------
async def upload_file(client: Client, chat_id: int, file_path: str, caption: str = ""):
    """Uploads a file to Telegram."""
    try:
        await client.send_document(
            chat_id,
            document=file_path,
            caption=caption
        )

    except RPCError as e:
        await client.send_message(chat_id, f"⚠️ Upload failed: `{e}`")

    finally:
        # cleanup
        if os.path.exists(file_path):
            os.remove(file_path)



# -------------------------
# FULL PROCESS FUNCTION
# -------------------------
async def process_url(client: Client, chat_id: int, url: str, cancel_flag_ref: dict):
    """Full process: download -> upload -> cleanup"""

    # Cancel check
    if cancel_flag_ref.get("cancel", False):
        cancel_flag_ref["cancel"] = False
        await client.send_message(chat_id, "❌ Download cancelled.")
        return

    # Send downloading message
    await client.send_message(chat_id, f"⬇️ Downloading:\n{url}")

    # Start download
    file_path = await download_file(url)

    if not file_path:
        await client.send_message(chat_id, "❌ Download failed!")
        return

    # Upload the file
    caption = f"Uploaded:\n`{url}`"
    await upload_file(client, chat_id, file_path, caption=caption)