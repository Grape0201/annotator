FROM ghcr.io/astral-sh/uv:alpine

WORKDIR /app

# Copy only package metadata first for efficient rebuilds
COPY pyproject.toml /app/
COPY src /app/src

RUN uv sync --no-dev
RUN uv run annotator download-font

EXPOSE 8000

ENTRYPOINT ["uv", "run", "annotator", "start-server", "--host", "0.0.0.0", "--port", "8000"]
