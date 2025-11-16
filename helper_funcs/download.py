import os
import aiohttp
from pyrogram import Client

# Folder to store temporary downloads
DOWNLOAD_FOLDER = "downloads"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

# Cancel flag, controlled from queue.py
CANCEL_FLAG = False

# ----------------------------
# Download a file from URL
# ----------------------------
async def download_file(url: str) -> str | None:  # <- Place here
    """
    Download a file from a URL using aiohttp.
    Returns local file path or None on failure.
    """
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


# ----------------------------
# Upload file to Telegram
# ----------------------------
async def upload_file(client: Client, chat_id: int, file_path: str, caption: str = ""):
    if not os.path.exists(file_path):
        await client.send_message(chat_id, "❌ File not found after download.")
        return

    video_exts = (".mp4", ".mkv", ".mov", ".webm")
    try:
        if file_path.lower().endswith(video_exts):
            await client.send_video(
                chat_id=chat_id,
                video=file_path,
                supports_streaming=True,
                caption=caption
            )
        else:
            await client.send_document(
                chat_id=chat_id,
                document=file_path,
                caption=caption
            )
    except Exception as e:
        await client.send_message(chat_id, f"⚠️ Upload failed: {e}")
    finally:
        try:
            os.remove(file_path)
        except:
            pass


# ----------------------------
# Full download -> upload process
# ----------------------------
async def process_url(client: Client, chat_id: int, url: str, cancel_flag_ref: dict):
    if cancel_flag_ref.get("cancel", False):
        cancel_flag_ref["cancel"] = False
        await client.send_message(chat_id, "❌ Download cancelled.")
        return

    await client.send_message(chat_id, f"⬇️ Downloading:\n{url}")

    file_path = await download_file(url)
    if not file_path:
        await client.send_message(chat_id, "❌ Download failed!")
        return

    await upload_file(client, chat_id, file_path, caption=f"Uploaded:\n`{url}`")