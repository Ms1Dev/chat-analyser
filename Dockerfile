FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV UV_SYSTEM_PYTHON=1

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen

COPY . .

EXPOSE 8000

CMD ["sh", "-c", "uv run manage.py migrate --no-input && uv run manage.py collectstatic --no-input && uv run gunicorn chat_analyser.wsgi:application --bind 0.0.0.0:8000 --worker-class gthread --workers 2 --threads 4"]   