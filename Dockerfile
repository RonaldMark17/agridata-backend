# Use an official lightweight Python image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Set environment variables
# Prevents Python from writing .pyc files and ensures logs are sent to terminal
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Install system dependencies required for MySQL and general builds
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    pkg-config \
    default-libmysqlclient-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
# We copy this first to take advantage of Docker's cache layers
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the backend application code
COPY . .

# Create the uploads folder to ensure it exists for farmer profile images
RUN mkdir -p static/uploads

# Expose the port your Flask app runs on
EXPOSE 8080

# Start the application using Gunicorn for production-grade performance
# --workers 4: standard for 1-2 core CPUs
# --bind 0.0.0.0: ensures the app is accessible outside the container
CMD ["gunicorn", "--workers", "4", "--bind", "0.0.0.0:8080", "app:app"]