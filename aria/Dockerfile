# Aria — containerized API server.
# Build context is the repository root:  docker build -f aria/Dockerfile -t aria .
FROM python:3.11-slim

# git is needed to clone repositories for ingestion.
RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install dependencies first for better layer caching.
COPY aria/requirements.txt /app/aria/requirements.txt
RUN pip install --no-cache-dir -r /app/aria/requirements.txt

# Copy the Aria package.
COPY aria /app/aria

# Persist the index/clones here; mount a volume at this path in production.
ENV ARIA_DATA_DIR=/data
RUN mkdir -p /data
VOLUME ["/data"]

EXPOSE 8100

# Single worker: the vector index is held in memory per process.
CMD ["sh", "-c", "uvicorn aria.api:app --host 0.0.0.0 --port ${PORT:-8100} --workers 1"]
