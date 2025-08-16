# Dockerfile (root of repo)
FROM python:3.11-slim

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy source
COPY . /app
ENV PYTHONPATH=/app

# Cloud Run provides $PORT; Uvicorn listens on it
ENV PORT=8080
CMD ["python","-m","uvicorn","service.app:app","--host","0.0.0.0","--port","${PORT}"]
