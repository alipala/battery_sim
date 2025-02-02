# Use Python 3.9 slim image
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create static directory
RUN mkdir -p /app/static/js /app/static/css

# Copy static files and application code
COPY static/ /app/static/
COPY main.py .

# Expose port (Railway will override this)
EXPOSE 8000

# Command to run the application
CMD uvicorn main:app --host 0.0.0.0 --port $PORT --workers 4