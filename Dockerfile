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

# Install uv with retry logic and fallback to pip
RUN set -eux; \
    UV_INSTALLED=false; \
    for i in 1 2 3 4 5; do \
        if curl -LsSf --max-time 30 --retry 3 --retry-delay 2 https://astral.sh/uv/install.sh | sh; then \
            echo "uv installed successfully on attempt $i"; \
            UV_INSTALLED=true; \
            break; \
        else \
            echo "Attempt $i failed, retrying in 5 seconds..."; \
            sleep 5; \
        fi; \
    done; \
    if [ "$UV_INSTALLED" = "false" ]; then \
        echo "Failed to install uv via install script, using pip as fallback"; \
        pip install --no-cache-dir uv; \
        echo "uv installed via pip"; \
    fi; \
    # Verify uv is accessible (installs to /root/.local/bin by default)
    if [ -f /root/.local/bin/uv ]; then \
        chmod +x /root/.local/bin/uv; \
        /root/.local/bin/uv --version || true; \
    elif [ -f /root/.cargo/bin/uv ]; then \
        chmod +x /root/.cargo/bin/uv; \
        /root/.cargo/bin/uv --version || true; \
    elif command -v uv >/dev/null 2>&1; then \
        uv --version || true; \
    fi
ENV PATH="/root/.local/bin:/root/.cargo/bin:/usr/local/bin:$PATH"

# Set working directory
WORKDIR /app

# ============================================================================
# Stage 2: Install IndexTTS
# ============================================================================
FROM builder-base AS indextts-install

# Ensure PATH includes uv location
ENV PATH="/root/.local/bin:/root/.cargo/bin:/usr/local/bin:$PATH"

# Clone IndexTTS repository
# Note: This step is cached unless the repo URL changes
ARG INDEXTTS_REPO_URL=https://github.com/index-tts/index-tts.git
ARG INDEXTTS_REPO_PATH=/app/index-tts

RUN set +e; \
    # Clone with GIT_LFS_SKIP_SMUDGE to avoid LFS errors during clone
    GIT_LFS_SKIP_SMUDGE=1 git clone --depth 1 ${INDEXTTS_REPO_URL} ${INDEXTTS_REPO_PATH} || \
    (git clone --depth 1 ${INDEXTTS_REPO_URL} ${INDEXTTS_REPO_PATH} && \
     cd ${INDEXTTS_REPO_PATH} && \
     git config lfs.fetchexclude '*' && \
     git reset --hard HEAD); \
    cd ${INDEXTTS_REPO_PATH}; \
    # Try to pull LFS files, but continue if it fails (LFS budget exceeded)
    git lfs pull || echo "Warning: Git LFS pull failed, continuing without LFS files"; \
    # Remove .git directory to save space
    rm -rf .git; \
    # Remove unnecessary files
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true; \
    find . -type d -name "tests" -exec rm -rf {} + 2>/dev/null || true; \
    find . -type d -name "docs" -exec rm -rf {} + 2>/dev/null || true; \
    find . -type f -name "*.pyc" -delete 2>/dev/null || true; \
    set -e

