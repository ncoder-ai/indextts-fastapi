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

# Apply patch to BigVGAN load.py to fix CUDA 12.8+ compatibility (remove compute_70)
echo ">> Applying BigVGAN CUDA 12.8+ compatibility patch..."
BIGVGAN_LOAD_FILE="$INDEXTTS_REPO_PATH/indextts/s2mel/modules/bigvgan/alias_free_activation/cuda/load.py"
if [ -f "$BIGVGAN_LOAD_FILE" ]; then
    # Check if patch is already applied (check if compute_70 is removed)
    if grep -q "arch=compute_70,code=sm_70" "$BIGVGAN_LOAD_FILE" 2>/dev/null; then
        echo ">> Patching BigVGAN load.py to remove compute_70 (CUDA 12.8+ compatibility)..."
        
        # Use Python to apply the patch reliably
        python3 - "$BIGVGAN_LOAD_FILE" << 'PYTHON_PATCH'
import sys

file_path = sys.argv[1]

with open(file_path, 'r') as f:
    lines = f.readlines()

new_lines = []
i = 0
while i < len(lines):
    line = lines[i]
    
    # Patch 1: Comment out TORCH_CUDA_ARCH_LIST clearing
    if 'os.environ["TORCH_CUDA_ARCH_LIST"] = ""' in line:
        indent = len(line) - len(line.lstrip())
        new_lines.append(' ' * indent + '# Let TORCH_CUDA_ARCH_LIST be set by the user or auto-detected (patched for CUDA 12.8+ compatibility)\n')
        new_lines.append(' ' * indent + '# os.environ["TORCH_CUDA_ARCH_LIST"] = ""\n')
        i += 1
        continue
    
    # Patch 2: Remove compute_70 line and add comment
    if 'arch=compute_70,code=sm_70' in line:
        indent = len(line) - len(line.lstrip())
        new_lines.append(' ' * indent + '# Removed compute_70 (Volta) - not supported in CUDA 12.8+\n')
        new_lines.append(' ' * indent + '# Architecture flags will come from TORCH_CUDA_ARCH_LIST or auto-detection\n')
        i += 1
        continue
    
    new_lines.append(line)
    i += 1

with open(file_path, 'w') as f:
    f.writelines(new_lines)

print(">> BigVGAN patch applied successfully")
PYTHON_PATCH
    else
        echo ">> BigVGAN patch already applied (compute_70 already removed)"
    fi
else
    echo ">> WARNING: BigVGAN load.py not found at $BIGVGAN_LOAD_FILE"
    echo ">> Patch will be applied when the file is available"
fi

# Check if uv is installed (required)
if ! command -v uv &> /dev/null; then
    echo "ERROR: uv is not installed. Please install uv first:"
    echo "  curl -LsSf https://astral.sh/uv/install.sh | sh"
    echo "  Or see: https://docs.astral.sh/uv/"
    exit 1
fi

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

# Try to install DeepSpeed for multi-GPU support (optional, will fall back if unavailable)
echo ">> Attempting to install DeepSpeed for multi-GPU support..."
uv pip install --python "$VENV_PYTHON" deepspeed==0.17.1 || {
    echo ">> WARNING: DeepSpeed installation failed or not available."
    echo ">> Multi-GPU support will be disabled. Single GPU will still work."
}

# Try to install flash-attention for acceleration (optional, will fall back if unavailable)
echo ">> Attempting to install flash-attention for acceleration..."
uv pip install --python "$VENV_PYTHON" flash-attn --no-build-isolation || {
    echo ">> WARNING: flash-attention installation failed or not available."
    echo ">> Acceleration will be disabled. Install manually if needed:"
    echo ">>   uv pip install flash-attn --no-build-isolation"
    echo ">>   Or see: https://github.com/Dao-AILab/flash-attention/releases/"
}

# Install wrapper dependencies
echo ">> Installing wrapper dependencies..."
cd "$PROJECT_ROOT"
uv pip install --python "$VENV_PYTHON" -e .

echo ">> Setup complete!"
echo ">> Note: Model checkpoints will be auto-downloaded on first API startup"
echo ">>   or you can download them manually using:"
echo ">>   hf download IndexTeam/IndexTTS-2 --local-dir=checkpoints"

