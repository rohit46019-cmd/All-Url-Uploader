# download.py
import os
import time
import aiohttp
import asyncio
import subprocess
import mimetypes
from typing import Callable, Optional
from pyrogram import Client
from pyrogram.errors import RPCError

# Config
CHUNK_SIZE = 1024 * 1024          # 1 MB
WRITE_BUFFER = 1024 * 1024        # buffered file writes
PROGRESS_UPDATE_INTERVAL = 1.0    # seconds between progress edits


# -------------------------
# Utility: throttled progress reporter
# -------------------------
class ThrottledProgress:
    def __init__(self, update_cb: Callable[[int, int], None], interval: float = PROGRESS_UPDATE_INTERVAL):
        self._update_cb = update_cb
        self._interval = interval
        self._last = 0.0

    def maybe_update(self, downloaded: int, total: int):
        now = time.time()
        if now - self._last >= self._interval or downloaded == total:
            try:
                self._update_cb(downloaded, total)
            except Exception:
                pass
            self._last = now


# -------------------------
# FAST DOWNLOAD
# -------------------------
async def download_file(
    url: str,
    output_folder: str = "downloads",
    progress_cb: Optional[Callable[[int, int], None]] = None,
    cancel_flag_ref: Optional[dict] = None,
) -> Optional[str]:
    """
    Downloads a URL quickly in 1MB chunks.
    Returns final_path on success, None on failure.
    progress_cb(downloaded_bytes, total_bytes_or_0)
    cancel_flag_ref is optional dict {'cancel': bool}
    """
    os.makedirs(output_folder, exist_ok=True)

    # derive filename
    filename = url.split("/")[-1].split("?")[0] or "video.mp4"
    temp_path = os.path.join(output_folder, filename + ".part")
    final_path = os.path.join(output_folder, filename)

    throttler = ThrottledProgress(progress_cb) if progress_cb else None

    try:
        timeout = aiohttp.ClientTimeout(total=None)  # disable total timeout
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    return None

                # try to get content-length
                total = int(resp.headers.get("Content-Length") or 0)
                downloaded = 0

                # write to temp file with large buffer
                with open(temp_path, "wb", buffering=WRITE_BUFFER) as f:
                    while True:
                        # cancel check
                        if cancel_flag_ref and cancel_flag_ref.get("cancel", False):
                            # leave cancel flag reset to caller if desired
                            return None

                        chunk = await resp.content.read(CHUNK_SIZE)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded += len(chunk)
                        if throttler:
                            throttler.maybe_update(downloaded, total)

        # atomic rename
        os.replace(temp_path, final_path)
        # final progress update
        if throttler:
            throttler.maybe_update(os.path.getsize(final_path), os.path.getsize(final_path))
        return final_path

    except Exception:
        # cleanup partial
        try:
            if os.path.exists(temp_path):
                os.remove(temp_path)
        except Exception:
            pass
        return None


# -------------------------
# FFmpeg faststart fix (no re-encode)
# -------------------------
def fix_video_for_telegram(input_path: str) -> Optional[str]:
    """
    Produces a new file with -movflags +faststart so Telegram can stream it.
    Returns path to fixed file, or None on failure.
    """
    if not input_path.lower().endswith(".mp4"):
        return None

    output_path = input_path.replace(".mp4", "_fixed.mp4")
    cmd = [
        "ffmpeg",
        "-y",
        "-i", input_path,
        "-c", "copy",
        "-movflags", "+faststart",
        output_path,
    ]

    try:
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        if os.path.exists(output_path):
            return output_path
        return None
    except Exception:
        # if ffmpeg fails or not installed, return None
        try:
            if os.path.exists(output_path):
                os.remove(output_path)
        except Exception:
            pass
        return None


