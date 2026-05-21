# syntax=docker/dockerfile:1.7
FROM gcc:12-bookworm AS gcc-runtime

FROM python:3.10-slim-bookworm

ARG DENO_VERSION=2.7.12
ARG TARGETARCH

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_NO_COMPILE=1 \
    PIP_ROOT_USER_ACTION=ignore \
    LD_LIBRARY_PATH=/usr/local/lib

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copy the small OpenMP runtime library required by torch/torchaudio without using apt.
RUN --mount=from=gcc-runtime,source=/usr/lib,target=/gcc-libs,readonly python - <<'PY'
import glob
import os
import shutil

matches = glob.glob("/gcc-libs/**/libgomp.so.1*", recursive=True)
if not matches:
    raise SystemExit("Could not find libgomp.so.1 in gcc runtime image")

source = os.path.realpath(matches[0])
destination = "/usr/local/lib/libgomp.so.1"
shutil.copy2(source, destination)
PY

# yt-dlp needs an external JavaScript runtime for full YouTube support.
RUN --mount=type=tmpfs,target=/tmp DENO_VERSION="${DENO_VERSION}" TARGETARCH="${TARGETARCH}" python - <<'PY'
import os
import stat
import urllib.request
import zipfile

version = os.environ["DENO_VERSION"]
target_arch = os.environ.get("TARGETARCH") or "arm64"
arch_map = {
    "amd64": "x86_64",
    "arm64": "aarch64",
}

try:
    deno_arch = arch_map[target_arch]
except KeyError as exc:
    raise SystemExit(f"Unsupported Docker target architecture for Deno: {target_arch}") from exc

archive_name = f"deno-{deno_arch}-unknown-linux-gnu.zip"
url = f"https://github.com/denoland/deno/releases/download/v{version}/{archive_name}"
archive_path = "/tmp/deno.zip"
install_path = "/usr/local/bin/deno"

urllib.request.urlretrieve(url, archive_path)
with zipfile.ZipFile(archive_path) as archive:
    archive.extract("deno", "/usr/local/bin")

os.chmod(install_path, os.stat(install_path).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
PY
RUN deno --version

# Set working directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN --mount=type=tmpfs,target=/tmp \
    python -m pip install --no-compile --prefer-binary torch==2.8.0 torchaudio==2.8.0 \
    && rm -rf /tmp/* /root/.cache/pip
RUN --mount=type=tmpfs,target=/tmp \
    python -m pip install --no-compile --prefer-binary -r requirements.txt \
    && rm -rf /tmp/* /root/.cache/pip

# Copy application code
COPY . .

# Create directories for downloads and output
RUN mkdir -p downloads output

# Run the bot
CMD ["python", "bot.py"]
