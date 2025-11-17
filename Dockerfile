# Best Buy Scraper Server - Production Dockerfile
FROM python:3.13-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    chromium-browser \
    chromium-chromedriver \
    && rm -rf /var/lib/apt/lists/*

# Copy scraper files
COPY n8n_list_scraper.py .
COPY n8n_main_scraper.py .
COPY scraper_server.py .
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/health')" || exit 1

# Run the server
CMD ["python", "scraper_server.py"]
