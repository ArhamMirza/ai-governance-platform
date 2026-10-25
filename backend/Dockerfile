# The API. Built for one purpose: `docker compose up` (see ../docker-compose.yml).
#
# bookworm, not the newest Debian: the OCR package pulls in OpenCV, which needs
# libGL and glib by their bookworm names.
FROM python:3.15-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# libgomp: the ONNX runtime behind search and reranking. libgl1 and glib: OpenCV,
# which the OCR package imports.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# The package and what it depends on.
COPY pyproject.toml ./
COPY app ./app
RUN pip install .

# What runs from the working directory rather than the installed package.
COPY alembic.ini ./
COPY alembic ./alembic
COPY docker-entrypoint.sh ./
# A checkout on Windows may have turned the line endings into CRLF, which the shell rejects.
RUN sed -i 's/\r$//' docker-entrypoint.sh && chmod +x docker-entrypoint.sh

# Everything the app keeps lives under /data (one volume): the database, the
# uploaded files, and the search models, which are downloaded the first time
# search or the assistant needs them rather than baked into the image.
ENV DATABASE_URL=sqlite:////data/ai_governance.db \
    EVIDENCE_STORAGE_DIR=/data/evidence \
    FASTEMBED_CACHE_PATH=/data/models \
    HF_HOME=/data/models/hf

RUN useradd --system --uid 10001 --home-dir /app app \
    && mkdir -p /data/evidence /data/models \
    && chown -R app:app /data /app
USER app
VOLUME /data

EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=5s --start-period=60s --retries=30 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health', timeout=4)"

ENTRYPOINT ["./docker-entrypoint.sh"]
