import os
import aiohttp
import asyncio
import mimetypes
import subprocess
from pyrogram import Client
from pyrogram.errors import RPCError


# -----------------------------------------------------
# FAST ASYNC DOWNLOADER
# -----------------------------------------------------
async def download_file(url: str, output_folder: str = "downloads") -> str | None:
    """Downloads a file from URL and returns saved file path."""
    os.makedirs(output_folder, exist_ok=True)

    # Try to extract filename
    filename = url.split("/")[-1].split("?")[0]

    # If no filename present → generate one
    if "." not in filename:
        filename = "video.mp4"

    file_path = os.path.join(output_folder, filename)

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:

                if response.status != 200:
                    return None

                # fast chunk download
                with open(file_path, "wb") as f:
                    while True:
                        chunk = await response.content.read(1024 * 64)
                        if not chunk:
                            break
                        f.write(chunk)

        return file_path

    except Exception:
        return None



# -----------------------------------------------------
# UPLOAD AS TELEGRAM STREAMABLE VIDEO
# -----------------------------------------------------
async def upload_file(client: Client, chat_id: int, file_path: str, caption: str = ""):
    """Uploads file as real streamable video (NOT document)."""

    # 1. Force .mp4 extension (Telegram requirement)
    if not file_path.lower().endswith(".mp4"):
        new_path = file_path + ".mp4"
        os.rename(file_path, new_path)
        file_path = new_path

    # 2. Apply FFmpeg faststart – required for Telegram streaming
    fixed_path = file_path.replace(".mp4", "_fixed.mp4")

    ffmpeg_cmd = [
        "ffmpeg", "-y",
        "-i", file_path,
        "-c:v", "copy",
        "-c:a", "copy",
        "-movflags", "+faststart",
        fixed_path
    ]

    try:
        subprocess.run(ffmpeg_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        final_path = fixed_path
    except:
        # ffmpeg failed → send original
        final_path = file_path

    # 3. Upload using send_video() (NOT send_document)
    try:
        await client.send_video(
            chat_id,
            video=final_path,
            caption=caption,
            supports_streaming=True   # ⬅️ Important
        )

    except RPCError as e:
        await client.send_message(chat_id, f"⚠️ Upload failed: `{e}`")

    finally:
        # Cleanup temp files
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except:
            pass

        try:
            if os.path.exists(fixed_path):
                os.remove(fixed_path)
        except:
            pass



# -----------------------------------------------------
# FULL PROCESS (DOWNLOAD → FIX → UPLOAD)
# -----------------------------------------------------
async def process_url(client: Client, chat_id: int, url: str, cancel_flag_ref: dict):
    """Handles full process: download & upload"""

    # Cancel check
    if cancel_flag_ref.get("cancel", False):
        cancel_flag_ref["cancel"] = False
        await client.send_message(chat_id, "❌ Download cancelled.")
        return

    await client.send_message(chat_id, f"⬇️ Downloading:\n{url}")

    # Download
    file_path = await download_file(url)

    if not file_path:
        await client.send_message(chat_id, "❌ Download failed!")
        return

    # Upload
    caption = f"Uploaded:\n`{url}`"
    await upload_file(client, chat_id, file_path, caption=caption)