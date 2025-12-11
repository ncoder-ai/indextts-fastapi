# Setting up the GitHub Repository

## Initial Setup

1. **Create the repository on GitHub:**
   - Go to https://github.com/new
   - Repository name: `index-tts-fastapi`
   - Description: "FastAPI REST API wrapper for IndexTTS2 with OpenAI-compatible endpoints"
   - Choose Public or Private
   - Don't initialize with README (we already have one)

2. **Initialize git and push:**

```bash
cd /Users/nishant/apps/index-tts-fastapi

# Initialize git
git init

# Add all files
git add .

# Create initial commit
git commit -m "Initial commit: FastAPI wrapper for IndexTTS2"

# Add remote (replace YOUR_USERNAME with your GitHub username)
git remote add origin https://github.com/YOUR_USERNAME/index-tts-fastapi.git

# Push to GitHub
git branch -M main
git push -u origin main
```

## Repository Structure

```
index-tts-fastapi/
├── indextts_fastapi/          # Main package
│   ├── __init__.py
│   ├── api.py                 # FastAPI application
│   └── config.py              # Configuration management
├── examples/                   # Example scripts
│   └── basic_usage.py
├── .gitignore
├── LICENSE
├── pyproject.toml            # Package configuration
├── README.md                  # Main documentation
└── SETUP_GITHUB.md           # This file
```

## Next Steps

1. **Add GitHub Actions for CI/CD** (optional):
   - Create `.github/workflows/ci.yml` for automated testing
   - Add code quality checks

2. **Set up PyPI publishing** (optional):
   - Create GitHub Actions workflow for automatic PyPI releases
   - Add version tags

3. **Add badges to README:**
   ```markdown
   ![PyPI version](https://img.shields.io/pypi/v/indextts-fastapi)
   ![License](https://img.shields.io/github/license/YOUR_USERNAME/index-tts-fastapi)
   ```

4. **Create releases:**
   - Tag releases: `git tag v1.0.0`
   - Push tags: `git push origin v1.0.0`

## Publishing to PyPI (Optional)

1. **Build the package:**
   ```bash
   pip install build
   python -m build
   ```

2. **Upload to PyPI:**
   ```bash
   pip install twine
   twine upload dist/*
   ```

## Notes

- The package requires `indextts>=2.0.0` to be installed separately
- Users need to download IndexTTS2 models separately
- See README.md for installation instructions

