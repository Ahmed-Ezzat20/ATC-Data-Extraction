#!/usr/bin/env python3
"""
Upload ATC Parquet Dataset to Hugging Face

Uploads the Parquet dataset to Hugging Face Hub.
The Parquet format is ideal for datasets with audio as it keeps everything in a single file.

Prerequisites:
    pip install huggingface_hub

Usage:
    python upload_parquet_to_huggingface.py --repo-id "username/dataset-name" --parquet-file atc_dataset.parquet
"""

import argparse
import sys
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


def create_dataset_card_parquet(parquet_file, repo_id, output_file='README.md'):
    """
    Create dataset card for Parquet dataset.

    Args:
        parquet_file: Path to Parquet file
        repo_id: Repository ID
        output_file: Output file path
    """
    import pandas as pd

    # Load dataset to get statistics
    parquet_path = Path(parquet_file)
    file_size_mb = parquet_path.stat().st_size / (1024 * 1024)

    try:
        df = pd.read_parquet(parquet_file)
        total_segments = len(df)
        total_videos = df['video_id'].nunique()
        has_audio = 'audio' in df.columns

        # Calculate duration
        total_duration = df['duration'].sum()
        total_hours = total_duration / 3600

        # Word count
        df['word_count'] = df['transcription'].str.split().str.len()
        total_words = df['word_count'].sum()

    except Exception as e:
        print(f"[!] Warning: Could not read Parquet file for statistics: {e}")
        total_segments = 0
        total_videos = 0
        total_hours = 0
        total_words = 0
        has_audio = False

    card_content = f"""---
license: cc-by-4.0
task_categories:
- automatic-speech-recognition
- audio-classification
- text-to-speech
language:
- en
tags:
- aviation
- atc
- air-traffic-control
- audio
- speech
size_categories:
- 1K<n<10K
dataset_info:
  features:
  - name: audio_filename
    dtype: string
  - name: video_id
    dtype: string
  - name: segment_num
    dtype: int64
  - name: transcription
    dtype: string
  - name: original_transcription
    dtype: string
  - name: audio
    dtype: binary
  - name: start_time
    dtype: float64
  - name: duration
    dtype: float64
  - name: timestamp_range
    dtype: string
  splits:
  - name: train
    num_bytes: {int(file_size_mb * 1024 * 1024)}
    num_examples: {total_segments}
---

# ATC (Air Traffic Control) Communications Dataset

## Dataset Description

This dataset contains Air Traffic Control (ATC) communications extracted from YouTube videos, with both audio and transcriptions in a single Parquet file.

### Dataset Summary

- **Total Audio Segments**: {total_segments:,}
- **Total Videos**: {total_videos}
- **Total Duration**: ~{total_hours:.1f} hours
- **Total Words**: ~{total_words:,}
- **Language**: English (Aviation/ATC terminology)
- **Format**: Parquet with embedded audio
- **Audio Included**: {'Yes' if has_audio else 'No'}

### Supported Tasks

- **Automatic Speech Recognition (ASR)**: Train models on aviation-specific speech
- **Audio Classification**: Classify types of ATC communications
- **Speaker Diarization**: Identify pilot vs. controller speech
- **Text-to-Speech**: Generate synthetic ATC communications
- **Language Modeling**: Train models on aviation terminology
- **Named Entity Recognition**: Extract callsigns, airports, altitudes

## Dataset Structure

### Data Format

The dataset is provided as a single Parquet file containing all data.

### Schema

Each record contains:

- **`audio_filename`**: WAV file name (e.g., "VIDEO_ID_seg001.wav")
- **`video_id`**: YouTube video ID (source)
- **`segment_num`**: Segment number within the video
- **`transcription`**: Preprocessed/normalized transcription (uppercase, standardized)
- **`original_transcription`**: Original transcription (before preprocessing)
- **`audio`**: Binary WAV file data (16-bit PCM, 44.1kHz, stereo)
- **`start_time`**: Start time in seconds (within source video)
- **`duration`**: Segment duration in seconds
- **`timestamp_range`**: Human-readable timestamp

### Data Instances

Example record:

```python
{{
    'audio_filename': '94VPOXc2bEM_seg001.wav',
    'video_id': '94VPOXc2bEM',
    'segment_num': 1,
    'transcription': 'AMERICAN ONE TWO THREE CONTACT TOWER ONE ONE EIGHT DECIMAL THREE',
    'original_transcription': 'American 123 contact tower 118.3',
    'audio': b'\\x52\\x49\\x46\\x46...',  # Binary WAV data
    'start_time': 5.0,
    'duration': 6.0,
    'timestamp_range': '[00:05 - 00:11]'
}}
```

## Usage

### Loading the Dataset

#### With Hugging Face Datasets

```python
from datasets import load_dataset

# Load dataset
dataset = load_dataset("{repo_id}")

# Access a sample
sample = dataset['train'][0]
print(f"Transcription: {{sample['transcription']}}")

# Access audio
audio_bytes = sample['audio']
```

#### With Pandas

```python
import pandas as pd
from huggingface_hub import hf_hub_download

# Download Parquet file
file_path = hf_hub_download(
    repo_id="{repo_id}",
    filename="data/train.parquet",
    repo_type="dataset"
)

# Load with pandas
df = pd.read_parquet(file_path)

print(f"Total records: {{len(df):,}}")
print(df.head())
```

### Extracting Audio

```python
import pandas as pd
import io
import soundfile as sf

# Load dataset
df = pd.read_parquet(file_path)

# Extract audio from first record
audio_bytes = io.BytesIO(df.iloc[0]['audio'])
audio_data, sample_rate = sf.read(audio_bytes)

print(f"Audio shape: {{audio_data.shape}}")
print(f"Sample rate: {{sample_rate}} Hz")
```

### Using with PyTorch

```python
import torch
from torch.utils.data import Dataset
import pandas as pd
import io
import soundfile as sf

class ATCDataset(Dataset):
    def __init__(self, parquet_file):
        self.df = pd.read_parquet(parquet_file)

    def __len__(self):
        return len(self.df)

    def __getitem__(self, idx):
        row = self.df.iloc[idx]

        # Load audio
        audio_bytes = io.BytesIO(row['audio'])
        audio, sr = sf.read(audio_bytes)

        return {{
            'audio': torch.tensor(audio, dtype=torch.float32),
            'transcription': row['transcription'],
            'sample_rate': sr
        }}

# Usage
from huggingface_hub import hf_hub_download

file_path = hf_hub_download(
    repo_id="{repo_id}",
    filename="data/train.parquet",
    repo_type="dataset"
)

dataset = ATCDataset(file_path)
dataloader = torch.utils.data.DataLoader(dataset, batch_size=32)
```

### Filtering and Searching

```python
# Load dataset
df = pd.read_parquet(file_path)

# Search for specific terms
tower_comms = df[df['transcription'].str.contains('TOWER', na=False)]

# Filter by video
video_data = df[df['video_id'] == 'SPECIFIC_VIDEO_ID']

# Filter by duration
short_segments = df[df['duration'] < 5.0]
```

## Dataset Creation

### Source Data

Audio and transcriptions extracted from publicly available YouTube videos containing ATC communications.

### Preprocessing Pipeline

1. **Subtitle Extraction**: Using Google Gemini 2.5 Pro API
2. **Audio Segmentation**: Using FFmpeg based on timestamps
3. **Text Normalization**:
   - Uppercase conversion
   - Number expansion (e.g., "123" → "ONE TWO THREE")
   - Phonetic alphabet expansion (e.g., "N" → "NOVEMBER")
   - Spelling corrections
   - Punctuation removal
4. **Quality Filtering**: Removed unintelligible and non-English segments
5. **Parquet Export**: Embedded audio with metadata

### Transcription Processing

The `transcription` field includes:
- **Uppercase normalization**: All text in uppercase
- **Number-to-word**: "118.3" → "ONE ONE EIGHT DECIMAL THREE"
- **Phonetic expansion**: "N 4 5 6" → "NOVEMBER FOUR FIVE SIX"
- **Standardized terminology**: Common ATC terms normalized

The `original_transcription` field preserves the original text before preprocessing.

## Considerations

### Aviation Terminology

This dataset contains specialized aviation terminology:
- Radio callsigns (airline flights, tail numbers)
- Airport codes (ICAO/IATA)
- Altitudes, headings, speeds
- Standard phraseology (cleared, roger, wilco, etc.)
- Runway designators (27L, 09R, etc.)

### Audio Quality

Audio quality varies based on:
- Original recording quality
- Radio transmission clarity
- Background noise levels

### Ethical Considerations

- All data from publicly available sources
- Contains real ATC communications (publicly broadcast)
- May include sensitive flight information
- Intended for research and educational purposes only

### Limitations

- Audio quality varies across sources
- Some transcriptions may have errors
- Not all ATC communications types equally represented
- Dataset reflects specific geographic regions/airports

## Citation

If you use this dataset, please cite:

```bibtex
@dataset{{atc_communications,
  title={{ATC Communications Dataset with Audio}},
  author={{Your Name}},
  year={{2024}},
  publisher={{Hugging Face}},
  url={{https://huggingface.co/datasets/{repo_id}}}
}}
```

## License

This dataset is released under CC-BY-4.0 license.

## Changelog

### Version 1.0
- Initial release
- {total_segments:,} audio segments
- Preprocessed transcriptions
- Parquet format with embedded audio

## Contact

For questions, issues, or feedback, please open an issue on the dataset repository.

---

**Dataset Size**: {file_size_mb:.2f} MB

**Last Updated**: 2024
"""

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(card_content)

    print(f"[OK] Dataset card created: {output_file}")
    return output_file


