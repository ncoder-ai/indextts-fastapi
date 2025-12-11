#!/bin/bash
# Start script for IndexTTS FastAPI wrapper

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"
INDEXTTS_REPO_PATH="${INDEXTTS_REPO_PATH:-$PROJECT_ROOT/index-tts}"

echo ">> Starting IndexTTS FastAPI..."
echo ">> Project root: $PROJECT_ROOT"

# Check if IndexTTS is installed
if [ ! -d "$INDEXTTS_REPO_PATH" ]; then
    echo ">> ERROR: IndexTTS repo not found at $INDEXTTS_REPO_PATH"
    echo ">> Please run ./scripts/setup.sh first to clone and install IndexTTS"
    exit 1
fi

# Check if uv is available (preferred)
if ! command -v uv &> /dev/null; then
    echo ">> WARNING: uv is not installed. Install it from https://docs.astral.sh/uv/"
    echo ">> Falling back to pip..."
    USE_UV=false
else
    USE_UV=true
fi

# Install IndexTTS if not already installed
if ! python3 -c "import sys; sys.path.insert(0, '$INDEXTTS_REPO_PATH'); import indextts" 2>/dev/null; then
    echo ">> IndexTTS not installed. Installing with dependencies..."
    cd "$INDEXTTS_REPO_PATH"
    if [ "$USE_UV" = true ]; then
        uv sync --no-dev
    elif command -v pip &> /dev/null; then
        pip install -e .
    else
        echo ">> ERROR: Neither uv nor pip is available"
        exit 1
    fi
    cd "$PROJECT_ROOT"
fi

# Verify torch is available (required by IndexTTS)
if ! python3 -c "import torch" 2>/dev/null; then
    echo ">> WARNING: torch not found. Installing IndexTTS dependencies..."
    cd "$INDEXTTS_REPO_PATH"
    if [ "$USE_UV" = true ]; then
        uv sync --no-dev
    elif command -v pip &> /dev/null; then
        pip install -e .
    fi
    cd "$PROJECT_ROOT"
    
    # Check again
    if ! python3 -c "import torch" 2>/dev/null; then
        echo ">> ERROR: torch still not available. Please ensure IndexTTS is properly installed."
        echo ">> Try running: cd $INDEXTTS_REPO_PATH && uv sync --no-dev"
        exit 1
    fi
fi

# Set PYTHONPATH to include IndexTTS
export PYTHONPATH="$INDEXTTS_REPO_PATH:$PYTHONPATH"

# Check if wrapper dependencies are installed
if ! python3 -c "import fastapi, uvicorn" 2>/dev/null; then
    echo ">> Installing wrapper dependencies..."
    if [ "$USE_UV" = true ]; then
        uv pip install -e .
    elif command -v pip &> /dev/null; then
        pip install -e .
    else
        echo ">> ERROR: Cannot install dependencies. Please install uv or pip."
        exit 1
    fi
fi

# Run the API
echo ">> Starting API server on http://0.0.0.0:8000"
echo ">> API docs will be available at http://localhost:8000/docs"
echo ">> Press Ctrl+C to stop"
echo ""

cd "$PROJECT_ROOT"

# Use uv run if available to ensure correct environment, otherwise use python3
if [ "$USE_UV" = true ] && [ -d "$INDEXTTS_REPO_PATH/.venv" ]; then
    # Use uv run from IndexTTS directory to get its environment
    echo ">> Using uv run with IndexTTS environment..."
    cd "$INDEXTTS_REPO_PATH"
    uv run python -m indextts_fastapi.api
else
    # Fallback to direct python3
    python3 -m indextts_fastapi.api
fi

