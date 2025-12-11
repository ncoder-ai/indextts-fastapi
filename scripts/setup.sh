#!/bin/bash
# Setup script for IndexTTS FastAPI wrapper
# Clones IndexTTS repo and installs dependencies

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
INDEXTTS_REPO_PATH="${INDEXTTS_REPO_PATH:-$PROJECT_ROOT/index-tts}"
INDEXTTS_REPO_URL="https://github.com/index-tts/index-tts.git"

echo ">> IndexTTS FastAPI Setup Script"
echo ">> Project root: $PROJECT_ROOT"
echo ">> IndexTTS repo path: $INDEXTTS_REPO_PATH"

# Check if git is installed
if ! command -v git &> /dev/null; then
    echo "ERROR: git is not installed. Please install git first."
    exit 1
fi

# Clone or update IndexTTS repo
if [ -d "$INDEXTTS_REPO_PATH" ]; then
    echo ">> IndexTTS repo exists, pulling latest changes..."
    cd "$INDEXTTS_REPO_PATH"
    git pull || true
    echo ">> Attempting to download LFS files (may fail due to quota limits)..."
    git lfs pull || echo ">> WARNING: LFS pull failed (examples files may be missing, but API will still work)"
else
    echo ">> Cloning IndexTTS repo..."
    # Clone without LFS checkout first to avoid immediate failure
    GIT_LFS_SKIP_SMUDGE=1 git clone "$INDEXTTS_REPO_URL" "$INDEXTTS_REPO_PATH" || {
        echo ">> Clone failed, trying without LFS skip..."
        git clone "$INDEXTTS_REPO_URL" "$INDEXTTS_REPO_PATH"
    }
    cd "$INDEXTTS_REPO_PATH"
    echo ">> Attempting to download LFS files (may fail due to quota limits)..."
    git lfs pull || echo ">> WARNING: LFS pull failed (examples files may be missing, but API will still work)"
fi

# Check if uv is installed
if command -v uv &> /dev/null; then
    # Create virtual environment in project root if it doesn't exist
    cd "$PROJECT_ROOT"
    if [ ! -d ".venv" ]; then
        echo ">> Creating virtual environment..."
        uv venv
    fi
    
    # Get the Python interpreter from the venv
    VENV_PYTHON="$PROJECT_ROOT/.venv/bin/python"
    
    # Install IndexTTS into the project venv
    echo ">> Installing IndexTTS using uv..."
    cd "$INDEXTTS_REPO_PATH"
    uv pip install --python "$VENV_PYTHON" -e .
    echo ">> IndexTTS installed successfully with uv"
    
    # Install wrapper dependencies
    echo ">> Installing wrapper dependencies..."
    cd "$PROJECT_ROOT"
    uv pip install --python "$VENV_PYTHON" -e .
elif command -v pip &> /dev/null; then
    echo ">> Installing IndexTTS using pip..."
    cd "$INDEXTTS_REPO_PATH"
    pip install -e .
    echo ">> IndexTTS installed successfully with pip"
    
    # Install wrapper dependencies
    echo ">> Installing wrapper dependencies..."
    cd "$PROJECT_ROOT"
    pip install -e .
else
    echo "ERROR: Neither uv nor pip is installed. Please install one of them."
    exit 1
fi

echo ">> Setup complete!"
echo ">> Note: Model checkpoints will be auto-downloaded on first API startup"
echo ">>   or you can download them manually using:"
echo ">>   hf download IndexTeam/IndexTTS-2 --local-dir=checkpoints"

