async def process_url(client: Client, chat_id: int, url: str, cancel_flag_ref: dict):
    """Full process: download -> upload -> cleanup"""
    if cancel_flag_ref.get("cancel", False):
        cancel_flag_ref["cancel"] = False
        await client.send_message(chat_id, "❌ Download cancelled.")
        return

    # Proper indentation!
    await client.send_message(chat_id, f"⬇️ Downloading:
{url}")
    file_path = await download_file(url)
    if not file_path:
        await client.send_message(chat_id, "❌ Download failed!")
        return

    # Use modular upload from plugins/upload.py
    await upload_file(client, chat_id, file_path, caption=f"Uploaded:
`{url}`")