"""
FastAPI REST API wrapper for IndexTTS2
Provides HTTP endpoints for text-to-speech synthesis
Includes OpenAI-compatible endpoints for easy integration
"""
import os
import tempfile
import uuid
from typing import List, Optional, Literal

import torch
from fastapi import FastAPI, File, Form, HTTPException, UploadFile, status, APIRouter
from fastapi.responses import FileResponse, JSONResponse, Response
from pydantic import BaseModel, Field

from indextts.infer_v2 import IndexTTS2
from .config import (
    get_model_config,
    get_auto_download_config,
    get_voice_directories,
    OPENAI_VOICE_MAP,
    DEFAULT_VOICE,
    AUDIO_EXTENSIONS,
)
from .model_downloader import ensure_checkpoints

# Initialize FastAPI app
app = FastAPI(
    title="IndexTTS2 API",
    description="REST API for IndexTTS2: Emotionally Expressive and Duration-Controlled Zero-Shot Text-to-Speech",
    version="1.0.0",
)

# Global model instance
tts_model: Optional[IndexTTS2] = None
model_config = get_model_config()
auto_download_config = get_auto_download_config()

# Get voice directories from config
VOICE_DIRECTORIES = get_voice_directories()


def get_app():
    """Factory function to get the FastAPI app instance"""
    return app


def discover_voice_files() -> dict:
    """
    Dynamically discover all available voice files in configured directories.
    
    Returns:
        dict: Mapping of voice names to file paths
    """
    voices = {}
    
    # Start with preset mappings
    voices.update(OPENAI_VOICE_MAP)
    
    # Scan configured directories
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    for directory in VOICE_DIRECTORIES:
        # Resolve directory path - try project root first, then index-tts
        if not os.path.isabs(directory):
            # Try project root first (default)
            full_dir = os.path.join(project_root, directory)
            if not os.path.exists(full_dir):
                # Fallback to index-tts directory
                full_dir = os.path.join(project_root, "index-tts", directory)
                if not os.path.exists(full_dir):
                    # Try current working directory
                    full_dir = os.path.join(os.getcwd(), directory)
                    if not os.path.exists(full_dir):
                        continue
            directory = full_dir
        elif not os.path.exists(directory):
            continue
        
        for filename in os.listdir(directory):
            file_path = os.path.join(directory, filename)
            
            # Skip if not a file or not an audio file
            if not os.path.isfile(file_path):
                continue
            
            # Check if it's an audio file
            _, ext = os.path.splitext(filename.lower())
            if ext not in AUDIO_EXTENSIONS:
                continue
            
            # Skip emotion reference files
            if "emo_" in filename.lower():
                continue
            
            # Create voice name from filename (without extension)
            voice_name = os.path.splitext(filename)[0]
            
            # Use filename as key, or a cleaned version
            # If it's already in the map, skip to avoid overwriting presets
            if voice_name not in voices:
                voices[voice_name] = file_path
    
    return voices


def get_voice_file(voice_identifier: str) -> Optional[str]:
    """
    Get voice file path from identifier.
    
    Supports:
    - Preset names (e.g., "alloy", "echo")
    - Voice names from discovered files (e.g., "voice_01")
    - Direct file paths (absolute or relative)
    
    Args:
        voice_identifier: Voice name or file path
        
    Returns:
        str: Path to voice file, or None if not found
    """
    # First check preset mappings
    if voice_identifier in OPENAI_VOICE_MAP:
        voice_path = OPENAI_VOICE_MAP[voice_identifier]
        # Resolve relative paths
        if not os.path.isabs(voice_path):
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            
            # Priority 1: Try project root first (default location)
            full_path = os.path.join(project_root, voice_path)
            if os.path.exists(full_path):
                return full_path
            
            # Priority 2: Try current working directory
            cwd_path = os.path.join(os.getcwd(), voice_path)
            if os.path.exists(cwd_path):
                return os.path.abspath(cwd_path)
            
            # Priority 3: Try index-tts directory (fallback for backward compatibility)
            index_tts_path = os.path.join(project_root, "index-tts", voice_path)
            if os.path.exists(index_tts_path):
                return index_tts_path
        elif os.path.exists(voice_path):
            return voice_path
        return None
    
    # Check discovered voices
    discovered = discover_voice_files()
    if voice_identifier in discovered:
        voice_path = discovered[voice_identifier]
        if os.path.exists(voice_path):
            return voice_path
        # Try to resolve relative paths
        if not os.path.isabs(voice_path):
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            
            # Priority 1: Try project root first
            full_path = os.path.join(project_root, voice_path)
            if os.path.exists(full_path):
                return full_path
            
            # Priority 2: Try current working directory
            cwd_path = os.path.join(os.getcwd(), voice_path)
            if os.path.exists(cwd_path):
                return os.path.abspath(cwd_path)
            
            # Priority 3: Try index-tts directory (fallback)
            index_tts_path = os.path.join(project_root, "index-tts", voice_path)
            if os.path.exists(index_tts_path):
                return index_tts_path
    
    # Check if it's a direct file path
    if os.path.exists(voice_identifier):
        return os.path.abspath(voice_identifier)
    
    # Check relative to current directory
    cwd_path = os.path.join(os.getcwd(), voice_identifier)
    if os.path.exists(cwd_path):
        return os.path.abspath(cwd_path)
    
    # Check relative to project root
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    project_path = os.path.join(project_root, voice_identifier)
    if os.path.exists(project_path):
        return project_path
    
    # Check relative to index-tts
    index_tts_path = os.path.join(project_root, "index-tts", voice_identifier)
    if os.path.exists(index_tts_path):
        return index_tts_path
    
    return None


