"""
Configuration for IndexTTS FastAPI
"""
import os
import json
from pathlib import Path
from typing import Dict, List, Optional

try:
    import yaml
except ImportError:
    yaml = None
    print(">> WARNING: pyyaml not installed. Install it with: pip install pyyaml")


# Global config cache
_config_cache: Optional[Dict] = None


def get_project_root() -> Path:
    """Get the project root directory"""
    return Path(__file__).parent.parent


def get_default_config() -> Dict:
    """Get default configuration values"""
    return {
        "model": {
            "cfg_path": "checkpoints/config.yaml",
            "model_dir": "checkpoints",
            "use_fp16": True,
            "use_cuda_kernel": True,  # Optimized for GPU performance
            "use_deepspeed": True,
            "use_accel": True,  # Optimized for GPU performance
            "use_torch_compile": True,  # Optimized for GPU performance
        },
        "auto_download": {
            "enabled": True,
            "hf_repo": "IndexTeam/IndexTTS-2",
        },
        "voice": {
            "voice_dir": "examples",
            "default_voice": "alloy",
        },
        "server": {
            "host": "0.0.0.0",
            "port": 9877,
        },
    }


def create_default_config_file(config_path: Path) -> None:
    """Create a default config.yaml file if it doesn't exist"""
    if yaml is None:
        print(">> WARNING: Cannot create config.yaml - pyyaml not installed")
        return
    
    default_config = get_default_config()
    
    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(default_config, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
        print(f">> Created default config.yaml at {config_path}")
    except Exception as e:
        print(f">> WARNING: Failed to create default config.yaml: {e}")


def load_config() -> Dict:
    """
    Load configuration from config.yaml file.
    Creates a default config.yaml if it doesn't exist.
    Environment variables will override YAML values in individual get_*_config() functions.
    
    Returns:
        Dict containing configuration from YAML file or defaults
    """
    global _config_cache
    
    if _config_cache is not None:
        return _config_cache
    
    project_root = get_project_root()
    config_path = project_root / "config.yaml"
    
    # Also try current working directory
    if not config_path.exists():
        config_path = Path("config.yaml")
    
    # If config.yaml doesn't exist, create default one
    if not config_path.exists():
        if yaml is not None:
            create_default_config_file(config_path)
        _config_cache = get_default_config()
        return _config_cache
    
    # Load from YAML file
    if yaml is None:
        print(">> WARNING: pyyaml not installed, using default configuration")
        _config_cache = get_default_config()
        return _config_cache
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        if config is None:
            print(f">> WARNING: config.yaml is empty, using defaults")
            _config_cache = get_default_config()
            return _config_cache
        
        # Merge with defaults to ensure all keys exist
        default_config = get_default_config()
        merged_config = _deep_merge(default_config.copy(), config)
        _config_cache = merged_config
        print(f">> Loaded configuration from {config_path}")
        return _config_cache
    
    except yaml.YAMLError as e:
        print(f">> WARNING: Failed to parse config.yaml: {e}. Using defaults.")
        _config_cache = get_default_config()
        return _config_cache
    except Exception as e:
        print(f">> WARNING: Error loading config.yaml: {e}. Using defaults.")
        _config_cache = get_default_config()
        return _config_cache


def _deep_merge(base: Dict, override: Dict) -> Dict:
    """Deep merge two dictionaries, with override taking precedence"""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def get_model_config() -> Dict:
    """
    Get model configuration from config.yaml, with environment variable overrides.
    
    Environment variables override YAML values:
    - INDEXTTS_CFG_PATH
    - INDEXTTS_MODEL_DIR
    - INDEXTTS_USE_FP16
    - INDEXTTS_USE_CUDA_KERNEL
    - INDEXTTS_USE_DEEPSPEED
    - INDEXTTS_USE_ACCEL
    - INDEXTTS_USE_TORCH_COMPILE
    """
    config = load_config()
    model_config = config.get("model", {})
    
    # Environment variables override YAML values
    return {
        "cfg_path": os.getenv("INDEXTTS_CFG_PATH", model_config.get("cfg_path", "checkpoints/config.yaml")),
        "model_dir": os.getenv("INDEXTTS_MODEL_DIR", model_config.get("model_dir", "checkpoints")),
        "use_fp16": os.getenv("INDEXTTS_USE_FP16", str(model_config.get("use_fp16", True))).lower() == "true",
        "use_cuda_kernel": os.getenv("INDEXTTS_USE_CUDA_KERNEL", str(model_config.get("use_cuda_kernel", True))).lower() == "true",
        "use_deepspeed": os.getenv("INDEXTTS_USE_DEEPSPEED", str(model_config.get("use_deepspeed", True))).lower() == "true",
        "use_accel": os.getenv("INDEXTTS_USE_ACCEL", str(model_config.get("use_accel", True))).lower() == "true",
        "use_torch_compile": os.getenv("INDEXTTS_USE_TORCH_COMPILE", str(model_config.get("use_torch_compile", True))).lower() == "true",
    }


def get_auto_download_config() -> Dict:
    """
    Get auto-download configuration from config.yaml, with environment variable overrides.
    
    Environment variables override YAML values:
    - INDEXTTS_AUTO_DOWNLOAD
    - INDEXTTS_HF_REPO
    """
    config = load_config()
    auto_download_config = config.get("auto_download", {})
    
    # Environment variables override YAML values
    return {
        "auto_download": os.getenv("INDEXTTS_AUTO_DOWNLOAD", str(auto_download_config.get("enabled", True))).lower() == "true",
        "hf_repo": os.getenv("INDEXTTS_HF_REPO", auto_download_config.get("hf_repo", "IndexTeam/IndexTTS-2")),
    }


def get_voice_config() -> Dict:
    """
    Get voice configuration from config.yaml, with environment variable overrides.
    
    Environment variables override YAML values:
    - INDEXTTS_VOICE_DIR
    """
    config = load_config()
    voice_config = config.get("voice", {})
    
    # Environment variables override YAML values
    return {
        "voice_dir": os.getenv("INDEXTTS_VOICE_DIR", voice_config.get("voice_dir", "examples")),
        "default_voice": voice_config.get("default_voice", "alloy"),
    }


def get_server_config() -> Dict:
    """
    Get server configuration from config.yaml, with environment variable overrides.
    
    Environment variables override YAML values:
    - INDEXTTS_HOST
    - INDEXTTS_PORT
    """
    config = load_config()
    server_config = config.get("server", {})
    
    # Environment variables override YAML values
    return {
        "host": os.getenv("INDEXTTS_HOST", server_config.get("host", "0.0.0.0")),
        "port": int(os.getenv("INDEXTTS_PORT", str(server_config.get("port", 9877)))),
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

AUDIO_EXTENSIONS = {".wav", ".mp3", ".flac", ".m4a", ".ogg", ".opus"}


def get_default_voice() -> str:
    """Get the default voice from configuration"""
    voice_config = get_voice_config()
    return voice_config["default_voice"]


# For backward compatibility
DEFAULT_VOICE = "alloy"  # Will be overridden by config on first access

