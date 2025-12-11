# Multi-stage Dockerfile for IndexTTS2 FastAPI wrapper
# Uses NVIDIA CUDA base image for GPU support
# Optimized for minimal image size

# ============================================================================
# Stage 1: Builder base - contains all build dependencies
# ============================================================================
FROM nvidia/cuda:12.8.0-runtime-ubuntu22.04 AS builder-base

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    git-lfs \
    curl \
    build-essential \
    python3.10 \
    python3.10-dev \
    python3-pip \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.cargo/bin:$PATH"

# Set working directory
WORKDIR /app

# ============================================================================
# Stage 2: Install IndexTTS
# ============================================================================
FROM builder-base AS indextts-install

# Clone IndexTTS repository
ARG INDEXTTS_REPO_URL=https://github.com/index-tts/index-tts.git
ARG INDEXTTS_REPO_PATH=/app/index-tts

RUN git clone --depth 1 ${INDEXTTS_REPO_URL} ${INDEXTTS_REPO_PATH} && \
    cd ${INDEXTTS_REPO_PATH} && \
    git lfs pull && \
    # Remove .git directory to save space
    rm -rf .git && \
    # Remove unnecessary files
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true && \
    find . -type d -name "tests" -exec rm -rf {} + 2>/dev/null || true && \
    find . -type d -name "docs" -exec rm -rf {} + 2>/dev/null || true && \
    find . -type f -name "*.pyc" -delete 2>/dev/null || true

# Install IndexTTS using uv pip (installs to system Python)
WORKDIR ${INDEXTTS_REPO_PATH}
RUN uv pip install --system -e . && \
    # Clean up pip cache and temporary files
    uv pip cache purge 2>/dev/null || true && \
    rm -rf /tmp/* /var/tmp/*

# ============================================================================
# Stage 3: Install wrapper dependencies
# ============================================================================
FROM builder-base AS wrapper-install

# Copy wrapper code
COPY --chown=root:root pyproject.toml /app/wrapper/
COPY --chown=root:root indextts_fastapi/ /app/wrapper/indextts_fastapi/

# Install wrapper dependencies
WORKDIR /app/wrapper
RUN uv pip install --system -e . && \
    # Clean up pip cache and temporary files
    uv pip cache purge 2>/dev/null || true && \
    rm -rf /tmp/* /var/tmp/*

# ============================================================================
# Stage 4: Runtime base - minimal runtime image
# ============================================================================
FROM nvidia/cuda:12.8.0-runtime-ubuntu22.04 AS runtime-base

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Install only runtime dependencies (minimal)
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.10 \
    python3.10-minimal \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean \
    && rm -rf /tmp/* /var/tmp/*

# Set working directory
WORKDIR /app

# ============================================================================
# Stage 5: Final runtime image
# ============================================================================
FROM runtime-base AS runtime

# Copy IndexTTS installation (without .git and unnecessary files)
COPY --from=indextts-install --chown=root:root /app/index-tts /app/index-tts

# Copy Python packages from builder stages
# uv pip installs to /root/.local when using --system
# Merge packages from both stages
RUN mkdir -p /root/.local/lib/python3.10/site-packages /root/.local/bin
COPY --from=indextts-install --chown=root:root /root/.local/lib/python3.10/site-packages/ /root/.local/lib/python3.10/site-packages/
COPY --from=indextts-install --chown=root:root /root/.local/bin/ /root/.local/bin/
COPY --from=wrapper-install --chown=root:root /root/.local/lib/python3.10/site-packages/ /root/.local/lib/python3.10/site-packages/
COPY --from=wrapper-install --chown=root:root /root/.local/bin/ /root/.local/bin/

# Set PATH to include .local/bin
ENV PATH="/root/.local/bin:$PATH"

# Set Python path to include IndexTTS
ENV PYTHONPATH="/app/index-tts:$PYTHONPATH"

# Copy wrapper code
COPY --chown=root:root pyproject.toml /app/wrapper/
COPY --chown=root:root indextts_fastapi/ /app/wrapper/indextts_fastapi/
# Copy voice_mappings.json (optional - will be skipped if not in build context due to .dockerignore)
COPY --chown=root:root voice_mappings.json /app/wrapper/voice_mappings.json

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
CMD ["python3", "-m", "uvicorn", "indextts_fastapi.api:app", "--host", "0.0.0.0", "--port", "8000"]
