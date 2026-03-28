FROM ghcr.io/astral-sh/uv:0.9.2-python3.13-bookworm-slim AS builder

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

COPY . .
RUN uv sync --frozen --no-dev


FROM python:3.13-slim-bookworm

COPY --from=builder /usr/local/bin/uv /usr/local/bin/uv

WORKDIR /app

COPY --from=builder /app /app

EXPOSE 8000
USER nobody
CMD ["uv", "run", "fastapi", "run", "main.py", "--host", "0.0.0.0", "--port", "8000"]
