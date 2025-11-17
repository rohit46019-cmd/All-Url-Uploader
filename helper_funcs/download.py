import os
import aiohttp
import asyncio
from pyrogram import Client
from pyrogram.errors import RPCError

# 1 MB chunk ( MUCH faster than 64KB )
CHUNK_SIZE = 1024 * 1024  


# -------------------------
# FAST DOWNLOAD FUNCTION
# -------------------------
async def download_file(url: str, output_folder: str = "downloads") -> str | None:
    """Super-fast downloader with big chunks."""
    os.makedirs(output_folder, exist_ok=True)

    filename = url.split("/")[-1].split("?")[0] or "file"
    temp_path = os.path.join(output_folder, filename + ".part")
    final_path = os.path.join(output_folder, filename)

    try:
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=None)
        ) as session:
            async with session.get(url) as response:
                if response.status != 200:
                    return None

                # High-speed buffered writing
                with open(temp_path, "wb", buffering=1024 * 1024) as f:
                    while True:
                        chunk = await response.content.read(CHUNK_SIZE)
                        if not chunk:
                            break
                        f.write(chunk)

        # Rename .part to final filename (safe & fast)
        os.replace(temp_path, final_path)
        return final_path

    except Exception as e:
        return None



# -------------------------
# FAST UPLOAD TO TELEGRAM
# -------------------------
async def upload_file(client: Client, chat_id: int, file_path: str, caption: str = ""):
    """Uploads a file very fast to Telegram."""
    try:
        await client.send_document(
            chat_id,
            document=file_path,
            caption=caption,
            force_document=True,
            disable_notification=True,
        )

    except RPCError as e:
        await client.send_message(chat_id, f"⚠️ Upload failed: `{e}`")

    finally:
        if os.path.exists(file_path):
            os.remove(file_path)



# -------------------------
# MAIN PROCESS FUNCTION
# -------------------------
async def process_url(client: Client, chat_id: int, url: str, cancel_flag_ref: dict):
    """Download -> Upload -> Cleanup"""

    # Cancel support
    if cancel_flag_ref.get("cancel", False):
        cancel_flag_ref["cancel"] = False
        await client.send_message(chat_id, "❌ Download cancelled.")
        return

    await client.send_message(chat_id, f"⬇️ Downloading:\n{url}")

    # FAST DOWNLOAD
    file_path = await download_file(url)

    if not file_path:
        await client.send_message(chat_id, "❌ Download failed!")
        return

    # FAST UPLOAD
    caption = f"Uploaded:\n`{url}`"
    await upload_file(client, chat_id, file_path, caption)