# Request/Response Models
class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
    device: Optional[str] = None
    model_version: Optional[str] = None


class ModelInfoResponse(BaseModel):
    model_version: Optional[str]
    device: str
    use_fp16: bool
    use_cuda_kernel: bool
    use_deepspeed: bool
    use_accel: bool
    use_torch_compile: bool


# OpenAI-compatible request models
class VoiceInfo(BaseModel):
    """Voice information model"""
    id: str
    name: str
    file_path: str
    is_preset: bool


class VoicesResponse(BaseModel):
    """Response model for voices list"""
    object: str = "list"
    data: List[VoiceInfo]


class OpenAITTSRequest(BaseModel):
    """OpenAI-compatible TTS request model"""
    model: str = Field(
        default="tts-1",
        description="Model to use (tts-1 or tts-1-hd). Note: IndexTTS2 uses its own model, this parameter is for compatibility."
    )
    input: str = Field(..., description="Text to synthesize", min_length=1)
    voice: str = Field(
        default="alloy",
        description="Voice to use. Can be: preset name (alloy, echo, fable, onyx, nova, shimmer), discovered voice name, or file path."
    )
    response_format: Literal["mp3", "opus", "aac", "flac", "pcm", "wav"] = Field(
        default="mp3",
        description="Audio format (wav recommended for best quality)"
    )
    speed: float = Field(
        default=1.0,
        ge=0.25,
        le=4.0,
        description="Speed multiplier (0.25-4.0). Note: IndexTTS2 doesn't support speed control directly, this may be ignored."
    )


class TTSRequest(BaseModel):
    """Request model for JSON-based TTS requests"""
    text: str = Field(..., description="Text to synthesize")
    spk_audio_prompt: Optional[str] = Field(
        None, description="Path to speaker reference audio file (if using file path instead of upload)"
    )
    emo_audio_prompt: Optional[str] = Field(
        None, description="Path to emotion reference audio file (optional)"
    )
    emo_alpha: float = Field(0.65, ge=0.0, le=1.0, description="Emotion weight (0.0-1.0)")
    emo_vector: Optional[List[float]] = Field(
        None,
        description="8-element emotion vector [happy, angry, sad, afraid, disgusted, melancholic, surprised, calm]",
        min_length=8,
        max_length=8,
    )
    use_emo_text: bool = Field(False, description="Use text-based emotion detection")
    emo_text: Optional[str] = Field(None, description="Emotion description text (if use_emo_text=True)")
    use_random: bool = Field(False, description="Enable random emotion sampling")
    max_text_tokens_per_segment: int = Field(120, ge=20, description="Max tokens per segment")
    # Generation parameters
    do_sample: bool = Field(True, description="Enable sampling")
    top_p: float = Field(0.8, ge=0.0, le=1.0, description="Top-p sampling parameter")
    top_k: int = Field(30, ge=0, description="Top-k sampling parameter")
    temperature: float = Field(0.8, ge=0.1, le=2.0, description="Sampling temperature")
    num_beams: int = Field(3, ge=1, le=10, description="Number of beams for beam search")
    repetition_penalty: float = Field(10.0, ge=0.1, le=20.0, description="Repetition penalty")
    length_penalty: float = Field(0.0, ge=-2.0, le=2.0, description="Length penalty")
    max_mel_tokens: int = Field(1500, ge=50, description="Maximum mel tokens to generate")
    interval_silence: int = Field(200, ge=0, description="Silence interval between segments (ms)")
    verbose: bool = Field(False, description="Enable verbose logging")


