# Use Python 3.9 slim image
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Copy requirements file
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Create static directory
RUN mkdir -p static/js static/css

# Copy static files to the correct location
COPY static/js/main.js static/js/
COPY static/css/style.css static/css/
COPY index.html static/

# Expose port (Railway will override this)
EXPOSE 8000

# Command to run the application
CMD uvicorn main:app --host 0.0.0.0 --port $PORT --workers 4