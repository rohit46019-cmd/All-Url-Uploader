class Translation(object):

    START_TEXT = """Hi {},
I am URL Uploader Bot!

Send me any **direct link**, I will download it and upload to Telegram as file/video.

Use /help to know how to use me."""

    HELP_TEXT = """**How to use me?**

1. Send me any direct download link
2. I will download the file/video
3. Then I will upload it to Telegram

Commands:
- /queue → Add multiple links
- /status → Show queue
- /clear → Clear queue"""

    DOWNLOAD_START = "Downloading…"
    UPLOAD_START = "Uploading…"
    UPLOADED_SUCCESS = "Uploaded successfully!"
