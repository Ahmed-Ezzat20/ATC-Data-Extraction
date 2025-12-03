#!/usr/bin/env python3
"""
Upload ATC Dataset to Hugging Face (No Audio)

Uploads only CSV and transcript files, excluding audio files.

Prerequisites:
    pip install huggingface_hub

Usage:
    python upload_to_huggingface_no_audio.py --repo-id "username/dataset-name"
"""

import argparse
import sys
import json
from pathlib import Path
from huggingface_hub import HfApi, create_repo
from huggingface_hub.utils import HfHubHTTPError


def check_authentication():
    """Check if user is authenticated with Hugging Face."""
    try:
        api = HfApi()
        api.whoami()
        return True
    except Exception:
        return False


def create_dataset_card_no_audio(data_dir, output_file='README.md'):
    """
    Create dataset card for text-only dataset.

    Args:
        data_dir: Data directory path
        output_file: Output file path
    """
    data_path = Path(data_dir)

    # Gather statistics
    transcript_files = list((data_path / 'transcripts').glob('*.json'))
    transcript_files = [f for f in transcript_files if not f.stem.endswith('_raw')]

    # Count segments and words
    total_segments = 0
    total_duration = 0
    total_words = 0

    for json_file in transcript_files:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            for seg in data['segments']:
                total_segments += 1
                total_duration += seg['duration']
                total_words += len(seg['transcript'].split())

    card_content = f"""---
license: cc-by-4.0
task_categories:
- automatic-speech-recognition
- text-classification
- text-generation
language:
- en
tags:
- aviation
- atc
- air-traffic-control
- transcriptions
- text
size_categories:
- 10K<n<100K
---

# ATC (Air Traffic Control) Communications Transcriptions Dataset

## Dataset Description

This dataset contains transcriptions of Air Traffic Control (ATC) communications extracted from YouTube videos.

**Note**: This dataset contains only text transcriptions. Audio files are not included.

### Dataset Summary

- **Total Transcription Segments**: {total_segments:,}
- **Total Videos**: {len(transcript_files)}
- **Total Duration**: ~{total_duration/60:.1f} minutes (~{total_duration/3600:.1f} hours)
- **Total Words**: ~{total_words:,}
- **Language**: English (Aviation/ATC terminology)

### Supported Tasks

- **Text Analysis**: Analyze ATC communication patterns
- **Named Entity Recognition**: Extract callsigns, airports, altitudes
- **Text Classification**: Classify types of ATC communications
- **Language Modeling**: Train models on aviation terminology
- **Keyword Extraction**: Identify aviation-specific terms

## Dataset Structure

### Data Files

The dataset consists of:
- **Transcript files**: `transcripts/*.json` - Full transcript data per video
- **Transcriptions**: `all_segments.csv` - Basic transcription text
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
{{
  "video_id": "VIDEO_ID",
  "video_url": "https://www.youtube.com/watch?v=VIDEO_ID",
  "segments": [
    {{
      "segment_num": 1,
      "start_time": 0.0,
      "duration": 3.5,
      "transcript": "American 123 contact tower 118.3",
      "timestamp_range": "0:00:00.0 - 0:00:03.5"
    }}
  ]
}}
```

### Data Fields

- `audio_filename`: Reference name for the audio segment (audio not included)
- `transcription`: Text transcription of the communication
- `video_id`: YouTube video ID (source)
- `segment_num`: Segment number within the video
- `start_time`: Start time in seconds (within source video)
- `duration`: Duration of the segment in seconds
- `timestamp_range`: Human-readable timestamp range

## Dataset Creation

### Source Data

Transcriptions extracted from publicly available YouTube videos containing ATC communications.

### Extraction Process

1. Subtitle extraction from YouTube videos
2. Timestamp-based segmentation
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

### Transcription Quality

Transcription quality varies depending on:
- Original recording quality
- Automatic transcription accuracy
- Radio transmission clarity

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
dataset = load_dataset("{{repo_id}}")

# Access transcriptions
for example in dataset['train']:
    transcription = example['transcription']
    print(f"Transcription: {{transcription}}")
```

### Loading with Pandas

```python
import pandas as pd

# Load CSV
df = pd.read_csv('hf://datasets/{{repo_id}}/all_segments.csv')

# Access transcriptions
print(df[['audio_filename', 'transcription']].head())
```

### Loading Transcript JSON Files

```python
from huggingface_hub import hf_hub_download
import json

# Download a transcript file
transcript_path = hf_hub_download(
    repo_id="{{repo_id}}",
    filename="transcripts/VIDEO_ID.json",
    repo_type="dataset"
)

# Load the transcript
with open(transcript_path, 'r') as f:
    data = json.load(f)

print(f"Video: {{data['video_id']}}")
print(f"Segments: {{len(data['segments'])}}")
```

## Citation

If you use this dataset, please cite:

```bibtex
@dataset{{atc_transcriptions,
  title={{ATC Communications Transcriptions Dataset}},
  author={{Your Name}},
  year={{2024}},
  publisher={{Hugging Face}},
  url={{https://huggingface.co/datasets/{{repo_id}}}}
}}
```

## License

This dataset is released under CC-BY-4.0 license.

## Contact

For questions or issues, please open an issue on the dataset repository.

---

**Note**: This dataset contains only transcriptions. Audio files are not included.
If you need audio files, they can be sourced from the original YouTube videos using the video IDs provided.
"""

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(card_content)

    print(f"[OK] Dataset card created: {output_file}")
    return output_file


