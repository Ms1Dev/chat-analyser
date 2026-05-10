FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV UV_SYSTEM_PYTHON=1

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev nodejs npm \
    && rm -rf /var/lib/apt/lists/*

COPY package.json package-lock.json* ./
RUN npm install

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen

COPY . .

RUN npm run build

EXPOSE 8000

CMD ["sh", "-c", "uv run manage.py migrate --no-input && uv run manage.py collectstatic --no-input && uv run gunicorn chat_analyser.wsgi:application --bind 0.0.0.0:8000 --worker-class gthread --workers 2 --threads 4"]   