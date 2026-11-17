# Build a real TypeScript compiler alongside the Node runtime.
FROM node:22-bookworm-slim AS typescript-toolchain
RUN npm install --global typescript@5.7.3

# Multi-Language Compilation & Execution Environment for Intervyn
FROM python:3.11-slim-bookworm

ENV DEBIAN_FRONTEND=noninteractive

# Fail the image build if a required advertised toolchain cannot be installed.
RUN mkdir -p /usr/share/man/man1 /usr/share/man/man2 /usr/share/man/man7 && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        g++ \
        gcc \
        gdb \
        default-jdk-headless && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY --from=typescript-toolchain /usr/local/bin/node /usr/local/bin/node
COPY --from=typescript-toolchain /usr/local/lib/node_modules/typescript /opt/typescript
ENV INTERVYN_TSC_PATH=/opt/typescript/bin/tsc
RUN node --version && node /opt/typescript/bin/tsc --version && javac -version && gdb --version

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy complete project repository
COPY . .

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV PORT=10000
ENV OPENBLAS_NUM_THREADS=1
ENV MKL_NUM_THREADS=1
ENV OMP_NUM_THREADS=1
ENV NUMEXPR_NUM_THREADS=1

EXPOSE 10000

# Start FastAPI with Uvicorn
CMD ["sh", "-c", "uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-10000}"]
