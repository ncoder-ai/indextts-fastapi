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


def get_voice_directories() -> List[str]:
    """Get voice directories from environment or defaults"""
    voice_dirs_env = os.getenv("INDEXTTS_VOICE_DIRECTORIES", "")
    if voice_dirs_env:
        return [d.strip() for d in voice_dirs_env.split(",") if d.strip()]
    return ["examples"]


def discover_voices_from_directories() -> Dict[str, str]:
    """
    Dynamically discover voices from configured directories.
    
    Scans voice directories and creates mappings from filenames.
    
    Returns:
        Dict mapping voice IDs to file paths
    """
    mappings = {}
    project_root = Path(__file__).parent.parent
    voice_dirs = get_voice_directories()
    audio_extensions = {".wav", ".mp3", ".flac", ".m4a", ".ogg", ".opus"}
    
    for directory in voice_dirs:
        # Resolve directory path - try project root first
        if not os.path.isabs(directory):
            full_dir = os.path.join(project_root, directory)
            if not os.path.exists(full_dir):
                # Fallback to index-tts directory
                full_dir = os.path.join(project_root, "index-tts", directory)
                if not os.path.exists(full_dir):
                    continue
            directory = full_dir
        elif not os.path.exists(directory):
            continue
        
        # Scan directory for audio files
        try:
            for filename in os.listdir(directory):
                file_path = os.path.join(directory, filename)
                
                # Skip if not a file or not an audio file
                if not os.path.isfile(file_path):
                    continue
                
                # Check if it's an audio file
                _, ext = os.path.splitext(filename.lower())
                if ext not in audio_extensions:
                    continue
                
                # Skip emotion reference files
                if "emo_" in filename.lower():
                    continue
                
                # Create voice name from filename (without extension)
                voice_name = os.path.splitext(filename)[0]
                
                # Use relative path from project root for consistency
                try:
                    rel_path = os.path.relpath(file_path, project_root)
                except ValueError:
                    # If relative path fails (different drives on Windows), use absolute
                    rel_path = file_path
                
                # Only add if not already in mappings (first found wins)
                if voice_name not in mappings:
                    mappings[voice_name] = rel_path
        except PermissionError:
            print(f">> WARNING: Permission denied accessing {directory}")
        except Exception as e:
            print(f">> WARNING: Error scanning {directory}: {e}")
    
    return mappings


# Track which voices are presets (from JSON file) vs dynamically discovered
_PRESET_VOICE_IDS = set()

def load_voice_mappings() -> Dict[str, str]:
    """
    Load OpenAI-compatible voice mappings.
    
    Strategy:
    1. Load optional voice_mappings.json for preset mappings
    2. Dynamically discover voices from configured directories (examples, prompts, etc.)
    3. Merge them (discovered voices added, JSON presets take priority)
    
    Returns:
        Dict mapping voice IDs to file paths
    """
    global _PRESET_VOICE_IDS
    _PRESET_VOICE_IDS.clear()
    
    # Step 1: Load optional JSON file for preset mappings
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
                    print(f">> Loaded {len(json_mappings)} preset mappings from {voice_mappings_file}")
                else:
                    print(f">> WARNING: voice_mappings.json is not a valid JSON object. Ignoring.")
                    json_mappings = {}
        except json.JSONDecodeError as e:
            print(f">> WARNING: Failed to parse voice_mappings.json: {e}. Ignoring.")
        except Exception as e:
            print(f">> WARNING: Error loading voice_mappings.json: {e}. Ignoring.")
    
    # Step 2: Dynamically discover voices from directories
    discovered_mappings = discover_voices_from_directories()
    print(f">> Discovered {len(discovered_mappings)} voices from configured directories")
    
    # Step 3: Merge - JSON presets first, then discovered voices (discovered don't override presets)
    final_mappings = json_mappings.copy()
    for voice_id, file_path in discovered_mappings.items():
        if voice_id not in final_mappings:  # Don't override presets
            final_mappings[voice_id] = file_path
    
    if json_mappings:
        print(f">> Total voice mappings: {len(final_mappings)} ({len(json_mappings)} presets + {len(discovered_mappings)} discovered)")
    else:
        print(f">> Total voice mappings: {len(final_mappings)} (all dynamically discovered)")
    
    return final_mappings


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

