import math

def humanbytes(size):
    """Convert bytes to human readable format."""
    if not size:
        return "0B"
    power = 1024
    n = 0
    Dic_powerN = {0: 'B', 1: 'KB', 2: 'MB', 3: 'GB', 4: 'TB'}
    while size > power:
        size /= power
        n += 1
    return f"{round(size, 2)} {Dic_powerN[n]}"
    

async def progress(current, total, message, start):
    """Progress bar for uploads/downloads (optional)."""
    now = time.time()
    diff = now - start

    if diff % 10 == 0:
        percent = current * 100 / total
        speed = current / diff
        elapsed = round(diff)
        eta = round((total - current) / speed)
        progress_str = "{0}{1}".format(
            ''.join(["▰" for i in range(math.floor(percent / 10))]),
            ''.join(["▱" for i in range(10 - math.floor(percent / 10))])
        )
        tmp = progress_str + "\n"
        tmp += f"Progress: {round(percent,2)}%\n"
        tmp += f"Speed: {humanbytes(speed)}/s\n"
        tmp += f"ETA: {eta} seconds"

        try:
            await message.edit(text=tmp)
        except:
            pass