# Startup and shutdown events
@app.on_event("startup")
async def load_model():
    """Load the TTS model on startup"""
    global tts_model
    try:
        # Get configuration
        cfg_path = model_config["cfg_path"]
        model_dir = model_config["model_dir"]
        
        # Ensure checkpoints exist (auto-download if enabled)
        print(">> Checking for IndexTTS2 checkpoints...")
        checkpoints_ok = ensure_checkpoints(
            model_dir=model_dir,
            repo_id=auto_download_config["hf_repo"],
            auto_download=auto_download_config["auto_download"]
        )
        
        if not checkpoints_ok:
            raise FileNotFoundError(
                f"Required checkpoints are missing in {model_dir}. "
                f"Please download them manually or enable auto-download."
            )
        
        # Verify config file exists
        if not os.path.exists(cfg_path):
            raise FileNotFoundError(f"Config file not found: {cfg_path}")
        
        # Create model directory if it doesn't exist
        if not os.path.exists(model_dir):
            os.makedirs(model_dir, exist_ok=True)
        
        print(f">> Loading IndexTTS2 model from {model_dir}...")
        tts_model = IndexTTS2(**model_config)
        print(">> Model loaded successfully!")
    except Exception as e:
        print(f">> ERROR: Failed to load model: {e}")
        tts_model = None
        raise


@app.on_event("shutdown")
async def cleanup():
    """Cleanup on shutdown"""
    global tts_model
    if tts_model is not None:
        # Clear CUDA cache if using GPU
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    tts_model = None


# API Endpoints
@app.get("/", response_model=dict)
async def root():
    """Root endpoint with API information"""
    return {
        "name": "IndexTTS2 API",
        "version": "2.0.0",
        "description": "REST API for IndexTTS2 Text-to-Speech",
        "endpoints": {
            "health": "/health",
            "model_info": "/model/info",
            "tts": "/api/v1/tts",
            "docs": "/docs",
        },
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    device = None
    model_version = None
    
    if tts_model is not None:
        device = str(tts_model.device)
        # Convert model_version to string if it's not already
        model_version = str(tts_model.model_version) if tts_model.model_version is not None else None
    
    return HealthResponse(
        status="healthy" if tts_model is not None else "unhealthy",
        model_loaded=tts_model is not None,
        device=device,
        model_version=model_version,
    )


@app.get("/model/info", response_model=ModelInfoResponse)
async def model_info():
    """Get model information"""
    if tts_model is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Model not loaded",
        )
    
    return ModelInfoResponse(
        model_version=str(tts_model.model_version) if tts_model.model_version is not None else None,
        device=str(tts_model.device),
        use_fp16=tts_model.use_fp16,
        use_cuda_kernel=tts_model.use_cuda_kernel,
        use_deepspeed=model_config.get("use_deepspeed", False),
        use_accel=tts_model.use_accel,
        use_torch_compile=tts_model.use_torch_compile,
    )


