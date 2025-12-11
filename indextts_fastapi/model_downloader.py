"""
Model downloader for IndexTTS2 checkpoints
Auto-downloads checkpoints from HuggingFace if missing
"""
import os
import sys
from pathlib import Path
from typing import List, Optional, Tuple

try:
    from huggingface_hub import snapshot_download, hf_hub_download
    from huggingface_hub.utils import HfHubHTTPError
except ImportError:
    print("ERROR: huggingface_hub is not installed. Install it with: pip install huggingface_hub")
    sys.exit(1)


# Required checkpoint files (from config.yaml analysis)
REQUIRED_FILES = [
    "gpt.pth",
    "s2mel.pth",
    "bpe.model",
    "wav2vec2bert_stats.pt",
    "feat1.pt",
    "feat2.pt",
    "config.yaml",
    "pinyin.vocab",
]

# Required directories
REQUIRED_DIRS = [
    "qwen0.6bemo4-merge",
]


def check_checkpoints_exist(model_dir: str) -> Tuple[bool, List[str]]:
    """
    Check if all required checkpoint files exist.
    
    Args:
        model_dir: Path to the model directory
        
    Returns:
        Tuple of (all_exist, missing_files)
    """
    model_path = Path(model_dir)
    missing = []
    
    # Check required files
    for file in REQUIRED_FILES:
        file_path = model_path / file
        if not file_path.exists():
            missing.append(file)
    
    # Check required directories
    for dir_name in REQUIRED_DIRS:
        dir_path = model_path / dir_name
        if not dir_path.exists() or not dir_path.is_dir():
            missing.append(f"{dir_name}/")
    
    return len(missing) == 0, missing


def download_checkpoints(
    repo_id: str = "IndexTeam/IndexTTS-2",
    local_dir: str = "checkpoints",
    force_download: bool = False
) -> str:
    """
    Download IndexTTS2 checkpoints from HuggingFace.
    
    Args:
        repo_id: HuggingFace repository ID
        local_dir: Local directory to save checkpoints
        force_download: Force re-download even if files exist
        
    Returns:
        Path to the downloaded checkpoint directory
    """
    local_path = Path(local_dir)
    local_path.mkdir(parents=True, exist_ok=True)
    
    print(f">> Downloading IndexTTS2 checkpoints from {repo_id}...")
    print(f">> Target directory: {local_path.absolute()}")
    
    try:
        # Use snapshot_download to download entire repo
        downloaded_path = snapshot_download(
            repo_id=repo_id,
            local_dir=str(local_path),
            local_dir_use_symlinks=False,
            force_download=force_download,
            resume_download=True,
        )
        
        print(f">> Checkpoints downloaded successfully to: {downloaded_path}")
        return downloaded_path
        
    except HfHubHTTPError as e:
        print(f">> ERROR: Failed to download checkpoints: {e}")
        print(f">> Please check your internet connection and HuggingFace access.")
        raise
    except Exception as e:
        print(f">> ERROR: Unexpected error during download: {e}")
        raise


def ensure_checkpoints(
    model_dir: str,
    repo_id: str = "IndexTeam/IndexTTS-2",
    auto_download: bool = True
) -> bool:
    """
    Ensure all required checkpoints exist, downloading if necessary.
    
    Args:
        model_dir: Path to the model directory
        repo_id: HuggingFace repository ID
        auto_download: Whether to auto-download if missing
        
    Returns:
        True if all checkpoints exist, False otherwise
    """
    all_exist, missing = check_checkpoints_exist(model_dir)
    
    if all_exist:
        print(f">> All checkpoints found in {model_dir}")
        return True
    
    print(f">> Missing checkpoints: {', '.join(missing)}")
    
    if not auto_download:
        print(">> Auto-download is disabled. Please download checkpoints manually:")
        print(f">>   hf download {repo_id} --local-dir={model_dir}")
        return False
    
    print(">> Auto-downloading missing checkpoints...")
    try:
        download_checkpoints(repo_id=repo_id, local_dir=model_dir)
        
        # Verify after download
        all_exist, missing = check_checkpoints_exist(model_dir)
        if all_exist:
            print(">> All checkpoints verified successfully!")
            return True
        else:
            # Try to copy missing files from index-tts checkpoints if available
            model_path = Path(model_dir).resolve()
            # Try multiple possible locations for index-tts checkpoints
            possible_locations = [
                model_path.parent / "index-tts" / "checkpoints",
                Path.cwd() / "index-tts" / "checkpoints",
                Path(__file__).parent.parent.parent / "index-tts" / "checkpoints",
            ]
            
            copied_any = False
            for index_tts_checkpoints in possible_locations:
                if index_tts_checkpoints.exists():
                    for file in missing[:]:  # Use slice to avoid modifying during iteration
                        source_file = index_tts_checkpoints / file
                        if source_file.exists():
                            dest_file = model_path / file
                            print(f">> Copying {file} from {index_tts_checkpoints}...")
                            import shutil
                            shutil.copy2(source_file, dest_file)
                            missing.remove(file)
                            copied_any = True
                    if copied_any:
                        break
            
            # Re-check after copying
            all_exist, missing = check_checkpoints_exist(model_dir)
            if all_exist:
                print(">> All checkpoints verified successfully!")
                return True
            else:
                print(f">> WARNING: Some files are still missing after download: {', '.join(missing)}")
                return False
            
    except Exception as e:
        print(f">> Failed to download checkpoints: {e}")
        return False


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Download IndexTTS2 checkpoints")
    parser.add_argument(
        "--repo-id",
        type=str,
        default="IndexTeam/IndexTTS-2",
        help="HuggingFace repository ID"
    )
    parser.add_argument(
        "--local-dir",
        type=str,
        default="checkpoints",
        help="Local directory to save checkpoints"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-download even if files exist"
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Only check if checkpoints exist, don't download"
    )
    
    args = parser.parse_args()
    
    if args.check_only:
        all_exist, missing = check_checkpoints_exist(args.local_dir)
        if all_exist:
            print(">> All checkpoints exist!")
            sys.exit(0)
        else:
            print(f">> Missing: {', '.join(missing)}")
            sys.exit(1)
    else:
        download_checkpoints(
            repo_id=args.repo_id,
            local_dir=args.local_dir,
            force_download=args.force
        )

