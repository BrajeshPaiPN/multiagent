# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Install system dependencies required for OCR (Tesseract & Poppler)
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-eng \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Expose a default port (though the cloud provider will override this)
EXPOSE 8000

# Command to run the FastAPI application using the dynamic PORT environment variable
CMD uvicorn api:app --host 0.0.0.0 --port ${PORT:-8000}
