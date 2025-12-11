# Multi-stage Dockerfile for IndexTTS2 FastAPI wrapper
# Uses NVIDIA CUDA base image for GPU support

FROM nvidia/cuda:12.8.0-runtime-ubuntu22.04 AS base

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    git-lfs \
    curl \
    build-essential \
    python3.10 \
    python3.10-dev \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.cargo/bin:$PATH"

# Set working directory
WORKDIR /app

# Stage 1: Clone and install IndexTTS
FROM base AS indextts-install

# Clone IndexTTS repository
ARG INDEXTTS_REPO_URL=https://github.com/index-tts/index-tts.git
ARG INDEXTTS_REPO_PATH=/app/index-tts

RUN git clone ${INDEXTTS_REPO_URL} ${INDEXTTS_REPO_PATH} && \
    cd ${INDEXTTS_REPO_PATH} && \
    git lfs pull

# Install IndexTTS using uv pip (installs to system Python)
WORKDIR ${INDEXTTS_REPO_PATH}
RUN uv pip install -e .

# Stage 2: Install wrapper
FROM base AS wrapper-install

# Copy wrapper code
COPY . /app/wrapper

# Install wrapper dependencies
WORKDIR /app/wrapper
RUN uv pip install -e .

# Stage 3: Final runtime image
FROM base AS runtime

# Copy installed packages from previous stages
COPY --from=indextts-install /app/index-tts /app/index-tts
COPY --from=wrapper-install /root/.local /root/.local

# Set Python path to include IndexTTS
ENV PYTHONPATH="/app/index-tts:$PYTHONPATH" \
    PATH="/root/.local/bin:$PATH"

# Copy wrapper code
COPY . /app/wrapper
WORKDIR /app/wrapper

# Create checkpoints directory (will be mounted or auto-downloaded)
RUN mkdir -p /app/checkpoints

# Set default environment variables
ENV INDEXTTS_MODEL_DIR=/app/checkpoints \
    INDEXTTS_CFG_PATH=/app/checkpoints/config.yaml \
    INDEXTTS_AUTO_DOWNLOAD=true \
    INDEXTTS_HF_REPO=IndexTeam/IndexTTS-2 \
    INDEXTTS_USE_FP16=false \
    INDEXTTS_USE_CUDA_KERNEL=false

# Expose API port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the API
CMD ["uvicorn", "indextts_fastapi.api:app", "--host", "0.0.0.0", "--port", "8000"]