# -------------------------
# UPLOAD (video streaming when possible)
# -------------------------
async def upload_file(
    client: Client,
    chat_id: int,
    file_path: str,
    caption: str = "",
    progress_edit_message=None,
    cancel_flag_ref: Optional[dict] = None,
):
    """
    Uploads file to telegram. If mp4, attempt to fix metadata and send as streamable video.
    progress_edit_message should be a pyrogram Message object (used for .edit_text).
    cancel_flag_ref is optional dict {'cancel': bool}
    """
    mime, _ = mimetypes.guess_type(file_path)
    is_mp4 = mime == "video/mp4" or file_path.lower().endswith(".mp4")

    # helper to edit progress (safe)
    def safe_edit(text: str):
        if progress_edit_message:
            try:
                progress_edit_message.edit_text(text)
            except Exception:
                pass

    try:
        # if mp4 try ffmpeg fix
        to_upload = file_path
        fixed_path = None
        if is_mp4:
            fixed = fix_video_for_telegram(file_path)
            if fixed:
                fixed_path = fixed
                to_upload = fixed_path

        # Progress callback for pyrogram upload (v2 style)
        async def _progress(current, total):
            if cancel_flag_ref and cancel_flag_ref.get("cancel", False):
                # Pyrogram doesn't directly stop an in-progress upload. We can just return and let user
                # decide to ignore further actions; upload will still finish. For a hard cancel you'd need
                # a different approach (terminate process/container).
                return
            # throttle with time checks could be added, but pyrogram progress callback frequency is fine
            if progress_edit_message:
                percent = (current / total * 100) if total else 0
                try:
                    await progress_edit_message.edit_text(
                        f"⬆️ Uploading: {current/1024/1024:.2f} / {total/1024/1024:.2f} MB ({percent:.1f}%)"
                    )
                except Exception:
                    pass

        # choose upload method
        if is_mp4:
            # send as video with streaming support
            if progress_edit_message:
                await progress_edit_message.edit_text("⬆️ Uploading (video, streamable)...")
            await client.send_video(
                chat_id=chat_id,
                video=to_upload,
                caption=caption,
                supports_streaming=True,
                progress=_progress,
                progress_args=()
            )
        else:
            if progress_edit_message:
                await progress_edit_message.edit_text("⬆️ Uploading (document)...")
            await client.send_document(
                chat_id=chat_id,
                document=to_upload,
                caption=caption,
                progress=_progress,
                progress_args=()
            )

        safe_edit("✅ Uploaded successfully.")

    except RPCError as e:
        safe_edit(f"⚠️ Upload failed: {e}")
    except Exception as e:
        safe_edit(f"⚠️ Upload error: {e}")
    finally:
        # cleanup uploaded files
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception:
            pass
        # cleanup fixed file if exists
        try:
            if 'fixed_path' in locals() and fixed_path and os.path.exists(fixed_path):
                os.remove(fixed_path)
        except Exception:
            pass


# -------------------------
# Combined process_url (download -> ffmpeg fix -> upload -> cleanup)
# -------------------------
async def process_url(
    client: Client,
    chat_id: int,
    url: str,
    cancel_flag_ref: Optional[dict] = None,
):
    """
    Full pipeline:
    - sends initial "Downloading..." message
    - downloads with progress updates
    - fixes mp4 for streaming (ffmpeg -movflags +faststart)
    - uploads as streamable video when possible
    - cleans up
    """
    if cancel_flag_ref is None:
        cancel_flag_ref = {}

    # Initial message
    status_msg = await client.send_message(chat_id, f"⬇️ Preparing to download:\n{url}")

    # progress callback for download (updates status_msg)
    def download_progress_cb(downloaded, total):
        try:
            if total:
                percent = downloaded / total * 100
                text = f"⬇️ Downloading: {downloaded/1024/1024:.2f} / {total/1024/1024:.2f} MB ({percent:.1f}%)"
            else:
                text = f"⬇️ Downloading: {downloaded/1024/1024:.2f} MB"
            # edit synchronously using pyrogram in event loop
            asyncio.get_event_loop().create_task(status_msg.edit_text(text))
        except Exception:
            pass

    # Start download
    file_path = await download_file(url, output_folder="downloads", progress_cb=download_progress_cb, cancel_flag_ref=cancel_flag_ref)

    if not file_path:
        # download failed or cancelled
        if cancel_flag_ref.get("cancel", False):
            await status_msg.edit_text("❌ Download cancelled.")
            cancel_flag_ref["cancel"] = False
        else:
            await status_msg.edit_text("❌ Download failed.")
        return

    # Small pause to ensure message edits don't collide
    await asyncio.sleep(0.2)

    # Prepare caption
    caption = f"Uploaded:\n`{url}`"

    # Upload with status updates
    await status_msg.edit_text("🔧 Finalizing file for Telegram (faststart)...")

    # call upload (which will attempt ffmpeg fix internally)
    await upload_file(client, chat_id, file_path, caption=caption, progress_edit_message=status_msg, cancel_flag_ref=cancel_flag_ref)