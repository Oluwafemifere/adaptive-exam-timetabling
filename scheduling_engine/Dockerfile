#scheduling_engine\Dockerfile
# Use Python 3.12 slim as base image
FROM python:3.12-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the scheduling engine source code
COPY . .

# Create a non-root user
RUN useradd --create-home --shell /bin/bash scheduler
RUN chown -R scheduler:scheduler /app
USER scheduler

# Set Python path
ENV PYTHONPATH=/app

# Default command
CMD ["python", "-m", "scheduling_engine.main"]