@app.post("/api/v1/tts")
async def synthesize_speech(
    text: str = Form(..., description="Text to synthesize"),
    spk_audio_prompt: UploadFile = File(..., description="Speaker reference audio file"),
    emo_audio_prompt: Optional[UploadFile] = File(None, description="Emotion reference audio file (optional)"),
    emo_alpha: float = Form(0.65, ge=0.0, le=1.0, description="Emotion weight"),
    emo_vector: Optional[str] = Form(
        None,
        description="Comma-separated emotion vector [happy,angry,sad,afraid,disgusted,melancholic,surprised,calm]",
    ),
    use_emo_text: bool = Form(False, description="Use text-based emotion detection"),
    emo_text: Optional[str] = Form(None, description="Emotion description text"),
    use_random: bool = Form(False, description="Enable random emotion sampling"),
    max_text_tokens_per_segment: int = Form(120, ge=20, description="Max tokens per segment"),
    do_sample: bool = Form(True, description="Enable sampling"),
    top_p: float = Form(0.8, ge=0.0, le=1.0, description="Top-p sampling"),
    top_k: int = Form(30, ge=0, description="Top-k sampling"),
    temperature: float = Form(0.8, ge=0.1, le=2.0, description="Temperature"),
    num_beams: int = Form(3, ge=1, le=10, description="Number of beams"),
    repetition_penalty: float = Form(10.0, ge=0.1, le=20.0, description="Repetition penalty"),
    length_penalty: float = Form(0.0, ge=-2.0, le=2.0, description="Length penalty"),
    max_mel_tokens: int = Form(1500, ge=50, description="Max mel tokens"),
    interval_silence: int = Form(200, ge=0, description="Interval silence (ms)"),
    verbose: bool = Form(False, description="Verbose logging"),
):
    """
    Synthesize speech from text with voice cloning
    
    This endpoint accepts:
    - Text to synthesize
    - Speaker reference audio file (required)
    - Optional emotion reference audio file
    - Various generation parameters
    """
    if tts_model is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Model not loaded. Please check /health endpoint.",
        )
    
    if not text or not text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Text cannot be empty",
        )
    
    # Validate audio file
    if not spk_audio_prompt.content_type or not spk_audio_prompt.content_type.startswith("audio/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="spk_audio_prompt must be an audio file",
        )
    
    # Parse emotion vector if provided
    parsed_emo_vector = None
    if emo_vector:
        try:
            parsed_emo_vector = [float(x.strip()) for x in emo_vector.split(",")]
            if len(parsed_emo_vector) != 8:
                raise ValueError("Emotion vector must have exactly 8 elements")
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid emotion vector format: {e}",
            )
    
    # Create temporary directory for files
    temp_dir = tempfile.mkdtemp()
    
    try:
        # Save uploaded audio files
        spk_audio_path = os.path.join(temp_dir, f"spk_{uuid.uuid4()}.wav")
        with open(spk_audio_path, "wb") as f:
            content = await spk_audio_prompt.read()
            f.write(content)
        
        emo_audio_path = None
        if emo_audio_prompt:
            emo_audio_path = os.path.join(temp_dir, f"emo_{uuid.uuid4()}.wav")
            with open(emo_audio_path, "wb") as f:
                content = await emo_audio_prompt.read()
                f.write(content)
        
        # Generate output file path
        output_filename = f"tts_{uuid.uuid4()}.wav"
        output_path = os.path.join(temp_dir, output_filename)
        
        # Prepare generation kwargs
        generation_kwargs = {
            "do_sample": do_sample,
            "top_p": top_p,
            "top_k": top_k if top_k > 0 else None,
            "temperature": temperature,
            "num_beams": num_beams,
            "repetition_penalty": repetition_penalty,
            "length_penalty": length_penalty,
            "max_mel_tokens": max_mel_tokens,
        }
        
        # Call TTS model
        result = tts_model.infer(
            spk_audio_prompt=spk_audio_path,
            text=text.strip(),
            output_path=output_path,
            emo_audio_prompt=emo_audio_path,
            emo_alpha=emo_alpha,
            emo_vector=parsed_emo_vector,
            use_emo_text=use_emo_text,
            emo_text=emo_text,
            use_random=use_random,
            interval_silence=interval_silence,
            verbose=verbose,
            max_text_tokens_per_segment=max_text_tokens_per_segment,
            **generation_kwargs,
        )
        
        if result is None or not os.path.exists(output_path):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate audio",
            )
        
        # Return audio file
        # Note: FileResponse will handle file cleanup after sending
        return FileResponse(
            output_path,
            media_type="audio/wav",
            filename=output_filename,
        )
    
    except Exception as e:
        # Cleanup on error
        import shutil
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error during synthesis: {str(e)}",
        )


