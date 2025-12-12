"""
IndexTTS FastAPI - REST API wrapper for IndexTTS2
"""
import os
import sys

# Set TORCH_CUDA_ARCH_LIST at package import time to prevent CUDA 12.8+ compilation errors
# CUDA 12.8+ doesn't support compute_70 (Volta), so we exclude it
# This must be set BEFORE any torch imports or CUDA-dependent modules are loaded
# Setting it here ensures it's available when IndexTTS2 compiles its CUDA kernels
if not os.getenv("TORCH_CUDA_ARCH_LIST"):
    # Set to supported architectures: 7.5 (Turing), 8.0+ (Ampere and newer)
    # Exclude 7.0 (Volta) which CUDA 12.8+ doesn't support
    os.environ["TORCH_CUDA_ARCH_LIST"] = "7.5;8.0;8.6"

# Note: BigVGAN CUDA loader patching is done in api.py before IndexTTS2 initialization
# This ensures the patch is applied at the right time

__version__ = "1.0.0"

from .api import app, get_app

__all__ = ["app", "get_app"]

