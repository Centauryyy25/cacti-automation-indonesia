# CactiAutomation Dockerfile
# Multi-stage build for smaller production image

# ==========================================================================
# Stage 1: Builder - Install dependencies
# ==========================================================================
FROM python:3.11-slim as builder

WORKDIR /app

# Install system dependencies for building
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ==========================================================================
# Stage 2: Runtime - Production image
# ==========================================================================
FROM python:3.11-slim as runtime

WORKDIR /app

# Install runtime dependencies
# - chromium: for Selenium
# - chromium-driver: ChromeDriver
# - libgl1: for OpenCV
# - libglib2.0-0: for OpenCV
RUN apt-get update && apt-get install -y --no-install-recommends \
    chromium \
    chromium-driver \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Set Chrome/Chromium environment variables
ENV CHROME_BIN=/usr/bin/chromium
ENV CHROMEDRIVER_PATH=/usr/bin/chromedriver
ENV DISPLAY=:99

# Create non-root user for security
RUN groupadd -r cacti && useradd -r -g cacti cacti

# Create required directories
RUN mkdir -p /app/output /app/logs /app/models && \
    chown -R cacti:cacti /app

# Copy application code
COPY --chown=cacti:cacti . .

# Switch to non-root user
USER cacti

# Environment variables (can be overridden)
ENV ENV=production
ENV DEBUG=false
ENV HOST=0.0.0.0
ENV PORT=5000
ENV SELENIUM_HEADLESS=true
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# Expose port
EXPOSE ${PORT}

# Run with production WSGI server
CMD ["waitress-serve", "--host=0.0.0.0", "--port=5000", "web.app:app"]
