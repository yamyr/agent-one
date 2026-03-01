# Stage 1: Build Vue frontend
FROM node:24-slim AS ui-build
WORKDIR /build
COPY ui/package.json ui/package-lock.json ./
RUN npm ci
COPY ui/ ./
RUN npm run build

# Stage 2: Python backend + built UI
FROM python:3.14-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Install Python dependencies
COPY server/pyproject.toml server/uv.lock ./
RUN uv sync --frozen --no-dev --no-editable

# Copy server code
COPY server/app/ app/

# Copy built UI assets
COPY --from=ui-build /build/dist ui_dist/

CMD .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-4009}
