import os
import aiohttp
from pyrogram import Client

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


async def upload_file(client: Client, chat_id: int, file_path: str, caption: str = ""):
    """Upload file to Telegram (streamable video if possible)."""
    if not os.path.exists(file_path):
        await client.send_message(chat_id, "❌ File not found after download.")
        return

    try:
        video_exts = (".mp4", ".mkv", ".mov", ".webm")
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


async def process_url(client: Client, chat_id: int, url: str, cancel_flag_ref: dict):
    """Full process: download -> upload -> cleanup"""
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