# CryptTraject FastAPI server — slim production image.
#
# Unlike docker/server.Dockerfile (used by the local dev compose), this
# image installs ONLY the server-side dependencies (requirements-server.txt,
# no PySide6/Qt) and only the `shared` + `server` packages. Result: a much
# lighter image suitable for a VPS.
#
# Multi-stage:
#   1. builder  — build the venv (with the C++ toolchain Pyfhel may need).
#   2. runtime  — slim image with just the venv + source.

# ---------- stage 1 — builder -------------------------------------------------
FROM python:3.11-slim AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1

# Pyfhel ships a prebuilt manylinux wheel for x86_64; on arm64 pip falls
# back to a source build which needs cmake + g++ + python headers.
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
        build-essential cmake git \
 && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /build

# Install the slim server requirements first so the heavy Pyfhel layer is
# cached as long as requirements-server.txt is unchanged.
COPY requirements-server.txt .
RUN pip install --upgrade pip \
 && pip install -r requirements-server.txt

# Copy only the packages the server actually needs. We do NOT run
# `pip install -e .` here: pyproject.toml pulls the client GUI scripts.
# Instead the runtime stage puts these on PYTHONPATH directly.
COPY shared shared
COPY server server

# ---------- stage 2 — runtime -------------------------------------------------
FROM python:3.11-slim AS runtime

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH="/app/shared:/app/server"

RUN apt-get update \
 && apt-get install -y --no-install-recommends libgomp1 \
 && rm -rf /var/lib/apt/lists/* \
 && useradd --create-home --shell /bin/bash crypt

COPY --from=builder /opt/venv /opt/venv
COPY --from=builder /build/shared /app/shared
COPY --from=builder /build/server /app/server

WORKDIR /app
USER crypt

EXPOSE 8000

CMD ["uvicorn", "crypttraject_server.api:app", \
     "--host", "0.0.0.0", "--port", "8000", \
     "--forwarded-allow-ips", "*"]
