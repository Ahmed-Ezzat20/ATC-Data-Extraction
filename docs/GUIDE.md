# Complete Usage Guide

This guide provides detailed instructions for using the ATC Data Extraction pipeline.

## Table of Contents

1. [Installation](#installation)
2. [Quick Start](#quick-start)
3. [Detailed Usage](#detailed-usage)
4. [Configuration](#configuration)
5. [Troubleshooting](#troubleshooting)

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/Ahmed-Ezzat20/ATC-Data-Extraction.git
cd ATC-Data-Extraction
```

### 2. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 3. Install System Dependencies

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install -y ffmpeg
pip install yt-dlp
```

**macOS:**
```bash
brew install ffmpeg
pip install yt-dlp
```

**Windows:**
- Download ffmpeg from [ffmpeg.org](https://ffmpeg.org/download.html)
- Add to PATH
- Install yt-dlp: `pip install yt-dlp`

### 4. Set Up API Key

```bash
export GEMINI_API_KEY="your-api-key-here"
```

Or create a `.env` file:
```
GEMINI_API_KEY=your-api-key-here
```

## Quick Start

### Process a Playlist (Complete Pipeline)

```bash
python main.py --playlist-url "https://youtube.com/playlist?list=YOUR_PLAYLIST_ID"
```

This will:
1. Extract subtitles from all videos using Gemini API
2. Download audio files
3. Segment audio based on timestamps
4. Generate analysis reports and visualizations

### Process Specific Videos

```bash
python main.py --video-urls \
  "https://www.youtube.com/watch?v=VIDEO_ID_1" \
  "https://www.youtube.com/watch?v=VIDEO_ID_2"
```

## Detailed Usage

### Phase 1: Extract Subtitles

#### Single Video

```python
from src.extraction.gemini_extractor import GeminiExtractor

extractor = GeminiExtractor(api_key="YOUR_API_KEY")
result = extractor.extract_subtitles("https://www.youtube.com/watch?v=VIDEO_ID")

print(f"Video ID: {result['video_id']}")
print(f"Total segments: {result['total_segments']}")

for segment in result['segments']:
    print(f"{segment['timestamp_range']}: {segment['transcript']}")
```

#### Batch Processing

```python
video_urls = [
    "https://www.youtube.com/watch?v=VIDEO_ID_1",
    "https://www.youtube.com/watch?v=VIDEO_ID_2",
]

results = extractor.extract_batch(video_urls, delay=2.0)
```

#### Command Line

```bash
python src/extraction/extract_playlist.py \
  --playlist-url "PLAYLIST_URL" \
  --output-dir "data/transcripts" \
  --delay 2.0
```

### Phase 2: Audio Processing

#### Download and Segment

```python
from src.segmentation.audio_segmenter import AudioSegmenter

segmenter = AudioSegmenter(
    transcripts_dir="data/transcripts",
    raw_audio_dir="data/raw_audio",
    segments_dir="data/audio_segments"
)

# Process single video
result = segmenter.process_video("VIDEO_ID", download=True)

# Process all videos
results = segmenter.process_all(download=True)
```

#### Skip Download (Use Existing Audio)

```python
result = segmenter.process_video("VIDEO_ID", download=False)
```

### Phase 3: Analysis

#### Duration Analysis

```python
from src.analysis.analyzer import Analyzer

analyzer = Analyzer(transcripts_dir="data/transcripts")
duration_stats = analyzer.analyze_duration()

print(f"Total videos: {duration_stats['total_videos']}")
print(f"Total duration: {duration_stats['total_duration_hours']:.2f} hours")
print(f"Average segment: {duration_stats['average_segment_duration']:.2f} seconds")
```

#### Vocabulary Analysis

```python
vocab_stats = analyzer.analyze_vocabulary()

print(f"Total words: {vocab_stats['total_words']:,}")
print(f"Unique words: {vocab_stats['unique_words']:,}")
print(f"Vocabulary richness: {vocab_stats['vocabulary_richness']*100:.2f}%")

# Top 10 words
for word, count in vocab_stats['top_words'][:10]:
    print(f"{word}: {count}")
```

#### Generate Reports

```python
# Text report
analyzer.generate_report(output_file="data/analysis_report.txt")

# CSV files
analyzer.generate_csv(output_file="data/all_segments.csv", detailed=False)
analyzer.generate_csv(output_file="data/all_segments_detailed.csv", detailed=True)
```

#### Create Visualizations

```python
from src.analysis.visualizer import Visualizer

visualizer = Visualizer(output_dir="data/visualizations")
visualizer.create_all_visualizations()
```

## Configuration

### Custom Configuration File

Create `config.yaml`:

```yaml
gemini:
  api_key: ${GEMINI_API_KEY}
  model: "gemini-2.5-pro"
  request_delay: 2

audio:
  format: "wav"
  sample_rate: 44100
  channels: 2
  bit_depth: 16

paths:
  transcripts: "data/transcripts"
  raw_audio: "data/raw_audio"
  segments: "data/audio_segments"
  visualizations: "data/visualizations"
```

### Environment Variables

```bash
# Required
export GEMINI_API_KEY="your-api-key"

# Optional
export ATC_DATA_DIR="custom/data/path"
export ATC_DELAY="3.0"
```

## Advanced Usage

### Skip Specific Phases

```bash
# Skip extraction (use existing transcripts)
python main.py --skip-extraction --playlist-url "URL"

# Skip audio download (use existing audio files)
python main.py --skip-download --playlist-url "URL"

# Skip segmentation
python main.py --skip-segmentation --playlist-url "URL"

# Only run analysis
python main.py --skip-extraction --skip-segmentation --skip-analysis
```

### Custom Output Directory

```bash
python main.py --playlist-url "URL" --output-dir "custom/output/path"
```

### Adjust API Rate Limiting

```bash
# Increase delay for free tier
python main.py --playlist-url "URL" --delay 5.0

# Decrease delay for paid tier
python main.py --playlist-url "URL" --delay 1.0
```

## Output Structure

After running the pipeline, your output directory will contain:

```
data/
├── transcripts/
│   ├── VIDEO_ID_1.json
│   ├── VIDEO_ID_1_raw.txt
│   ├── VIDEO_ID_2.json
│   └── VIDEO_ID_2_raw.txt
├── raw_audio/
│   ├── VIDEO_ID_1.webm
│   └── VIDEO_ID_2.webm
├── audio_segments/
│   ├── VIDEO_ID_1_seg001.wav
│   ├── VIDEO_ID_1_seg002.wav
│   └── ...
├── visualizations/
│   ├── top_20_words.png
│   ├── aviation_terms.png
│   ├── duration_by_video.png
│   └── segments_by_video.png
├── all_segments.csv
├── all_segments_detailed.csv
└── analysis_report.txt
```

## Troubleshooting

### API Rate Limit Errors

**Problem:** `429 Too Many Requests` error

**Solution:**
```bash
# Increase delay between requests
python main.py --playlist-url "URL" --delay 5.0
```

### Audio Download Fails

**Problem:** `yt-dlp` fails to download video

**Solution:**
```bash
# Update yt-dlp
pip install --upgrade yt-dlp

# Check video availability
yt-dlp --simulate "VIDEO_URL"
```

### FFmpeg Errors

**Problem:** Audio segmentation fails

**Solution:**
```bash
# Verify ffmpeg installation
ffmpeg -version

# Check audio file
ffmpeg -i data/raw_audio/VIDEO_ID.webm 2>&1 | grep Duration
```

### Memory Issues

**Problem:** Out of memory with large playlists

**Solution:**
```bash
# Process in batches
python main.py --video-urls VIDEO_1 VIDEO_2 VIDEO_3
# Then process next batch
python main.py --video-urls VIDEO_4 VIDEO_5 VIDEO_6
```

### Import Errors

**Problem:** `ModuleNotFoundError`

**Solution:**
```bash
# Reinstall dependencies
pip install -r requirements.txt

# Run from project root
cd /path/to/ATC-Data-Extraction
python main.py ...
```

## Performance Tips

1. **Use Tier 1 API** for faster processing (2000 requests/min vs 15/min)
2. **Process in parallel** by running multiple instances on different video subsets
3. **Skip already-processed videos** - scripts automatically detect existing files
4. **Use SSD storage** for faster audio processing
5. **Increase delay** if hitting rate limits consistently

## Examples

See the `examples/` directory for complete working examples:

- `examples/process_sample.py` - Process a small sample
- `examples/batch_processing.py` - Process videos in batches
- `examples/custom_analysis.py` - Custom analysis scripts

## Support

For issues, questions, or contributions:
- GitHub Issues: https://github.com/Ahmed-Ezzat20/ATC-Data-Extraction/issues
- Documentation: https://github.com/Ahmed-Ezzat20/ATC-Data-Extraction/docs
