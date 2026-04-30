FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV PORT=7860

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY mastering ./mastering

RUN pip install --upgrade pip \
    && pip install -e ".[api,stems]"

EXPOSE 7860

CMD ["sh", "-c", "uvicorn mastering.api.app:app --host 0.0.0.0 --port ${PORT}"]