@app.post("/api/v1/tts/json", response_class=FileResponse)
async def synthesize_speech_json(request: TTSRequest):
    """
    Synthesize speech from JSON request
    
    This endpoint accepts a JSON body instead of form data.
    Note: For file uploads, use the /api/v1/tts endpoint instead.
    """
    if tts_model is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Model not loaded. Please check /health endpoint.",
        )
    
    if not request.text or not request.text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Text cannot be empty",
        )
    
    # If using file paths instead of uploads
    if not request.spk_audio_prompt or not os.path.exists(request.spk_audio_prompt):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="spk_audio_prompt file path does not exist",
        )
    
    emo_audio_path = None
    if request.emo_audio_prompt:
        if not os.path.exists(request.emo_audio_prompt):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="emo_audio_prompt file path does not exist",
            )
        emo_audio_path = request.emo_audio_prompt
    
    # Create temporary directory for output
    temp_dir = tempfile.mkdtemp()
    output_filename = f"tts_{uuid.uuid4()}.wav"
    output_path = os.path.join(temp_dir, output_filename)
    
    try:
        # Prepare generation kwargs
        generation_kwargs = {
            "do_sample": request.do_sample,
            "top_p": request.top_p,
            "top_k": request.top_k if request.top_k > 0 else None,
            "temperature": request.temperature,
            "num_beams": request.num_beams,
            "repetition_penalty": request.repetition_penalty,
            "length_penalty": request.length_penalty,
            "max_mel_tokens": request.max_mel_tokens,
        }
        
        # Call TTS model
        result = tts_model.infer(
            spk_audio_prompt=request.spk_audio_prompt,
            text=request.text.strip(),
            output_path=output_path,
            emo_audio_prompt=emo_audio_path,
            emo_alpha=request.emo_alpha,
            emo_vector=request.emo_vector,
            use_emo_text=request.use_emo_text,
            emo_text=request.emo_text,
            use_random=request.use_random,
            interval_silence=request.interval_silence,
            verbose=request.verbose,
            max_text_tokens_per_segment=request.max_text_tokens_per_segment,
            **generation_kwargs,
        )
        
        if result is None or not os.path.exists(output_path):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate audio",
            )
        
        # Return audio file
        return FileResponse(
            output_path,
            media_type="audio/wav",
            filename=output_filename,
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error during synthesis: {str(e)}",
        )


# OpenAI-compatible endpoints
@app.post("/v1/audio/speech")
async def openai_audio_speech(request: OpenAITTSRequest):
    """
    OpenAI-compatible TTS endpoint
    
    This endpoint matches OpenAI's /v1/audio/speech API format,
    making it a drop-in replacement for OpenAI TTS.
    
    Example using OpenAI Python SDK:
    ```python
    from openai import OpenAI
    
    client = OpenAI(
        base_url="http://localhost:8000/v1",
        api_key="not-needed"  # API key not required for local use
    )
    
    response = client.audio.speech.create(
        model="tts-1",
        voice="alloy",
        input="Hello, this is a test!"
    )
    
    response.stream_to_file("output.mp3")
    ```
    """
    if tts_model is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Model not loaded. Please check /health endpoint.",
        )
    
    if not request.input or not request.input.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="input cannot be empty",
        )
    
    # Get voice file path (supports preset names, discovered voices, or file paths)
    voice_file = get_voice_file(request.voice)
    
    if voice_file is None:
        # Try default voice
        voice_file = get_voice_file(DEFAULT_VOICE)
        if voice_file is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Voice '{request.voice}' not found. Use /v1/voices to list available voices.",
            )
    
    if not os.path.exists(voice_file):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Voice file not found: {voice_file}. Please ensure the voice file exists.",
        )
    
    # Create temporary directory
    temp_dir = tempfile.mkdtemp()
    
    try:
        # Generate output file
        output_filename = f"tts_{uuid.uuid4()}.wav"
        output_path = os.path.join(temp_dir, output_filename)
        
        # Call TTS model with default settings optimized for OpenAI compatibility
        result = tts_model.infer(
            spk_audio_prompt=voice_file,
            text=request.input.strip(),
            output_path=output_path,
            emo_audio_prompt=None,
            emo_alpha=1.0,
            emo_vector=None,
            use_emo_text=False,
            emo_text=None,
            use_random=False,
            interval_silence=200,
            verbose=False,
            max_text_tokens_per_segment=120,
            do_sample=True,
            top_p=0.8,
            top_k=30,
            temperature=0.8,
            num_beams=3,
            repetition_penalty=10.0,
            length_penalty=0.0,
            max_mel_tokens=1500,
        )
        
        if result is None or not os.path.exists(output_path):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate audio",
            )
        
        # Convert to requested format if needed
        output_file = output_path
        media_type = "audio/wav"
        
        if request.response_format != "wav":
            try:
                from pydub import AudioSegment
                
                # Load WAV file
                audio = AudioSegment.from_wav(output_path)
                
                # Convert based on requested format
                converted_path = os.path.join(temp_dir, f"tts_{uuid.uuid4()}.{request.response_format}")
                
                if request.response_format == "mp3":
                    audio.export(converted_path, format="mp3")
                    media_type = "audio/mpeg"
                elif request.response_format == "opus":
                    audio.export(converted_path, format="opus")
                    media_type = "audio/opus"
                elif request.response_format == "aac":
                    audio.export(converted_path, format="aac")
                    media_type = "audio/aac"
                elif request.response_format == "flac":
                    audio.export(converted_path, format="flac")
                    media_type = "audio/flac"
                elif request.response_format == "pcm":
                    # PCM is raw audio, export as WAV with PCM encoding
                    audio.export(converted_path, format="wav", parameters=["-acodec", "pcm_s16le"])
                    media_type = "audio/pcm"
                
                output_file = converted_path
            except ImportError:
                # pydub not available, return WAV with note
                # In production, ensure pydub is installed for format conversion
                pass
            except Exception as e:
                # Conversion failed, fall back to WAV
                print(f"Warning: Audio format conversion failed: {e}. Returning WAV format.")
                pass
        
        # Handle speed parameter (if needed, would require audio processing)
        # For now, we'll note that speed control isn't directly supported
        # but the parameter is accepted for compatibility
        
        # Return audio file
        return FileResponse(
            output_file,
            media_type=media_type,
            filename=f"speech.{request.response_format}",
        )
    
    except Exception as e:
        import shutil
        import traceback
        error_msg = str(e) if str(e) else repr(e)
        error_trace = traceback.format_exc()
        print(f">> ERROR in TTS synthesis: {error_msg}")
        print(f">> Traceback: {error_trace}")
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error during synthesis: {error_msg}",
        )


