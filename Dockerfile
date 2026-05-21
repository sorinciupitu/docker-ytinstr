# syntax=docker/dockerfile:1.7
FROM python:3.9-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_NO_COMPILE=1 \
    PIP_ROOT_USER_ACTION=ignore

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
