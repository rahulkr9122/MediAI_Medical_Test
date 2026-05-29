# Use official Python lightweight image
FROM python:3.11-slim

# Install system dependencies for OCR and PDF processing
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /app

# Copy requirements and install them
COPY src/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY src/ ./src/

# Set working directory to src so app.py is easily runnable
WORKDIR /app/src

# Set environment variables for production
ENV FLASK_ENV=production
ENV PYTHONUNBUFFERED=1

# Expose the port (Render sets the PORT environment variable)
EXPOSE 5000

# Start Gunicorn (use the PORT environment variable if provided by Render)
CMD sh -c "gunicorn --bind 0.0.0.0:${PORT:-5000} app:app"
