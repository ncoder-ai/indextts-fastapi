# Docker Build Optimization Tips

## Why builds are slow

The Docker build takes a long time because:

1. **Flash-attention compilation** - Takes 10-30+ minutes to compile from source
2. **IndexTTS cloning** - Clones the entire repository each time
3. **Layer invalidation** - Code changes invalidate expensive compilation steps

## Optimizations applied

1. **Layer reordering** - Stable dependencies (flash-attention, IndexTTS) are installed BEFORE code copying
   - Code changes no longer invalidate expensive compilation
   - Only wrapper code changes trigger fast reinstall

2. **Docker layer caching** - Each layer is cached independently
   - If only `indextts_fastapi/api.py` changes, flash-attention won't recompile

## Further optimization with BuildKit

Enable BuildKit for even better caching:

```bash
# Enable BuildKit (one-time setup)
export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1

# Or add to ~/.docker/config.json
{
  "features": {
    "buildkit": true
  }
}
```

Then rebuild:
```bash
docker-compose build --progress=plain
```

## Build time breakdown

- **Flash-attention compilation**: ~15-30 minutes (cached after first build)
- **IndexTTS installation**: ~2-5 minutes (cached unless repo changes)
- **Wrapper dependencies**: ~30 seconds (cached unless pyproject.toml changes)
- **Code copying**: <1 second

## When full rebuild is needed

Full rebuild happens when:
- Dockerfile changes (especially early layers)
- Base image changes
- IndexTTS repo URL changes
- Python version changes
- Build dependencies change

Partial rebuild (fast) happens when:
- Only wrapper code changes (`indextts_fastapi/`)
- Only `pyproject.toml` changes
- Only `docker-compose.yml` changes (no rebuild needed, just restart)

## Tips

1. **Use `--no-cache` sparingly** - Only when you suspect cache issues
2. **Keep Dockerfile stable** - Put frequently changing files at the end
3. **Use multi-stage builds** - Already implemented for minimal final image
4. **Consider pre-built wheels** - Flash-attention wheels exist but may not match CUDA version