def upload_parquet_dataset(repo_id, parquet_file, private=False):
    """
    Upload Parquet dataset to Hugging Face Hub.

    Args:
        repo_id: Repository ID (username/dataset-name)
        parquet_file: Path to Parquet file
        private: Whether to create a private repository

    Returns:
        True if successful
    """
    api = HfApi()
    parquet_path = Path(parquet_file)

    if not parquet_path.exists():
        print(f"[X] Error: Parquet file not found: {parquet_file}")
        return False

    file_size_mb = parquet_path.stat().st_size / (1024 * 1024)

    print("=" * 70)
    print("UPLOADING PARQUET DATASET TO HUGGING FACE")
    print("=" * 70)
    print(f"\nRepository: {repo_id}")
    print(f"Parquet file: {parquet_path.absolute()}")
    print(f"File size: {file_size_mb:.2f} MB")
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

    readme_path = create_dataset_card_parquet(parquet_file, repo_id, 'README.md')

    api.upload_file(
        path_or_fileobj=readme_path,
        path_in_repo="README.md",
        repo_id=repo_id,
        repo_type="dataset"
    )
    print("[OK] README.md uploaded")

    # Step 2: Upload Parquet file
    print("\n" + "-" * 70)
    print("Step 2: Uploading Parquet file...")
    print(f"  This may take a while for large files ({file_size_mb:.2f} MB)...")

    api.upload_file(
        path_or_fileobj=str(parquet_path),
        path_in_repo="data/train.parquet",
        repo_id=repo_id,
        repo_type="dataset"
    )
    print(f"[OK] {parquet_path.name} uploaded as data/train.parquet")

    # Summary
    print("\n" + "=" * 70)
    print("UPLOAD COMPLETE")
    print("=" * 70)
    print(f"\nDataset URL: https://huggingface.co/datasets/{repo_id}")
    print(f"\nUploaded files:")
    print("  - README.md (dataset card)")
    print(f"  - data/train.parquet ({file_size_mb:.2f} MB)")
    print("\nYou can now:")
    print("1. View your dataset on Hugging Face")
    print("2. Share it with others")
    print(f"3. Load it with: load_dataset('{repo_id}')")
    print("\nLoading example:")
    print(f"""
from datasets import load_dataset
dataset = load_dataset('{repo_id}')
    """)

    return True


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Upload ATC Parquet dataset to Hugging Face Hub"
    )
    parser.add_argument(
        '--repo-id',
        required=True,
        help='Repository ID (username/dataset-name)'
    )
    parser.add_argument(
        '--parquet-file',
        default='atc_dataset.parquet',
        help='Path to Parquet file (default: atc_dataset.parquet)'
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
    parquet_path = Path(args.parquet_file)
    if not parquet_path.exists():
        print(f"\n[X] Error: Parquet file not found: {args.parquet_file}")
        return 1

    file_size_mb = parquet_path.stat().st_size / (1024 * 1024)

    print("\n" + "=" * 70)
    print(f"Ready to upload to: {args.repo_id}")
    print(f"Parquet file: {parquet_path.absolute()}")
    print(f"File size: {file_size_mb:.2f} MB")
    print(f"Private: {args.private}")
    print("=" * 70)

    response = input("\nProceed with upload? (yes/no): ").strip().lower()
    if response not in ['yes', 'y']:
        print("Upload cancelled.")
        return 0

    # Upload
    success = upload_parquet_dataset(
        repo_id=args.repo_id,
        parquet_file=args.parquet_file,
        private=args.private
    )

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
