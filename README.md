# IndexTTS FastAPI

FastAPI REST API wrapper for [IndexTTS2](https://github.com/index-tts/index-tts) with **OpenAI-compatible endpoints**.

## Features

- 🚀 **FastAPI-based REST API** for IndexTTS2
- 🤖 **OpenAI-compatible endpoints** - drop-in replacement for OpenAI TTS
- 🎤 **Dynamic voice discovery** - automatically finds all available voices
- 📦 **Standalone package** - easy to install and deploy
- 🔧 **Configurable** via environment variables
- 📝 **Interactive API docs** at `/docs`

## Installation

### Prerequisites

1. Install [IndexTTS2](https://github.com/index-tts/index-tts) first:
   ```bash
   git clone https://github.com/index-tts/index-tts.git
   cd index-tts
   uv sync --all-extras
   ```

2. Download the IndexTTS2 model:
   ```bash
   hf download IndexTeam/IndexTTS-2 --local-dir=checkpoints
   ```

### Install IndexTTS FastAPI

```bash
pip install indextts-fastapi
```

Or from source:
```bash
git clone https://github.com/yourusername/index-tts-fastapi.git
cd index-tts-fastapi
pip install -e .
```

## Quick Start

### 1. Set up environment variables (optional)

```bash
export INDEXTTS_MODEL_DIR="checkpoints"
export INDEXTTS_CFG_PATH="checkpoints/config.yaml"
export INDEXTTS_USE_FP16="true"  # Enabled by default for lower VRAM usage
export INDEXTTS_USE_DEEPSPEED="true"  # Enabled by default for multi-GPU support
```

### 2. Run the API server

```bash
indextts-api
```

Or using uvicorn directly:
```bash
uvicorn indextts_fastapi.api:app --host 0.0.0.0 --port 8000
```

### 3. Access the API

- API: `http://localhost:8000`
- Interactive Docs: `http://localhost:8000/docs`
- Health Check: `http://localhost:8000/health`

## Usage Examples

### OpenAI-Compatible API

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:8000/v1",
    api_key="not-needed"
)

response = client.audio.speech.create(
    model="tts-1",
    voice="alloy",
    input="Hello from IndexTTS2!"
)

response.stream_to_file("output.mp3")
```

### Direct HTTP Request

```bash
curl -X POST "http://localhost:8000/v1/audio/speech" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "tts-1",
    "input": "Hello, world!",
    "voice": "alloy",
    "response_format": "wav"
  }' \
  --output output.wav
```

### Native API with File Upload

```bash
curl -X POST "http://localhost:8000/api/v1/tts" \
  -F "text=Hello, this is a test" \
  -F "spk_audio_prompt=@path/to/voice.wav" \
  -o output.wav
```

## API Endpoints

### OpenAI-Compatible Endpoints

- `POST /v1/audio/speech` - Generate speech (OpenAI-compatible)
- `GET /v1/models` - List available models
- `GET /v1/voices` - List all available voices

### Native Endpoints

- `POST /api/v1/tts` - Generate speech with file upload
- `POST /api/v1/tts/json` - Generate speech with JSON request
- `GET /api/v1/voices` - List all available voices
- `GET /health` - Health check
- `GET /model/info` - Model information

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `INDEXTTS_MODEL_DIR` | `checkpoints` | Path to model directory |
| `INDEXTTS_CFG_PATH` | `checkpoints/config.yaml` | Path to config file |
| `INDEXTTS_USE_FP16` | `false` | Use FP16 for lower VRAM |
| `INDEXTTS_USE_CUDA_KERNEL` | `false` | Use CUDA kernel acceleration |
| `INDEXTTS_USE_DEEPSPEED` | `false` | Use DeepSpeed acceleration (optimization only, not model parallelism) |
| `INDEXTTS_USE_ACCEL` | `false` | Use acceleration engine |
| `INDEXTTS_USE_TORCH_COMPILE` | `false` | Use torch.compile optimization |
| `INDEXTTS_VOICE_DIR` | `examples` | Voice directory path (relative to project root or absolute) |

### Voice Discovery

The API automatically discovers voice files from a single configured directory. Supported formats:
- `.wav`, `.mp3`, `.flac`, `.m4a`, `.ogg`, `.opus`

**Configuration:**
- Set `INDEXTTS_VOICE_DIR` environment variable to specify the voice directory
- Default: `examples` (relative to project root)
- In Docker: Set to `/app/examples` to match the mounted volume

**Voice files are identified by their filename (without extension):**
- `voice_01.wav` → voice ID: `voice_01`
- `voice_12.wav` → voice ID: `voice_12`

List all available voices:
```bash
curl http://localhost:8000/v1/voices
```

## Development

```bash
# Clone the repository
git clone https://github.com/yourusername/index-tts-fastapi.git
cd index-tts-fastapi

# Install in development mode
pip install -e ".[dev]"

# Run tests
pytest

# Format code
black indextts_fastapi/
ruff check indextts_fastapi/
```

## Integration Examples

### With LangChain

```python
import os
os.environ["OPENAI_API_BASE"] = "http://localhost:8000/v1"
os.environ["OPENAI_API_KEY"] = "not-needed"

# Use with LangChain (if it supports TTS)
```

### With Custom Applications

Any application using OpenAI SDK can be configured:

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:8000/v1",
    api_key="not-needed"
)

# Use normally
response = client.audio.speech.create(...)
```

## Differences from OpenAI TTS

1. **Voice System**: Uses zero-shot voice cloning with reference audio files
2. **Speed Control**: The `speed` parameter is accepted but not implemented
3. **Model Parameter**: Both "tts-1" and "tts-1-hd" work the same way
4. **Custom Voices**: Supports custom voice files via discovery or file paths

## License

This package is provided as-is. Please refer to the [IndexTTS2 license](https://github.com/index-tts/index-tts) for model usage terms.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Acknowledgments

- [IndexTTS2](https://github.com/index-tts/index-tts) - The underlying TTS model
- [FastAPI](https://fastapi.tiangolo.com/) - The web framework
- [OpenAI](https://openai.com/) - For the API compatibility standard

## Support

For issues related to:
- **This FastAPI wrapper**: Open an issue in this repository
- **IndexTTS2 model**: See [IndexTTS2 repository](https://github.com/index-tts/index-tts)

