# An example using multi-stage image builds to create a final image without uv.

# First, build the application in the `/app` directory.
# See `Dockerfile` for details.
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS builder
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

# Disable Python downloads, because we want to use the system interpreter
# across both images. If using a managed Python version, it needs to be
# copied from the build image into the final image; see `standalone.Dockerfile`
# for an example.
ENV UV_PYTHON_DOWNLOADS=0

WORKDIR /app
# Copy common dependencies first
COPY ./common/kafka-helper /common/kafka-helper
COPY ./common/redis-helper /common/redis-helper
COPY ./common/logger /common/logger

COPY ./websocket-server/uv.lock ./websocket-server/pyproject.toml ./
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=./websocket-server/uv.lock,target=uv.lock \
    --mount=type=bind,source=./websocket-server/pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project --no-dev

COPY ./websocket-server/websocket_server /app/websocket_server

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev


# Then, use a final image without uv
FROM python:3.13-slim-bookworm
# It is important to use the image that matches the builder, as the path to the
# Python executable must be the same, e.g., using `python:3.11-slim-bookworm`
# will fail.

# Install curl for health checks
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

# Copy the application from the builder
COPY --from=builder /app /app

# Place executables in the environment at the front of the path
ENV PATH="/app/.venv/bin:$PATH"

# Use `/app` as the working directory
WORKDIR /app

# Run the FastAPI application by default
# Using multiple workers for better concurrency (recommended: 2-4 workers per core)
CMD ["uvicorn", "websocket_server.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4", "--log-level", "info"]