def upload_dataset_no_audio(repo_id, data_dir='data', private=False):
    """
    Upload dataset without audio files.

    Args:
        repo_id: Repository ID (username/dataset-name)
        data_dir: Data directory path
        private: Whether to create a private repository

    Returns:
        True if successful
    """
    api = HfApi()
    data_path = Path(data_dir)

    print("=" * 70)
    print("UPLOADING TO HUGGING FACE (NO AUDIO)")
    print("=" * 70)
    print(f"\nRepository: {repo_id}")
    print(f"Data directory: {data_path.absolute()}")
    print(f"Private: {private}")

    # Check if repo exists or create it
    try:
        api.repo_info(repo_id=repo_id, repo_type="dataset")
        print(f"\n[OK] Repository exists: {repo_id}")
    except HfHubHTTPError:
        print(f"\n[!] Creating repository: {repo_id}")
        create_repo(
            repo_id=repo_id,
            repo_type="dataset",
            private=private,
            exist_ok=True
        )
        print(f"[OK] Repository created")

    # Step 1: Create and upload README
    print("\n" + "-" * 70)
    print("Step 1: Creating and uploading README...")

    readme_path = create_dataset_card_no_audio(data_dir, 'README.md')
    # Update repo_id placeholder in README
    with open(readme_path, 'r') as f:
        content = f.read()
    content = content.replace('{repo_id}', repo_id)
    with open(readme_path, 'w') as f:
        f.write(content)

    api.upload_file(
        path_or_fileobj=readme_path,
        path_in_repo="README.md",
        repo_id=repo_id,
        repo_type="dataset"
    )
    print("[OK] README.md uploaded")

    # Step 2: Upload CSV files
    print("\n" + "-" * 70)
    print("Step 2: Uploading CSV files...")

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

    # Step 3: Upload transcript files
    print("\n" + "-" * 70)
    print("Step 3: Uploading transcript files...")

    transcripts_dir = data_path / 'transcripts'
    if transcripts_dir.exists():
        transcript_files = [f for f in transcripts_dir.glob('*.json')
                          if not f.stem.endswith('_raw')]
        print(f"Found {len(transcript_files)} transcript files")

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
        print("[X] transcripts directory not found")
        return False

    # Step 4: Upload analysis report (optional)
    print("\n" + "-" * 70)
    print("Step 4: Uploading analysis report...")

    report_path = data_path / 'analysis_report.txt'
    if report_path.exists():
        api.upload_file(
            path_or_fileobj=str(report_path),
            path_in_repo="analysis_report.txt",
            repo_id=repo_id,
            repo_type="dataset"
        )
        print("[OK] analysis_report.txt uploaded")

    # Summary
    print("\n" + "=" * 70)
    print("UPLOAD COMPLETE")
    print("=" * 70)
    print(f"\nDataset URL: https://huggingface.co/datasets/{repo_id}")
    print(f"\nUploaded files:")
    print("  - README.md (dataset card)")
    print("  - all_segments.csv")
    print("  - all_segments_detailed.csv")
    print("  - transcripts/ (JSON files)")
    print("  - analysis_report.txt")
    print("\nYou can now:")
    print("1. View your dataset on Hugging Face")
    print("2. Share it with others")
    print(f"3. Load it with: load_dataset('{repo_id}')")

    return True


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Upload ATC dataset to Hugging Face Hub (CSV and transcripts only)"
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

    args = parser.parse_args()

    # Check authentication
    print("Checking Hugging Face authentication...")
    if not check_authentication():
        print("\n[X] Not authenticated with Hugging Face")
        print("\nPlease login first:")
        print("  huggingface-cli login")
        return 1

    print("[OK] Authenticated")

    # Confirm
    print("\n" + "=" * 70)
    print(f"Ready to upload to: {args.repo_id}")
    print(f"Data directory: {args.data_dir}")
    print(f"Private: {args.private}")
    print("\nWill upload:")
    print("  - CSV files (transcriptions)")
    print("  - Transcript JSON files")
    print("  - Analysis report")
    print("  - README (dataset card)")
    print("\nWill NOT upload:")
    print("  - Audio WAV files (excluded)")
    print("=" * 70)

    response = input("\nProceed with upload? (yes/no): ").strip().lower()
    if response not in ['yes', 'y']:
        print("Upload cancelled.")
        return 0

    # Upload
    success = upload_dataset_no_audio(
        repo_id=args.repo_id,
        data_dir=args.data_dir,
        private=args.private
    )

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
