# backend/Dockerfile
FROM python:3.12-slim

# Prevent Python from writing pyc files and enforce unbuffered stdout logging
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies required for gevent and typical ML libraries
RUN apt-get update && apt-get install -y gcc g++ && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the backend source code
COPY . /app/backend/

# Expose the FastAPI port
EXPOSE 8000