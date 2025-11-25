# Quick Start Guide - Enhanced Version

This guide shows how to use the enhanced ATC Data Extraction pipeline.

## Installation

1. **Install dependencies:**
```bash
pip install -r requirements.txt
```

2. **Set up your API key:**
```bash
# Option 1: Environment variable
export GEMINI_API_KEY="your-api-key-here"

# Option 2: Create .env file
echo "GEMINI_API_KEY=your-api-key-here" > .env
```

3. **Verify configuration:**
```bash
# Config file already created at project root
cat config.yaml
```

## Basic Usage

### Simple Extraction (Auto-retry, Logging, Validation)

```python
from src.extraction import GeminiExtractor
from src.utils import setup_logger

# Setup logging
logger = setup_logger("my_extraction", log_file="logs/extraction.log")

# Initialize with automatic retry
extractor = GeminiExtractor(max_retries=3)

# Extract (automatically validates URL, retries on failure)
result = extractor.extract_subtitles("https://www.youtube.com/watch?v=VIDEO_ID")

print(f"Extracted {result['total_segments']} segments")
```

### Using Configuration File

```python
from src.utils import Config
from src.extraction import GeminiExtractor

# Load config from config.yaml
config = Config.from_yaml("config.yaml")

# Use configuration
extractor = GeminiExtractor(
    api_key=config.gemini.api_key,
    model=config.gemini.model,
    max_retries=config.gemini.max_retries
)

results = extractor.extract_batch(
    video_urls,
    delay=config.gemini.request_delay,
    output_dir=config.paths.transcripts
)
```

### Using Checkpoints (Resume on Interrupt)

```python
from src.utils import Checkpoint, ExtractionProgress
from src.extraction import GeminiExtractor

# Setup checkpoint
checkpoint = Checkpoint("data/checkpoints")
progress = ExtractionProgress(checkpoint, "my_session")

# Set total
progress.set_total(len(video_urls))

# Process videos
extractor = GeminiExtractor()
for url in video_urls:
    video_id = extractor.extract_video_id(url)

    # Skip if already done
    if progress.is_processed(video_id):
        continue

    try:
        result = extractor.extract_subtitles(url)
        progress.mark_processed(video_id)
    except Exception as e:
        progress.mark_failed(video_id)

# Check progress
stats = progress.get_stats()
print(f"Processed: {stats['processed']}/{stats['total']}")
```

## Command Line Usage

### Run Complete Pipeline

```bash
python main.py --playlist-url "PLAYLIST_URL"
```

### With Custom Configuration

```bash
python main.py --playlist-url "PLAYLIST_URL" \
  --delay 3.0 \
  --output-dir "output"
```

### Run Enhanced Example

```bash
python examples/enhanced_example.py
```

## Configuration Options

Edit `config.yaml` to customize:

```yaml
gemini:
  api_key: ${GEMINI_API_KEY}     # From environment
  model: gemini-2.5-pro           # Model to use
  request_delay: 2.0              # Seconds between requests
  max_retries: 3                  # Retry attempts
  retry_delay: 1.0                # Initial retry delay

audio:
  format: wav                     # Output format
  sample_rate: 44100              # Sample rate in Hz
  channels: 2                     # Stereo
  bit_depth: 16                   # Bit depth

paths:
  transcripts: data/transcripts
  raw_audio: data/raw_audio
  segments: data/audio_segments
  visualizations: data/visualizations
  logs: logs
  checkpoints: data/checkpoints
```

## Features Overview

### ✅ Automatic Validation
- YouTube URLs validated before processing
- API keys checked for correct format
- Timestamps validated (end > start)
- Clear error messages

### ✅ Automatic Retry
- API calls automatically retry on failure
- Exponential backoff (1s → 2s → 4s → 8s)
- Configurable retry attempts
- Logged retry attempts

### ✅ Progress Tracking
- Checkpoint files saved automatically
- Resume interrupted operations
- Track processed and failed videos
- Progress statistics

### ✅ Comprehensive Logging
- Console and file logging
- Multiple log levels (DEBUG, INFO, WARNING, ERROR)
- Timestamped entries
- Detailed error traces

### ✅ Configuration Management
- YAML-based configuration
- Environment variable support
- Type-safe settings
- Default fallbacks

## Troubleshooting

### "Invalid API key format"
- Check that `GEMINI_API_KEY` is set correctly
- API key should be 20+ alphanumeric characters

### "Invalid YouTube URL"
- URL must be in format: `https://www.youtube.com/watch?v=VIDEO_ID`
- Or: `https://youtu.be/VIDEO_ID`

### Resume from Checkpoint
```python
from src.utils import Checkpoint

# List checkpoints
checkpoint = Checkpoint()
print(checkpoint.list_checkpoints())

# Load specific checkpoint
data = checkpoint.load("my_session")
print(data)
```

### View Logs
```bash
# Real-time log viewing
tail -f logs/extraction.log

# Search for errors
grep "ERROR" logs/extraction.log
```

## API Rate Limits

The enhanced version automatically handles rate limits:

**Free Tier:**
- 15 requests/minute
- 1,500 requests/day
- Set `request_delay: 4.0` in config

**Tier 1:**
- 2,000 requests/minute
- Unlimited daily
- Set `request_delay: 0.5` in config

## Common Workflows

### 1. Process Playlist with Checkpoints

```bash
# Start processing
python main.py --playlist-url "PLAYLIST_URL"

# If interrupted (Ctrl+C), just run again
python main.py --playlist-url "PLAYLIST_URL"
# It will resume where it left off!
```

### 2. Process with Custom Logging

```python
from src.utils import setup_logger, Config
from src.extraction import GeminiExtractor

# Setup verbose logging
logger = setup_logger(
    "my_extraction",
    level=10,  # DEBUG level
    log_file="logs/detailed.log"
)

config = Config.from_yaml("config.yaml")
extractor = GeminiExtractor(api_key=config.gemini.api_key)

# All operations will be logged in detail
results = extractor.extract_batch(video_urls)
```

### 3. Validate Before Processing

```python
from src.utils import (
    validate_youtube_url,
    validate_playlist_url,
    validate_api_key,
    ValidationError
)

# Validate all inputs first
video_urls = ["url1", "url2", "url3"]
valid_urls = []

for url in video_urls:
    if validate_youtube_url(url):
        valid_urls.append(url)
    else:
        print(f"Skipping invalid URL: {url}")

# Process only valid URLs
extractor = GeminiExtractor()
results = extractor.extract_batch(valid_urls)
```

## Getting Help

- Check `ENHANCEMENTS.md` for detailed feature documentation
- View logs in `logs/` directory
- Run examples in `examples/` directory
- Check GitHub issues for known problems

## Next Steps

1. Try `python examples/enhanced_example.py`
2. Customize `config.yaml` for your needs
3. Run your first extraction with automatic retry and logging
4. Check logs to see detailed progress

Happy extracting! 🎉
