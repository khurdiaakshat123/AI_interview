# Multi-Language Compilation & Execution Environment for Intervyn
FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive

# Fix Debian-slim missing man directories and install compilers (g++, gcc, openjdk-17, nodejs)
RUN mkdir -p /usr/share/man/man1 /usr/share/man/man2 /usr/share/man/man7 && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        g++ \
        gcc \
        openjdk-17-jdk-headless \
        nodejs \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy complete project repository
COPY . .

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV PORT=10000

EXPOSE 10000

# Start FastAPI with Uvicorn
CMD ["sh", "-c", "uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-10000}"]
