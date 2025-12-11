"""
Configuration for IndexTTS FastAPI
"""
import os
import json
from pathlib import Path
from typing import Dict, List, Optional


def get_model_config() -> Dict:
    """Get model configuration from environment variables or defaults"""
    return {
        "cfg_path": os.getenv("INDEXTTS_CFG_PATH", "checkpoints/config.yaml"),
        "model_dir": os.getenv("INDEXTTS_MODEL_DIR", "checkpoints"),
        "use_fp16": os.getenv("INDEXTTS_USE_FP16", "true").lower() == "true",  # Default: enabled for lower VRAM
        "use_cuda_kernel": os.getenv("INDEXTTS_USE_CUDA_KERNEL", "false").lower() == "true",
        "use_deepspeed": os.getenv("INDEXTTS_USE_DEEPSPEED", "true").lower() == "true",  # Note: DeepSpeed in IndexTTS is for optimization only, not model parallelism
        "use_accel": os.getenv("INDEXTTS_USE_ACCEL", "false").lower() == "true",
        "use_torch_compile": os.getenv("INDEXTTS_USE_TORCH_COMPILE", "false").lower() == "true",
    }


def get_auto_download_config() -> Dict:
    """Get auto-download configuration from environment variables or defaults"""
    return {
        "auto_download": os.getenv("INDEXTTS_AUTO_DOWNLOAD", "true").lower() == "true",
        "hf_repo": os.getenv("INDEXTTS_HF_REPO", "IndexTeam/IndexTTS-2"),
    }




# Track which voices are presets (from JSON file) vs dynamically discovered
_PRESET_VOICE_IDS = set()

def load_voice_mappings() -> Dict[str, str]:
    """
    Load optional voice mappings from voice_mappings.json for aliases.
    
    This is kept for backward compatibility to support aliases (e.g., "alloy" -> "voice_01").
    Voice discovery is now handled directly in api.py via discover_voice_files().
    
    Returns:
        Dict mapping alias IDs to file paths (relative paths)
    """
    global _PRESET_VOICE_IDS
    _PRESET_VOICE_IDS.clear()
    
    # Load optional JSON file for alias mappings
    project_root = Path(__file__).parent.parent
    voice_mappings_file = project_root / "voice_mappings.json"
    
    # Also try current working directory
    if not voice_mappings_file.exists():
        voice_mappings_file = Path("voice_mappings.json")
    
    json_mappings = {}
    if voice_mappings_file.exists():
        try:
            with open(voice_mappings_file, 'r', encoding='utf-8') as f:
                json_mappings = json.load(f)
                if isinstance(json_mappings, dict):
                    _PRESET_VOICE_IDS = set(json_mappings.keys())
                    print(f">> Loaded {len(json_mappings)} alias mappings from {voice_mappings_file} (optional)")
                else:
                    print(f">> WARNING: voice_mappings.json is not a valid JSON object. Ignoring.")
                    json_mappings = {}
        except json.JSONDecodeError as e:
            print(f">> WARNING: Failed to parse voice_mappings.json: {e}. Ignoring.")
        except Exception as e:
            print(f">> WARNING: Error loading voice_mappings.json: {e}. Ignoring.")
    
    return json_mappings


def is_preset_voice(voice_id: str) -> bool:
    """
    Check if a voice ID is a preset (from JSON file).
    
    Args:
        voice_id: Voice identifier
        
    Returns:
        True if voice is a preset, False if dynamically discovered
    """
    return voice_id in _PRESET_VOICE_IDS


# OpenAI-compatible voice mapping (dynamically generated + optional JSON overrides)
OPENAI_VOICE_MAP = load_voice_mappings()

DEFAULT_VOICE = "alloy"
AUDIO_EXTENSIONS = {".wav", ".mp3", ".flac", ".m4a", ".ogg", ".opus"}

