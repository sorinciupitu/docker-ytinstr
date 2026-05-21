# syntax=docker/dockerfile:1.7
FROM python:3.10-slim-bookworm

ARG DENO_VERSION=2.7.12
ARG TARGETARCH

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_NO_COMPILE=1 \
    PIP_ROOT_USER_ACTION=ignore

# Install the small runtime library required by torch/torchaudio.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates libgomp1 \
    && rm -rf /var/lib/apt/lists/*

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
