"""
Configuration for IndexTTS FastAPI
"""
import os
from typing import Dict, List, Optional


def get_model_config() -> Dict:
    """Get model configuration from environment variables or defaults"""
    return {
        "cfg_path": os.getenv("INDEXTTS_CFG_PATH", "checkpoints/config.yaml"),
        "model_dir": os.getenv("INDEXTTS_MODEL_DIR", "checkpoints"),
        "use_fp16": os.getenv("INDEXTTS_USE_FP16", "true").lower() == "true",  # Default: enabled for lower VRAM
        "use_cuda_kernel": os.getenv("INDEXTTS_USE_CUDA_KERNEL", "false").lower() == "true",
        "use_deepspeed": os.getenv("INDEXTTS_USE_DEEPSPEED", "true").lower() == "true",  # Default: enabled for multi-GPU
        "use_accel": os.getenv("INDEXTTS_USE_ACCEL", "false").lower() == "true",
        "use_torch_compile": os.getenv("INDEXTTS_USE_TORCH_COMPILE", "false").lower() == "true",
    }


def get_auto_download_config() -> Dict:
    """Get auto-download configuration from environment variables or defaults"""
    return {
        "auto_download": os.getenv("INDEXTTS_AUTO_DOWNLOAD", "true").lower() == "true",
        "hf_repo": os.getenv("INDEXTTS_HF_REPO", "IndexTeam/IndexTTS-2"),
    }


def get_voice_directories() -> List[str]:
    """Get voice directories from environment or defaults"""
    voice_dirs_env = os.getenv("INDEXTTS_VOICE_DIRECTORIES", "")
    if voice_dirs_env:
        return [d.strip() for d in voice_dirs_env.split(",") if d.strip()]
    return ["examples", "prompts"]


# OpenAI-compatible voice mapping
OPENAI_VOICE_MAP = {
    "alloy": "examples/voice_01.wav",
    "echo": "examples/voice_02.wav",
    "fable": "examples/voice_03.wav",
    "onyx": "examples/voice_04.wav",
    "nova": "examples/voice_05.wav",
    "shimmer": "examples/voice_06.wav",
    # Additional voices using remaining examples
    "voice_07": "examples/voice_07.wav",
    "voice_08": "examples/voice_08.wav",
    "voice_09": "examples/voice_09.wav",
    "voice_10": "examples/voice_10.wav",
    "voice_11": "examples/voice_11.wav",
    "voice_12": "examples/voice_12.wav",
}

DEFAULT_VOICE = "alloy"
AUDIO_EXTENSIONS = {".wav", ".mp3", ".flac", ".m4a", ".ogg", ".opus"}

