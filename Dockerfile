# Pin patch + distro so rebuilds don't silently pick up a newer python:3.11-slim.
FROM python:3.11.9-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgomp1 \
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN pip install pip==24.0

COPY requirements.txt .
RUN pip install -r requirements.txt && \
    python -m nltk.downloader punkt_tab

COPY . .
RUN chown -R appuser:appuser /app

EXPOSE 8501
USER appuser

# Orchestrators (Docker Compose, Kubernetes) use this to know when the
# Streamlit app is actually ready to serve traffic.
#
# Note: the app also runs a background FastAPI server (src/api/app.py) on
# port 8000 which exposes /healthz, but that port isn't published by this
# image and the container's primary listener is Streamlit on 8501. We
# target Streamlit's own built-in /_stcore/health endpoint instead — the
# same endpoint already relied on by the "app" service healthcheck in
# docker-compose.yml — so both healthcheck definitions stay consistent
# and actually reachable.
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl --fail http://localhost:8501/_stcore/health || exit 1

CMD ["streamlit", "run", "src/asgi_app.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.headless=true", "--server.fileWatcherType=none"]