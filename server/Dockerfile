# Dockerfile cho Willhaben Crawler Backend
FROM python:3.11-slim

# Thiết lập working directory
WORKDIR /app

# Cài đặt system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libxml2-dev \
    libxslt-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements và cài đặt Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY realtime_backend.py .
COPY config.py .
COPY start.py .

# Tạo user non-root để chạy ứng dụng
RUN useradd --create-home --shell /bin/bash app && chown -R app:app /app
USER app

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Khởi động ứng dụng
CMD ["python", "realtime_backend.py"]
