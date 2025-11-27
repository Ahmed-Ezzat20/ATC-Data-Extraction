# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ATC-Data-Extraction is a pipeline for extracting, processing, and analyzing Air Traffic Control (ATC) communications from YouTube videos. The pipeline extracts on-screen subtitles using Google's Gemini 2.5 Pro API, segments audio files, and performs vocabulary/duration analysis.

## Architecture

### Pipeline Phases

The system operates as a multi-phase pipeline, each phase processing data from the previous:

1. **Extraction Phase** (`src/extraction/`): Uses Gemini API to extract on-screen subtitles from YouTube videos
   - `gemini_extractor.py`: Core extraction logic with retry mechanisms and validation
   - `extract_playlist.py`: Playlist video enumeration using yt-dlp
   - Output: JSON transcripts in `data/transcripts/`

2. **Segmentation Phase** (`src/segmentation/`): Downloads and segments audio based on extracted timestamps
   - `audio_segmenter.py`: Downloads audio with yt-dlp and segments with ffmpeg
   - Output: Raw audio in `data/raw_audio/`, segments in `data/audio_segments/`

3. **Analysis Phase** (`src/analysis/`): Analyzes transcripts for vocabulary and duration statistics
   - `analyzer.py`: Statistical analysis of transcripts
   - `visualizer.py`: Chart generation using matplotlib/seaborn
   - Output: Reports, CSVs, and visualizations in `data/`

4. **Preprocessing Phase** (`src/preprocessing/`): Normalizes and filters transcripts for ATC compliance
   - `normalizer.py`: Text normalization (phonetic expansion, number conversion, spelling)
   - `filters.py`: Transmission filtering (tag-based, quality-based, manual exclusions)
   - Output: Preprocessed data in `data/preprocessed/`

### Core Components

**Utilities** (`src/utils/`):
- `logger.py`: Centralized logging configuration
- `validation.py`: Input validation (YouTube URLs, API keys, timestamps)
- `retry.py`: Exponential backoff decorator for API calls
- `checkpoint.py`: Checkpoint/resume functionality
- `config.py`: Configuration management

**Preprocessing** (`src/preprocessing/`):
- `normalizer.py`: ATC text normalization with NATO phonetic alphabet, number expansion
- `filters.py`: Transmission filtering based on tags, quality, and manual rules

**Data Flow**:
```
YouTube Videos → Gemini API → JSON Transcripts → Audio Download →
FFmpeg Segmentation → CSV/Analysis → Visualizations → [Optional] Preprocessing
```

### Key Design Patterns

- **Batch Processing with Checkpoints**: All extractors support batch operations with skip-if-exists logic
- **Retry with Exponential Backoff**: API calls use `@exponential_backoff` decorator
- **Validation First**: All inputs validated before processing (see `utils/validation.py`)
- **Structured Logging**: Consistent logging via `utils.logger.get_logger()`

## Development Commands

### Environment Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Required environment variable
export GEMINI_API_KEY="your-api-key-here"
```

### Running the Pipeline

**Full Pipeline**:
```bash
python main.py --playlist-url "PLAYLIST_URL"
```

**Individual Phases**:
```bash
# Extract subtitles only
python src/extraction/extract_playlist.py --playlist-url "URL" --output-dir data/transcripts

# Segment audio only (requires existing transcripts)
python main.py --skip-extraction --playlist-url "URL"

# Analysis only (requires existing transcripts)
python main.py --skip-extraction --skip-segmentation --playlist-url "URL"
```

**Common Options**:
- `--skip-extraction`: Skip subtitle extraction (use existing transcripts)
- `--skip-download`: Skip audio download (use existing audio)
- `--skip-segmentation`: Skip audio segmentation
- `--skip-analysis`: Skip analysis and visualization
- `--delay 2.0`: Delay between API requests (default: 2.0s)
- `--output-dir data`: Base output directory (default: data)

### Data Validation

```bash
# Validate data synchronization across all phases
python validate_data.py --data-dir data
```

This checks:
- Transcript JSON validity
- Audio segments match transcripts
- CSV outputs match transcript data
- Analysis reports present and consistent

### Data Preprocessing

```bash
# Preprocess all transcripts with full normalization and filtering
python preprocess_data.py --data-dir data --output-dir data/preprocessed

# Test preprocessing functions
python examples/test_preprocessing.py

# Custom preprocessing options
python preprocess_data.py --data-dir data \
    --no-phonetic-expansion \
    --min-length 5 \
    --manual-exclusions config/manual_exclusions.txt
