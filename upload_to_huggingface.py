#!/usr/bin/env python3
"""
Upload ATC Dataset to Hugging Face Hub

Uploads audio segments and CSV files to create a Hugging Face dataset.

Prerequisites:
    pip install huggingface_hub datasets

Usage:
    python upload_to_huggingface.py --repo-id "username/dataset-name" [options]
"""

import argparse
import sys
from pathlib import Path
from huggingface_hub import HfApi, create_repo, upload_folder, upload_file
from huggingface_hub.utils import HfHubHTTPError


def check_authentication():
    """
    Check if user is authenticated with Hugging Face.

    Returns:
        True if authenticated, False otherwise
    """
    try:
        api = HfApi()
        api.whoami()
        return True
    except Exception:
        return False


def create_dataset_card(data_dir, output_file='README.md'):
    """
    Create a dataset card (README.md) for Hugging Face.

    Args:
        data_dir: Data directory path
        output_file: Output file path
    """
    import json

    data_path = Path(data_dir)

    # Gather statistics
    transcript_files = list((data_path / 'transcripts').glob('*.json'))
    transcript_files = [f for f in transcript_files if not f.stem.endswith('_raw')]

    audio_files = list((data_path / 'audio_segments').glob('*.wav'))

    # Load analysis report if exists
    report_path = data_path / 'analysis_report.txt'
    report_content = ""
    if report_path.exists():
        with open(report_path, 'r', encoding='utf-8') as f:
            report_content = f.read()

    # Count total duration and words from transcripts
    total_duration = 0
    total_words = 0

    for json_file in transcript_files[:100]:  # Sample first 100 for speed
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            for seg in data['segments']:
                total_duration += seg['duration']
                total_words += len(seg['transcript'].split())

    # Estimate totals
    if transcript_files:
        avg_duration_per_file = total_duration / min(100, len(transcript_files))
        avg_words_per_file = total_words / min(100, len(transcript_files))
        estimated_duration = avg_duration_per_file * len(transcript_files)
        estimated_words = avg_words_per_file * len(transcript_files)
    else:
        estimated_duration = 0
        estimated_words = 0

    card_content = f"""---
license: cc-by-4.0
task_categories:
- automatic-speech-recognition
- audio-classification
language:
- en
tags:
- aviation
- atc
- air-traffic-control
- speech
- audio
size_categories:
- 10K<n<100K
---

# ATC (Air Traffic Control) Communications Dataset

## Dataset Description

This dataset contains audio segments of Air Traffic Control (ATC) communications extracted from YouTube videos, with corresponding transcriptions.

### Dataset Summary

- **Total Audio Segments**: {len(audio_files):,}
- **Total Videos**: {len(transcript_files)}
- **Estimated Duration**: ~{estimated_duration/60:.1f} minutes (~{estimated_duration/3600:.1f} hours)
- **Estimated Words**: ~{estimated_words:,}
- **Audio Format**: WAV (PCM 16-bit, 44.1kHz, Stereo)
- **Language**: English (Aviation/ATC terminology)

### Supported Tasks

- **Automatic Speech Recognition (ASR)**: Train models to transcribe ATC communications
- **Audio Classification**: Identify types of ATC communications
- **Keyword Spotting**: Detect aviation-specific terms and callsigns
- **Speaker Diarization**: Distinguish between pilots and controllers

## Dataset Structure

### Data Files

The dataset consists of:
- **Audio files**: `audio_segments/*.wav` - Segmented audio clips
- **Transcript files**: `transcripts/*.json` - Full transcript data per video
- **Transcriptions**: `all_segments.csv` - Basic audio-transcription pairs
- **Detailed metadata**: `all_segments_detailed.csv` - Includes timing and video information

### CSV Format

**all_segments.csv**:
```csv
audio_filename,transcription
video_id_seg001.wav,"American 123 contact tower 118.3"
```

**all_segments_detailed.csv**:
```csv
audio_filename,transcription,video_id,segment_num,start_time,duration,timestamp_range
video_id_seg001.wav,"American 123 contact tower 118.3",video_id,1,0.0,3.5,"0:00:00.0 - 0:00:03.5"
```

### Transcript JSON Format

Each video has a JSON file in `transcripts/` with this structure:
```json
{
  "video_id": "VIDEO_ID",
  "video_url": "https://www.youtube.com/watch?v=VIDEO_ID",
  "segments": [
    {
      "segment_num": 1,
      "start_time": 0.0,
      "duration": 3.5,
      "transcript": "American 123 contact tower 118.3",
      "timestamp_range": "0:00:00.0 - 0:00:03.5"
    }
  ]
}
```

### Data Fields

- `audio_filename`: Name of the audio file
- `transcription`: Text transcription of the audio
- `video_id`: YouTube video ID (source)
- `segment_num`: Segment number within the video
- `start_time`: Start time in seconds (within source video)
- `duration`: Duration of the segment in seconds
- `timestamp_range`: Human-readable timestamp range

## Dataset Creation

### Source Data

Audio extracted from publicly available YouTube videos containing ATC communications.

### Extraction Process

1. Subtitle extraction from YouTube videos
2. Audio download and segmentation based on subtitle timestamps
3. Quality control and validation
4. Metadata aggregation

### Annotations

Transcriptions are sourced from YouTube's automatic captions and/or manual subtitles.
Accuracy may vary depending on audio quality and source.

## Considerations

### Aviation Terminology

This dataset contains specialized aviation terminology including:
- Radio callsigns (airline flight numbers, tail numbers)
- Airport codes (ICAO/IATA identifiers)
- Altitude, heading, and speed instructions
- Standard phraseology (cleared, roger, wilco, etc.)

### Audio Quality

Audio quality varies depending on:
- Original recording quality
- Radio transmission clarity
- Background noise levels

### Ethical Considerations

- All data is from publicly available sources
- Contains real ATC communications (publicly broadcast)
- May include sensitive flight information
- Intended for research and educational purposes

## Usage

### Loading with Hugging Face Datasets

```python
from datasets import load_dataset

# Load the dataset
dataset = load_dataset("YOUR_USERNAME/YOUR_DATASET_NAME")

# Access audio and transcription
for example in dataset['train']:
    audio = example['audio']
    transcription = example['transcription']
    print(f"Transcription: {{transcription}}")
```

### Loading with Pandas

```python
import pandas as pd

# Load CSV
df = pd.read_csv('all_segments.csv')

# Access transcriptions
print(df[['audio_filename', 'transcription']].head())
```

## Citation

If you use this dataset, please cite:

```bibtex
@dataset{{atc_communications,
  title={{ATC Communications Dataset}},
  author={{Your Name}},
  year={{2024}},
  publisher={{Hugging Face}},
  url={{https://huggingface.co/datasets/YOUR_USERNAME/YOUR_DATASET_NAME}}
}}
```

## License

This dataset is released under CC-BY-4.0 license.

## Contact

For questions or issues, please open an issue on the dataset repository.

---

**Note**: This dataset is intended for research and educational purposes.
Users should be aware of and comply with relevant regulations regarding aviation communications.
"""

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(card_content)

    print(f"[OK] Dataset card created: {output_file}")
    return output_file


