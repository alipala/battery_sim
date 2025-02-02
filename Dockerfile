FROM python:3.11-slim

WORKDIR /code

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Verify files exist
RUN ls -la /code && \
    ls -la /code/static && \
    ls -la /code/static/js && \
    ls -la /code/static/css

# Make sure static files are readable
RUN chmod -R 755 /code/static

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# Start the application
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT} --log-level debug