import os
import aiohttp
import asyncio
import mimetypes
import subprocess
import json
from pyrogram import Client
from pyrogram.errors import RPCError


# -----------------------------------------------------
# FAST ASYNC DOWNLOADER
# -----------------------------------------------------
async def download_file(url: str, output_folder: str = "downloads") -> str | None:
    """Downloads a file from URL and saves it with correct extension."""

    os.makedirs(output_folder, exist_ok=True)

    # Extract name
    filename = url.split("/")[-1].split("?")[0]

    # If no filename → assign default mp4
    if "." not in filename:
        filename = "video.mp4"

    file_path = os.path.join(output_folder, filename)

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:

                if response.status != 200:
                    return None

                with open(file_path, "wb") as f:
                    while True:
                        chunk = await response.content.read(1024 * 128)
                        if not chunk:
                            break
                        f.write(chunk)

        return file_path

    except Exception:
        return None



# -----------------------------------------------------
# GET VIDEO METADATA (duration, width, height)
# -----------------------------------------------------
def get_video_metadata(path: str):
    try:
        cmd = [
            "ffprobe", "-v", "quiet",
            "-print_format", "json",
            "-show_format", "-show_streams",
            path
        ]
        output = subprocess.check_output(cmd).decode()
        info = json.loads(output)

        video_stream = next(
            (s for s in info["streams"] if s["codec_type"] == "video"),
            None
        )

        if video_stream:
            duration = float(info["format"].get("duration", 0))
            width = int(video_stream.get("width", 720))
            height = int(video_stream.get("height", 480))
            return duration, width, height

    except Exception:
        pass

    return 0, 720, 480



# -----------------------------------------------------
# UPLOAD AS REAL TELEGRAM STREAMABLE VIDEO
# -----------------------------------------------------
async def upload_file(client: Client, chat_id: int, file_path: str, caption: str = ""):
    """Uploads a video properly with metadata so Telegram plays it internally."""

    # FORCE MP4 EXTENSION
    if not file_path.lower().endswith(".mp4"):
        new_path = file_path + ".mp4"
        os.rename(file_path, new_path)
        file_path = new_path

    # FIX STREAMING HEADER (FFmpeg FASTSTART)
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
        subprocess.run(
            ffmpeg_cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True
        )
        final_path = fixed_path
    except:
        final_path = file_path  # fallback

    # GET VIDEO METADATA (DURATION + SIZE)
    duration, width, height = get_video_metadata(final_path)

    # SEND AS VIDEO
    try:
        await client.send_video(
            chat_id,
            video=final_path,
            caption=caption,
            duration=int(duration),
            width=width,
            height=height,
            supports_streaming=True
        )

    except RPCError as e:
        await client.send_message(chat_id, f"⚠️ Upload failed: `{e}`")

    finally:
        # CLEANUP
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
    """Handles full process: download → convert → upload"""

    if cancel_flag_ref.get("cancel", False):
        cancel_flag_ref["cancel"] = False
        await client.send_message(chat_id, "❌ Download cancelled.")
        return

    await client.send_message(chat_id, f"⬇️ Downloading:\n{url}")

    # DOWNLOAD
    file_path = await download_file(url)

    if not file_path:
        await client.send_message(chat_id, "❌ Download failed!")
        return

    # UPLOAD
    caption = f"Uploaded:\n`{url}`"
    await upload_file(client, chat_id, file_path, caption=caption)