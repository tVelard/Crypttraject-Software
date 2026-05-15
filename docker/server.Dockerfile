# CryptTraject FastAPI server.
#
# Multi-stage build:
#   1. `builder`  installs Python deps into a venv (heavy, includes the
#      C++ toolchain Pyfhel needs in case a wheel is unavailable).
#   2. `runtime`  is a slim image that just copies the venv + the source
#      and exposes uvicorn on :8000.

# ---------- stage 1 — builder -------------------------------------------------
FROM python:3.11-slim AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1

# Pyfhel ships a prebuilt manylinux wheel for x86_64; on arm64 (Apple
# Silicon Docker) pip falls back to a source build which needs cmake +
# g++ + the python headers. Installing them here keeps the build portable.
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
        build-essential cmake git \
 && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /build

# Copy only the requirements first so Docker can cache the heavy
# Pyfhel install layer when only source files change.
COPY requirements.txt .
RUN pip install --upgrade pip \
 && pip install -r requirements.txt

# Now copy the source and install the local packages.
COPY pyproject.toml .
COPY shared shared
COPY client client
COPY server server
RUN pip install -e .

# ---------- stage 2 — runtime -------------------------------------------------
FROM python:3.11-slim AS runtime

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# libgomp is pulled in by numpy on some base images; ship it explicitly
# so the runtime image works even if the wheel changes its dep set.
RUN apt-get update \
 && apt-get install -y --no-install-recommends libgomp1 \
 && rm -rf /var/lib/apt/lists/* \
 && useradd --create-home --shell /bin/bash crypt

COPY --from=builder /opt/venv /opt/venv
COPY --from=builder /build /app

WORKDIR /app
USER crypt

EXPOSE 8000

# uvicorn rather than `python -m`: gives us proper signal handling +
# --forwarded-allow-ips for use behind nginx/the web service.
CMD ["uvicorn", "crypttraject_server.api:app", \
     "--host", "0.0.0.0", "--port", "8000", \
     "--forwarded-allow-ips", "*"]
