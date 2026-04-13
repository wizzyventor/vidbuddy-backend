# Use Python 3.11 as the base image
FROM python:3.11-slim

# NEW FEATURE: Manual System Dependency Installation
# This installs FFmpeg and Node.js (required for yt-dlp JavaScript extraction)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    && curl -sL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y nodejs \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory inside the container
WORKDIR /app

# Copy requirements and install Python libraries
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project (including app.py, index.html, and cookies.txt)
COPY . .

# Start the application using Gunicorn
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:10000"]
