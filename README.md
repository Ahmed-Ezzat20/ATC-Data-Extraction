# ATC Data Extraction

Automated extraction and analysis of Air Traffic Control (ATC) communications from YouTube videos using Google Gemini API.

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

## Overview

This project provides a complete pipeline for extracting on-screen subtitles from ATC YouTube videos, segmenting audio based on timestamps, and performing comprehensive vocabulary and duration analysis.

### Key Features

- 🎥 **YouTube Playlist Support** - Process entire playlists automatically
- 🤖 **Gemini API Integration** - Extract on-screen text with high accuracy using Google's Gemini 2.5 Pro
- 🎵 **Audio Segmentation** - Automatically segment audio based on extracted timestamps
- 📊 **Comprehensive Analysis** - Duration statistics, vocabulary analysis, and visualizations
- 🔄 **Resume Capability** - All scripts can resume from interruptions
- 📈 **Detailed Reporting** - Generate CSV files and analysis reports

## Architecture

```
┌─────────────────┐
│  YouTube Video  │
└────────┬────────┘
         │
         ▼
┌─────────────────────────┐
│  Gemini 2.5 Pro API     │
│  (Extract Subtitles)    │
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│  Timestamp Extraction   │
│  [MM:SS - MM:SS]        │
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│  Audio Download         │
│  (yt-dlp)               │
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│  Audio Segmentation     │
│  (ffmpeg)               │
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│  Analysis & Reports     │
│  (CSV, Visualizations)  │
└─────────────────────────┘
```

## Installation

### Prerequisites

- Python 3.11+
- ffmpeg
- yt-dlp

### Setup

1. **Clone the repository**
```bash
git clone https://github.com/Ahmed-Ezzat20/ATC-Data-Extraction.git
cd ATC-Data-Extraction
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Install system dependencies**
```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y ffmpeg

# macOS
brew install ffmpeg

# Install yt-dlp
pip install yt-dlp
```

4. **Set up API key**
```bash
export GEMINI_API_KEY="your-api-key-here"
```

## Quick Start

### Process a Single Video

```bash
python src/extraction/extract_video.py --url "https://www.youtube.com/watch?v=VIDEO_ID"
```

### Process a Playlist

```bash
python src/extraction/extract_playlist.py --playlist-url "PLAYLIST_URL"
```

### Complete Pipeline

```bash
# 1. Extract subtitles
python src/extraction/extract_playlist.py --playlist-url "PLAYLIST_URL"

# 2. Download audio
python src/segmentation/download_audio.py

# 3. Segment audio
python src/segmentation/segment_audio.py

# 4. Analyze results
python src/analysis/analyze.py
```

## Usage

### 1. Extract Subtitles from Videos

```python
from src.extraction.gemini_extractor import GeminiExtractor

extractor = GeminiExtractor(api_key="YOUR_API_KEY")
result = extractor.extract_subtitles("https://www.youtube.com/watch?v=VIDEO_ID")

print(f"Extracted {result['total_segments']} segments")
```

### 2. Segment Audio

```python
from src.segmentation.audio_segmenter import AudioSegmenter

segmenter = AudioSegmenter()
segmenter.segment_video(
    video_id="VIDEO_ID",
    transcript_file="data/transcripts/VIDEO_ID.json",
    audio_file="data/raw_audio/VIDEO_ID.webm"
)
```

### 3. Analyze Data

```python
from src.analysis.analyzer import Analyzer

analyzer = Analyzer()
results = analyzer.analyze_all()