def upload_dataset(repo_id, data_dir='data', private=False, create_if_not_exists=True):
    """
    Upload dataset to Hugging Face Hub.

    Args:
        repo_id: Repository ID (username/dataset-name)
        data_dir: Data directory path
        private: Whether to create a private repository
        create_if_not_exists: Create repo if it doesn't exist

    Returns:
        True if successful
    """
    api = HfApi()
    data_path = Path(data_dir)

    print("=" * 70)
    print("UPLOADING TO HUGGING FACE")
    print("=" * 70)
    print(f"\nRepository: {repo_id}")
    print(f"Data directory: {data_path.absolute()}")
    print(f"Private: {private}")

    # Check if repo exists or create it
    try:
        api.repo_info(repo_id=repo_id, repo_type="dataset")
        print(f"\n[OK] Repository exists: {repo_id}")
    except HfHubHTTPError:
        if create_if_not_exists:
            print(f"\n[!] Repository doesn't exist, creating: {repo_id}")
            create_repo(
                repo_id=repo_id,
                repo_type="dataset",
                private=private,
                exist_ok=True
            )
            print(f"[OK] Repository created")
        else:
            print(f"\n[X] Repository doesn't exist: {repo_id}")
            print("    Use --create-repo to create it automatically")
            return False

    # Create dataset card
    print("\n" + "-" * 70)
    print("Creating dataset card...")
    readme_path = create_dataset_card(data_dir, 'README.md')

    # Upload README
    print("\nUploading README.md...")
    api.upload_file(
        path_or_fileobj=readme_path,
        path_in_repo="README.md",
        repo_id=repo_id,
        repo_type="dataset"
    )
    print("[OK] README.md uploaded")

    # Upload CSV files
    print("\n" + "-" * 70)
    print("Uploading CSV files...")

    csv_files = [
        'all_segments.csv',
        'all_segments_detailed.csv'
    ]

    for csv_file in csv_files:
        csv_path = data_path / csv_file
        if csv_path.exists():
            print(f"  Uploading {csv_file}...")
            api.upload_file(
                path_or_fileobj=str(csv_path),
                path_in_repo=csv_file,
                repo_id=repo_id,
                repo_type="dataset"
            )
            print(f"  [OK] {csv_file} uploaded")
        else:
            print(f"  [!] {csv_file} not found, skipping")

    # Upload audio segments folder
    print("\n" + "-" * 70)
    print("Uploading audio segments...")
    print("This may take a while depending on the number and size of files...")

    audio_segments_dir = data_path / 'audio_segments'
    if audio_segments_dir.exists():
        audio_files = list(audio_segments_dir.glob('*.wav'))
        print(f"Found {len(audio_files)} audio files")

        # Upload folder
        api.upload_folder(
            folder_path=str(audio_segments_dir),
            path_in_repo="audio_segments",
            repo_id=repo_id,
            repo_type="dataset"
        )
        print(f"[OK] Audio segments uploaded")
    else:
        print("[X] audio_segments directory not found")
        return False

    # Upload transcript JSON files
    print("\n" + "-" * 70)
    print("Uploading transcript files...")

    transcripts_dir = data_path / 'transcripts'
    if transcripts_dir.exists():
        # Filter out raw files
        transcript_files = [f for f in transcripts_dir.glob('*.json')
                          if not f.stem.endswith('_raw')]
        print(f"Found {len(transcript_files)} transcript files")

        # Upload transcripts folder
        api.upload_folder(
            folder_path=str(transcripts_dir),
            path_in_repo="transcripts",
            repo_id=repo_id,
            repo_type="dataset",
            allow_patterns="*.json",
            ignore_patterns="*_raw.json"
        )
        print(f"[OK] Transcript files uploaded")
    else:
        print("[!] transcripts directory not found, skipping")

    # Upload analysis report (optional)
    report_path = data_path / 'analysis_report.txt'
    if report_path.exists():
        print("\nUploading analysis report...")
        api.upload_file(
            path_or_fileobj=str(report_path),
            path_in_repo="analysis_report.txt",
            repo_id=repo_id,
            repo_type="dataset"
        )
        print("[OK] analysis_report.txt uploaded")

    print("\n" + "=" * 70)
    print("UPLOAD COMPLETE")
    print("=" * 70)
    print(f"\nDataset URL: https://huggingface.co/datasets/{repo_id}")
    print("\nYou can now:")
    print("1. View your dataset on Hugging Face")
    print("2. Share it with others")
    print("3. Load it with: load_dataset('{}')".format(repo_id))

    return True


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Upload ATC dataset to Hugging Face Hub"
    )
    parser.add_argument(
        '--repo-id',
        required=True,
        help='Repository ID (username/dataset-name)'
    )
    parser.add_argument(
        '--data-dir',
        default='data',
        help='Data directory (default: data)'
    )
    parser.add_argument(
        '--private',
        action='store_true',
        help='Create a private repository'
    )
    parser.add_argument(
        '--no-create',
        action='store_true',
        help='Do not create repository if it doesn\'t exist'
    )

    args = parser.parse_args()

    # Check authentication
    print("Checking Hugging Face authentication...")
    if not check_authentication():
        print("\n[X] Not authenticated with Hugging Face")
        print("\nPlease login first:")
        print("  huggingface-cli login")
        print("\nOr set your token:")
        print("  export HF_TOKEN=your_token_here")
        return 1

    print("[OK] Authenticated")

    # Confirm
    print("\n" + "=" * 70)
    print(f"Ready to upload to: {args.repo_id}")
    print(f"Data directory: {args.data_dir}")
    print(f"Private: {args.private}")
    print("=" * 70)

    response = input("\nProceed with upload? (yes/no): ").strip().lower()
    if response not in ['yes', 'y']:
        print("Upload cancelled.")
        return 0

    # Upload
    success = upload_dataset(
        repo_id=args.repo_id,
        data_dir=args.data_dir,
        private=args.private,
        create_if_not_exists=not args.no_create
    )

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
