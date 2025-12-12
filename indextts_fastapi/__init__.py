"""
IndexTTS FastAPI - REST API wrapper for IndexTTS2
"""
import os

# Set TORCH_CUDA_ARCH_LIST early to prevent compilation warnings
# This must be set BEFORE any torch imports or CUDA-dependent modules are loaded
# Setting it here ensures it's available when DeepSpeed/PyTorch compile CUDA kernels
if not os.getenv("TORCH_CUDA_ARCH_LIST"):
    # Set to supported architectures: 7.5 (Turing), 8.0+ (Ampere and newer)
    # Exclude 7.0 (Volta) which CUDA 12.8+ doesn't support
    os.environ["TORCH_CUDA_ARCH_LIST"] = "7.5;8.0;8.6"

__version__ = "1.0.0"

from .api import app, get_app

__all__ = ["app", "get_app"]