print(f"Total duration: {results['total_duration']/60:.1f} minutes")
print(f"Total words: {results['total_words']:,}")
print(f"Unique words: {results['unique_words']:,}")
```

## Project Structure

```
ATC-Data-Extraction/
├── src/
│   ├── extraction/          # Gemini API extraction logic
│   │   ├── gemini_extractor.py
│   │   ├── extract_video.py
│   │   └── extract_playlist.py
│   ├── segmentation/        # Audio processing
│   │   ├── audio_segmenter.py
│   │   ├── download_audio.py
│   │   └── segment_audio.py
│   └── analysis/            # Data analysis and visualization
│       ├── analyzer.py
│       ├── visualizer.py
│       └── report_generator.py
├── data/                    # Data storage (gitignored)
│   ├── transcripts/         # JSON files with extracted subtitles
│   ├── raw_audio/           # Downloaded audio files
│   └── audio_segments/      # Segmented WAV files
├── docs/                    # Documentation
│   ├── API.md
│   ├── GUIDE.md
│   └── EXAMPLES.md
├── examples/                # Example scripts
│   └── process_sample.py
├── tests/                   # Unit tests
│   └── test_extraction.py
├── requirements.txt         # Python dependencies
├── .gitignore
├── LICENSE
└── README.md
```

## Output Format

### Transcript JSON Structure

```json
{
  "video_id": "VIDEO_ID",
  "video_url": "https://www.youtube.com/watch?v=VIDEO_ID",
  "total_segments": 50,
  "segments": [
    {
      "segment_num": 1,
      "start_time": 5,
      "end_time": 11,
      "duration": 6,
      "timestamp_range": "[00:05 - 00:11]",
      "transcript": "Emirates 521, Dubai Tower, good afternoon!"
    }
  ]
}
```

### CSV Output

**all_segments.csv**
```csv
audio_filename,transcription
VIDEO_ID_seg001.wav,"Emirates 521, Dubai Tower, good afternoon!"
VIDEO_ID_seg002.wav,"Tower, hello, Emirates 521"
```

**all_segments_detailed.csv**
```csv
audio_filename,transcription,video_id,segment_num,start_time,duration,timestamp_range
VIDEO_ID_seg001.wav,"Emirates 521...",VIDEO_ID,1,5,6,"[00:05 - 00:11]"
```

## Analysis Features

### Duration Analysis
- Total duration across all videos
- Average segment duration
- Duration distribution by video

### Vocabulary Analysis
- Total word count
- Unique word count
- Vocabulary richness
- Top N most common words
- Aviation-specific terminology frequency
- Flight callsign extraction

### Visualizations
- Top 20 most common words (bar chart)
- Aviation terminology frequency (bar chart)
- Duration by video (bar chart)
- Segments by video (bar chart)
- Word length distribution (histogram)

## Configuration

Create a `config.yaml` file:

```yaml
gemini:
  api_key: ${GEMINI_API_KEY}
  model: "gemini-2.5-pro"
  request_delay: 2  # seconds between requests

audio:
  format: "wav"
  sample_rate: 44100
  channels: 2
  bit_depth: 16

output:
  transcripts_dir: "data/transcripts"
  raw_audio_dir: "data/raw_audio"
  segments_dir: "data/audio_segments"
```

## Performance

### Processing Times (Estimated)

| Task | Duration (per video) | Notes |
|------|---------------------|-------|
| Subtitle Extraction | 20-30s | Gemini API processing |
| Audio Download | 10-30s | Depends on video length |
| Audio Segmentation | 5-10s | Depends on segment count |

**For 250 videos:**
- Extraction: ~90 minutes
- Audio Download: ~60 minutes
- Segmentation: ~40 minutes
- **Total: ~3 hours**

## API Rate Limits

### Gemini API (Free Tier)
- 15 requests per minute
- 1,500 requests per day
- 1 million tokens per minute

### Gemini API (Tier 1)
- 2,000 requests per minute
- No daily limit
- 4 million tokens per minute

## Troubleshooting

### Common Issues

**1. API Rate Limit Errors**
```bash
# Solution: Increase delay between requests
# Edit config.yaml: request_delay: 5
```

**2. Audio Download Fails**
```bash
# Check video availability
yt-dlp --simulate <video_url>
```

**3. FFmpeg Segmentation Errors**
```bash
# Verify audio file
ffmpeg -i <audio_file> 2>&1 | grep Duration
```

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Google Gemini API for subtitle extraction
- yt-dlp for YouTube video/audio downloading
- FFmpeg for audio processing

## Citation

If you use this project in your research, please cite:

```bibtex
@software{atc_data_extraction,
  author = {Ahmed Ezzat},
  title = {ATC Data Extraction},
  year = {2025},
  url = {https://github.com/Ahmed-Ezzat20/ATC-Data-Extraction}
}
```

## Contact

Ahmed Ezzat - [@Ahmed-Ezzat20](https://github.com/Ahmed-Ezzat20)

Project Link: [https://github.com/Ahmed-Ezzat20/ATC-Data-Extraction](https://github.com/Ahmed-Ezzat20/ATC-Data-Extraction)