@app.get("/v1/models")
async def openai_models():
    """
    OpenAI-compatible models endpoint
    
    Returns available models for compatibility with OpenAI SDK.
    """
    return {
        "object": "list",
        "data": [
            {
                "id": "tts-1",
                "object": "model",
                "created": 1677610602,
                "owned_by": "indextts",
                "permission": [],
                "root": "tts-1",
                "parent": None
            },
            {
                "id": "tts-1-hd",
                "object": "model",
                "created": 1677610602,
                "owned_by": "indextts",
                "permission": [],
                "root": "tts-1-hd",
                "parent": None
            }
        ]
    }


@app.get("/v1/voices", response_model=VoicesResponse)
async def list_voices():
    """
    List all available voices
    
    Returns all discovered voice files including:
    - Preset OpenAI-compatible voices (alloy, echo, etc.)
    - Automatically discovered voices from configured directories
    - Shows both preset and custom voices
    """
    discovered = discover_voice_files()
    voices_list = []
    
    # Add preset voices
    for voice_id, file_path in OPENAI_VOICE_MAP.items():
        voices_list.append(VoiceInfo(
            id=voice_id,
            name=voice_id,
            file_path=file_path,
            is_preset=True
        ))
    
    # Add discovered voices (excluding presets)
    for voice_id, file_path in discovered.items():
        if voice_id not in OPENAI_VOICE_MAP:
            # Get a clean name from the file path
            voice_name = os.path.splitext(os.path.basename(file_path))[0]
            voices_list.append(VoiceInfo(
                id=voice_id,
                name=voice_name,
                file_path=file_path,
                is_preset=False
            ))
    
    return VoicesResponse(data=voices_list)


@app.get("/v1/audio/voices", response_model=VoicesResponse)
async def list_voices_audio():
    """
    List all available voices (OpenAI-compatible path)
    
    This endpoint is under /v1/audio/ to match OpenAI API structure.
    Same functionality as /v1/voices.
    """
    return await list_voices()


@app.get("/api/v1/voices", response_model=VoicesResponse)
async def list_voices_native():
    """
    List all available voices (native API endpoint)
    
    Same as /v1/voices but using native API path.
    """
    return await list_voices()


def main():
    """Main entry point for running the API server"""
    import uvicorn
    
    # Get port from environment variable, default to 9877
    port = int(os.getenv("INDEXTTS_PORT", "9877"))
    host = os.getenv("INDEXTTS_HOST", "0.0.0.0")
    
    uvicorn.run(
        "indextts_fastapi.api:app",
        host=host,
        port=port,
        reload=False,  # Set to True for development
    )


if __name__ == "__main__":
    main()

