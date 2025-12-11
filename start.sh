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

# Set PYTHONPATH to include both IndexTTS and wrapper
export PYTHONPATH="$PROJECT_ROOT:$INDEXTTS_REPO_PATH:$PYTHONPATH"

# Check for virtual environment (prefer project root venv, fallback to IndexTTS venv)
VENV_PYTHON=""
if [ "$USE_UV" = true ]; then
    # Prefer project root venv (created by setup.sh)
    if [ -d "$PROJECT_ROOT/.venv" ]; then
        VENV_PYTHON="$PROJECT_ROOT/.venv/bin/python"
        echo ">> Using project root virtual environment"
    elif [ -d "$INDEXTTS_REPO_PATH/.venv" ]; then
        VENV_PYTHON="$INDEXTTS_REPO_PATH/.venv/bin/python"
        echo ">> Using IndexTTS virtual environment"
    fi
fi

# Verify and install dependencies if needed
if [ "$USE_UV" = true ]; then
    if [ -n "$VENV_PYTHON" ]; then
        # Check if IndexTTS is installed in the venv
        if ! "$VENV_PYTHON" -c "import indextts" 2>/dev/null; then
            echo ">> Installing IndexTTS into virtual environment..."
            cd "$INDEXTTS_REPO_PATH"
            uv pip install --python "$VENV_PYTHON" -e .
            cd "$PROJECT_ROOT"
        fi
        
        # Check if wrapper dependencies are installed
        if ! "$VENV_PYTHON" -c "import fastapi, uvicorn" 2>/dev/null; then
            echo ">> Installing wrapper dependencies..."
            cd "$PROJECT_ROOT"
            uv pip install --python "$VENV_PYTHON" -e .
        fi
    else
        # No venv found, create one in project root
        echo ">> Creating virtual environment..."
        cd "$PROJECT_ROOT"
        uv venv
        VENV_PYTHON="$PROJECT_ROOT/.venv/bin/python"
        
        echo ">> Installing IndexTTS..."
        cd "$INDEXTTS_REPO_PATH"
        uv pip install --python "$VENV_PYTHON" -e .
        
        echo ">> Installing wrapper dependencies..."
        cd "$PROJECT_ROOT"
        uv pip install --python "$VENV_PYTHON" -e .
    fi
elif command -v pip &> /dev/null; then
    # Fallback to pip
    if ! python3 -c "import indextts" 2>/dev/null; then
        echo ">> Installing IndexTTS..."
        cd "$INDEXTTS_REPO_PATH"
        pip install -e .
        cd "$PROJECT_ROOT"
    fi
    
    if ! python3 -c "import fastapi, uvicorn" 2>/dev/null; then
        echo ">> Installing wrapper dependencies..."
        cd "$PROJECT_ROOT"
        pip install -e .
    fi
    VENV_PYTHON="python3"
else
    echo ">> ERROR: Neither uv nor pip is available"
    exit 1
fi

# Run the API
echo ">> Starting API server on http://0.0.0.0:8000"
echo ">> API docs will be available at http://localhost:8000/docs"
echo ">> Press Ctrl+C to stop"
echo ""

# Use the virtual environment Python if available
cd "$PROJECT_ROOT"
if [ -n "$VENV_PYTHON" ]; then
    "$VENV_PYTHON" -m indextts_fastapi.api
else
    python3 -m indextts_fastapi.api
fi

