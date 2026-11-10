# Multi-Language Compilation & Execution Environment for Intervyn
FROM python:3.11-slim-bookworm

ENV DEBIAN_FRONTEND=noninteractive

# Install native C/C++ compiler (build-essential, g++, gcc), Node.js 22 LTS, and Java (default-jdk-headless)
RUN mkdir -p /usr/share/man/man1 /usr/share/man/man2 /usr/share/man/man7 && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
        curl \
        ca-certificates \
        gnupg \
        build-essential \
        g++ \
        gcc \
        default-jdk-headless && \
    curl -fsSL https://deb.nodesource.com/setup_22.x | bash - && \
    apt-get install -y --no-install-recommends nodejs && \
    rm -rf /var/lib/apt/lists/*

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
