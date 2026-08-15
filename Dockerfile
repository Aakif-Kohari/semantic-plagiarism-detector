# Pin patch + distro so rebuilds don't silently pick up a newer python:3.11-slim.
FROM python:3.11.9-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgomp1 \
    tesseract-ocr \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Add ARG to dynamically choose requirements file (defaults to CPU-only for smaller images)
ARG REQS_FILE=requirements-no-torch.txt

# Use the ARG for copying and installing dependencies
COPY ${REQS_FILE} .
RUN pip install --upgrade pip && \
    pip install -r ${REQS_FILE}

COPY . .

EXPOSE 8501

CMD ["streamlit", "run", "src/asgi_app.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.headless=true"]
