FROM python:3.11-slim

# Update & install ffmpeg
RUN apt-get update -y && apt-get upgrade -y
RUN apt-get install -y ffmpeg

# Set working directory
WORKDIR /usr/src/app

# Copy all files
COPY . .

# Upgrade pip first
RUN python -m pip install --upgrade pip

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Ensure downloads folder exists
RUN mkdir -p downloads

# Unbuffered output for logs
ENV PYTHONUNBUFFERED=1

# Start the bot
CMD ["python", "bot.py"]