# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    build-essential \
    pkg-config \
    libavformat-dev \
    libavcodec-dev \
    libavdevice-dev \
    libavutil-dev \
    libswscale-dev \
    libswresample-dev \
    libavfilter-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/

# Create storage directories
RUN mkdir -p /app/storage/uploads \
    /app/storage/watermarks \
    /app/storage/captions \
    /app/storage/outputs

# Expose port
EXPOSE 8000

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV STORAGE_BASE_PATH=/app/storage
ENV UPLOADS_PATH=/app/storage/uploads
ENV WATERMARKS_PATH=/app/storage/watermarks
ENV CAPTIONS_PATH=/app/storage/captions
ENV OUTPUTS_PATH=/app/storage/outputs

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