```

**Preprocessing Features**:
- Spelling corrections (e.g., "RODGER" → "ROGER")
- Diacritic normalization (e.g., "café" → "CAFE")
- Letter-to-phonetic (e.g., "N 1 2 3" → "NOVEMBER ONE TWO THREE")
- Number-to-word (e.g., "350" → "THREE FIVE ZERO", "118.3" → "ONE ONE EIGHT DECIMAL THREE")
- Uppercase normalization
- Tag removal (e.g., [GROUND], [AIR])
- Transmission filtering (excludes [NO_ENG], [UNINTELLIGIBLE], etc.)

**Preprocessing Options**:
- `--no-spelling-corrections`: Disable spelling corrections
- `--no-diacritics`: Disable diacritic normalization
- `--no-phonetic-expansion`: Disable letter-to-phonetic conversion
- `--no-number-expansion`: Disable number-to-word conversion
- `--no-uppercase`: Disable uppercase conversion
- `--no-tag-removal`: Disable tag removal
- `--no-filtering`: Disable transmission filtering
- `--min-length N`: Minimum text length in words (default: 3)
- `--max-length N`: Maximum text length in words
- `--manual-exclusions FILE`: Path to manual exclusions file

### Data Upload

```bash
# Upload dataset to Hugging Face (CSV and transcripts only, no audio)
python upload_to_huggingface_no_audio.py --repo-id "username/dataset-name"

# For private repository
python upload_to_huggingface_no_audio.py --repo-id "username/dataset-name" --private
```

Requires: `huggingface-cli login` first

## Data Structures

### Transcript JSON Format
```json
{
  "video_id": "VIDEO_ID",
  "video_url": "https://www.youtube.com/watch?v=VIDEO_ID",
  "total_segments": 10,
  "segments": [
    {
      "segment_num": 1,
      "start_time": 5,
      "end_time": 11,
      "duration": 6,
      "timestamp_range": "[00:05 - 00:11]",
      "transcript": "CLEARED FOR TAKEOFF RUNWAY 27"
    }
  ]
}
```

### Segment Naming Convention
Audio files: `{video_id}_seg{segment_num:03d}.wav`
Example: `94VPOXc2bEM_seg001.wav`

### CSV Outputs
- `all_segments.csv`: Basic format (audio_filename, transcription)
- `all_segments_detailed.csv`: Includes video_id, segment_num, start_time, duration, timestamp_range

### Preprocessed Output Structure
After preprocessing, output in `data/preprocessed/`:
- `transcripts/`: Preprocessed JSON files with `original_transcript` preserved
- `all_segments.csv`: Preprocessed transcriptions
- `all_segments_detailed.csv`: Includes both preprocessed and original transcriptions
- `preprocessing_report.txt`: Statistics and configuration used

## Important Configuration Details

### Uppercase Transcripts
By default, `GeminiExtractor` converts all transcripts to uppercase (`uppercase_transcripts=True`). This matches ATC communication conventions. To disable, pass `uppercase_transcripts=False` when initializing.

### Preprocessing Normalization
The `ATCTextNormalizer` applies transformations in this order:
1. Uppercase conversion
2. Diacritic removal
3. Non-critical tag removal
4. Phonetic letter expansion (NATO alphabet)
5. Number-to-word expansion (digit-by-digit)
6. Spelling corrections
7. Whitespace cleanup

**Important**: Phonetic expansion only applies to single-letter words (e.g., "N" but not "NOVEMBER"). Runway designators like "27L" are handled specially: "27L" → "TWO SEVEN LEFT".

### Transmission Filtering
The `TransmissionFilter` excludes transmissions containing:
- Language tags: [NO_ENG], [CZECH_], [FRENCH_], etc.
- Quality tags: [UNINTELLIGIBLE], [CROSSTALK], [NOISE], [STATIC]
- Uncertainty markers: [?], (?), <UNK>
- Length constraints: Configurable min/max word counts
- Manual exclusions: Custom exclusion list in `config/manual_exclusions.txt`

### External Dependencies
- **yt-dlp**: YouTube video/audio download. Commands run via subprocess.
- **ffmpeg**: Audio segmentation. Must be installed and in PATH.
- **Gemini API**: Requires valid `GEMINI_API_KEY` environment variable.

### File Organization
Raw API responses saved as `{video_id}_raw.txt` alongside JSON transcripts for debugging. These are excluded from batch processing (files ending with `_raw`).

## Error Handling

- **ValidationError**: Input validation failures (invalid URLs, API keys, timestamps)
- **RetryableError**: Operations that should be retried with backoff
- **NonRetryableError**: Operations that should fail immediately

All extractor methods use `@exponential_backoff` decorator with:
- Default: 3 retries, 2s initial delay, 2x backoff factor
- Rate limiting: 5 retries, 5s initial delay

## Testing Strategy

When modifying extraction logic:
1. Test with single video first: `extractor.extract_subtitles(video_url)`
2. Check raw output in `data/transcripts/{video_id}_raw.txt`
3. Verify JSON structure matches expected format
4. Run validation: `python validate_data.py`

When modifying segmentation:
1. Ensure ffmpeg is available: `ffmpeg -version`
2. Test with one video's JSON transcript
3. Check segment file naming convention
4. Validate audio file size/duration matches expected

## Notes

- All paths use `pathlib.Path` for cross-platform compatibility
- Transcripts directory scans exclude `_raw.json` files
- Batch operations skip existing outputs (idempotent)
- Delay between API requests prevents rate limiting (default 2s, configurable)
- Visualizations use `seaborn-v0_8-darkgrid` style
