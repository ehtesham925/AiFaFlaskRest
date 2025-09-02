# Use official Python 3.11.9 image
FROM python:3.11.9-slim

# Set working directory inside the container
WORKDIR /app

# Prevent Python from writing pyc files and enable unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies (optional but useful for common Python packages)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency file first (to leverage Docker layer caching)
COPY requirements.txt .

# Install dependencies
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy all project files
COPY . .

# Expose port (optional, only if running web apps like Flask/FastAPI)
EXPOSE 5000

# Default command (change according to your app entry point)
CMD ["python", "main.py"]