# Install IndexTTS using uv pip (installs to system Python)
# Use --break-system-packages to override PEP 668 externally-managed check in Ubuntu 22.04
WORKDIR ${INDEXTTS_REPO_PATH}
RUN uv pip install --system --break-system-packages -e . && \
    # Clean up pip cache and temporary files
    uv pip cache purge 2>/dev/null || true && \
    rm -rf /tmp/* /var/tmp/*

# ============================================================================
# Stage 3: Install wrapper dependencies
# ============================================================================
FROM builder-base AS wrapper-install

# Ensure PATH includes uv location
ENV PATH="/root/.local/bin:/root/.cargo/bin:/usr/local/bin:$PATH"

# Copy wrapper code
COPY --chown=root:root pyproject.toml /app/wrapper/
COPY --chown=root:root README.md /app/wrapper/
COPY --chown=root:root indextts_fastapi/ /app/wrapper/indextts_fastapi/

# Install wrapper dependencies
# Use --break-system-packages to override PEP 668 externally-managed check in Ubuntu 22.04
WORKDIR /app/wrapper
RUN uv pip install --system --break-system-packages -e . && \
    # Verify uvicorn was installed
    python3 -c "import uvicorn; print('uvicorn installed at:', uvicorn.__file__)" && \
    # Show where packages are installed
    python3 -c "import site; print('Site packages:', site.getsitepackages())" && \
    # Clean up pip cache and temporary files
    uv pip cache purge 2>/dev/null || true && \
    rm -rf /tmp/* /var/tmp/*

# ============================================================================
# Stage 4: Runtime base - using runtime image (pre-built wheel doesn't need devel)
# ============================================================================
FROM nvidia/cuda:12.8.0-runtime-ubuntu22.04 AS runtime-base

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Install only runtime dependencies (no build tools needed for pre-built wheel)
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3.10 \
    python3.10-minimal \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean \
    && rm -rf /tmp/* /var/tmp/* && \
    # Verify python3 is available
    python3 --version

# Set working directory
WORKDIR /app

# ============================================================================
# Stage 5: Final runtime image
# ============================================================================
FROM runtime-base AS runtime

# Copy IndexTTS installation (without .git and unnecessary files)
COPY --from=indextts-install --chown=root:root /app/index-tts /app/index-tts

# Copy uv from builder stage to runtime (following setup.sh/start.sh approach)
COPY --from=builder-base --chown=root:root /root/.local/bin/uv /usr/local/bin/uv
COPY --from=builder-base --chown=root:root /root/.local/bin/uvx /usr/local/bin/uvx

# Copy Python packages from builder stages
# uv pip install --system installs to /usr/local/lib/python3.10/dist-packages/ (Ubuntu/Debian)
# Create target directories first and make uv executable
RUN mkdir -p /usr/local/lib/python3.10/dist-packages /usr/local/lib/python3.10/site-packages && \
    chmod +x /usr/local/bin/uv && \
    (chmod +x /usr/local/bin/uvx 2>/dev/null || true) && \
    uv --version

# Copy packages from system Python location (where --system installs)
# Note: We also install in runtime, but copying ensures IndexTTS dependencies are available
COPY --from=indextts-install --chown=root:root /usr/local/lib/python3.10/dist-packages/ /usr/local/lib/python3.10/dist-packages/
COPY --from=wrapper-install --chown=root:root /usr/local/lib/python3.10/dist-packages/ /usr/local/lib/python3.10/dist-packages/

# Set PATH to include uv location
ENV PATH="/root/.local/bin:/usr/local/bin:$PATH"

# Set Python path to include IndexTTS and ensure dist-packages is in Python's search path
ENV PYTHONPATH="/app/index-tts:/usr/local/lib/python3.10/dist-packages:/usr/local/lib/python3.10/site-packages:$PYTHONPATH"

WORKDIR /app/wrapper

# Create virtual environment and install stable dependencies FIRST (for better caching)
# This layer will be cached unless Python or dependency files change
RUN uv venv /app/.venv && \
    # Install IndexTTS into the venv (this is stable, rarely changes)
    cd /app/index-tts && \
    uv pip install --python /app/.venv/bin/python -e . && \
    # Install flash-attention from pre-built wheel (much faster than compiling)
    # Using v2.8.3 wheel for CUDA 12.x and Python 3.10, PyTorch 2.8
    # Note: cu12 wheels work with CUDA 12.x (including 12.8)
    echo ">> Installing flash-attention from pre-built wheel..." && \
    uv pip install --python /app/.venv/bin/python \
        https://github.com/Dao-AILab/flash-attention/releases/download/v2.8.3/flash_attn-2.8.3+cu12torch2.8cxx11abiFALSE-cp310-cp310-linux_x86_64.whl && \
    /app/.venv/bin/python -c "import flash_attn; print('✓ flash-attention v2.8.3 installed successfully')"

# Copy wrapper code AFTER installing stable dependencies
# This way code changes don't invalidate the expensive flash-attention compilation
COPY --chown=root:root pyproject.toml /app/wrapper/
COPY --chown=root:root README.md /app/wrapper/
COPY --chown=root:root indextts_fastapi/ /app/wrapper/indextts_fastapi/
# Copy voice_mappings.json (optional - will be skipped if not in build context due to .dockerignore)
COPY --chown=root:root voice_mappings.json /app/wrapper/voice_mappings.json

# Install wrapper dependencies (this changes when code changes, but is fast)
RUN cd /app/wrapper && \
    uv pip install --python /app/.venv/bin/python -e . && \
    # Verify installations
    /app/.venv/bin/python -c "import uvicorn; print('✓ uvicorn installed:', uvicorn.__version__)" && \
    /app/.venv/bin/python -c "import fastapi; print('✓ fastapi installed')" && \
    /app/.venv/bin/python -c "import flash_attn; print('✓ flash-attention available')" && \
    /app/.venv/bin/python -m uvicorn --version && \
    # Clean up
    uv pip cache purge 2>/dev/null || true && \
    rm -rf /tmp/* /var/tmp/*

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
# Use venv Python (same as start.sh: "$VENV_PYTHON" -m indextts_fastapi.api)
CMD ["/app/.venv/bin/python", "-m", "indextts_fastapi.api"]
