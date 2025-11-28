#!/usr/bin/env python3
"""
Prepare and Upload ATC Dataset to Hugging Face

Complete pipeline that:
1. Loads preprocessed transcripts
2. Splits dataset into train/validation/test
3. Exports each split to Parquet with embedded audio
4. Uploads to Hugging Face Hub

Usage:
    python prepare_and_upload_dataset.py --repo-id "username/atc-dataset" [options]
"""

import argparse
import sys
import json
from pathlib import Path
from typing import List, Dict, Tuple
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from tqdm import tqdm
from huggingface_hub import HfApi, create_repo
from huggingface_hub.utils import HfHubHTTPError
import random


class DatasetPreparation:
    """Prepare and upload ATC dataset."""

    def __init__(
        self,
        transcripts_dir: str,
        audio_dir: str,
        output_dir: str = "dataset_parquet",
        train_ratio: float = 0.8,
        val_ratio: float = 0.1,
        test_ratio: float = 0.1,
        random_seed: int = 42,
        include_audio: bool = True
    ):
        """
        Initialize dataset preparation.

        Args:
            transcripts_dir: Directory containing transcript JSON files
            audio_dir: Directory containing audio WAV files
            output_dir: Output directory for Parquet files
            train_ratio: Ratio for training set (default: 0.8)
            val_ratio: Ratio for validation set (default: 0.1)
            test_ratio: Ratio for test set (default: 0.1)
            random_seed: Random seed for reproducibility
            include_audio: Whether to include audio in Parquet files
        """
        self.transcripts_dir = Path(transcripts_dir)
        self.audio_dir = Path(audio_dir)
        self.output_dir = Path(output_dir)
        self.train_ratio = train_ratio
        self.val_ratio = val_ratio
        self.test_ratio = test_ratio
        self.random_seed = random_seed
        self.include_audio = include_audio

        # Validate split ratios
        total_ratio = train_ratio + val_ratio + test_ratio
        if not (0.99 < total_ratio < 1.01):  # Allow small floating point errors
            raise ValueError(f"Split ratios must sum to 1.0, got {total_ratio}")

        random.seed(random_seed)

        # Statistics
        self.stats = {
            'total_videos': 0,
            'total_segments': 0,
            'train_videos': 0,
            'train_segments': 0,
            'val_videos': 0,
            'val_segments': 0,
            'test_videos': 0,
            'test_segments': 0,
            'missing_audio': 0,
        }

    def load_transcripts(self) -> Dict[str, List[Dict]]:
        """
        Load all transcript files grouped by video.

        Returns:
            Dictionary mapping video_id to list of segments
        """
        print("\n" + "="*70)
        print("LOADING TRANSCRIPTS")
        print("="*70)

        transcript_files = sorted(self.transcripts_dir.glob("*.json"))
        transcript_files = [f for f in transcript_files if not f.stem.endswith('_raw')]

        if not transcript_files:
            print("[!] No transcript files found")
            return {}

        print(f"Found {len(transcript_files)} transcript files")

        videos_data = {}

        for transcript_file in tqdm(transcript_files, desc="Loading transcripts"):
            with open(transcript_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            video_id = data['video_id']
            videos_data[video_id] = data['segments']

        total_segments = sum(len(segments) for segments in videos_data.values())

        print(f"Loaded {len(videos_data)} videos with {total_segments:,} total segments")

        self.stats['total_videos'] = len(videos_data)
        self.stats['total_segments'] = total_segments

        return videos_data

    def split_videos(self, videos_data: Dict[str, List[Dict]]) -> Tuple[List[str], List[str], List[str]]:
        """
        Split videos into train/validation/test sets.

        Args:
            videos_data: Dictionary mapping video_id to segments

        Returns:
            Tuple of (train_video_ids, val_video_ids, test_video_ids)
        """
        print("\n" + "="*70)
        print("SPLITTING DATASET")
        print("="*70)

        video_ids = list(videos_data.keys())
        random.shuffle(video_ids)

        n_videos = len(video_ids)
        n_train = int(n_videos * self.train_ratio)
        n_val = int(n_videos * self.val_ratio)

        train_videos = video_ids[:n_train]
        val_videos = video_ids[n_train:n_train + n_val]
        test_videos = video_ids[n_train + n_val:]

        # Calculate statistics
        train_segments = sum(len(videos_data[vid]) for vid in train_videos)
        val_segments = sum(len(videos_data[vid]) for vid in val_videos)
        test_segments = sum(len(videos_data[vid]) for vid in test_videos)

        print(f"\nSplit configuration:")
        print(f"  Random seed: {self.random_seed}")
        print(f"  Train ratio: {self.train_ratio:.1%}")
        print(f"  Validation ratio: {self.val_ratio:.1%}")
        print(f"  Test ratio: {self.test_ratio:.1%}")

        print(f"\nSplit results:")
        print(f"  Train: {len(train_videos)} videos, {train_segments:,} segments")
        print(f"  Validation: {len(val_videos)} videos, {val_segments:,} segments")
        print(f"  Test: {len(test_videos)} videos, {test_segments:,} segments")

        self.stats['train_videos'] = len(train_videos)
        self.stats['train_segments'] = train_segments
        self.stats['val_videos'] = len(val_videos)
        self.stats['val_segments'] = val_segments
        self.stats['test_videos'] = len(test_videos)
        self.stats['test_segments'] = test_segments

        return train_videos, val_videos, test_videos

    def load_audio_file(self, audio_filename: str) -> bytes | None:
        """Load audio file as binary data."""
        audio_path = self.audio_dir / audio_filename

        if not audio_path.exists():
            return None

        with open(audio_path, 'rb') as f:
            return f.read()

    def create_split_dataframe(
        self,
        videos_data: Dict[str, List[Dict]],
        video_ids: List[str],
        split_name: str
    ) -> pd.DataFrame:
        """
        Create DataFrame for a specific split.

        Args:
            videos_data: All videos data
            video_ids: Video IDs for this split
            split_name: Name of the split (for logging)

        Returns:
            pandas DataFrame
        """
        print(f"\n  Creating {split_name} split...")

        segments = []

        for video_id in tqdm(video_ids, desc=f"  Processing {split_name}"):
            for segment in videos_data[video_id]:
                segment_data = {
                    'audio_filename': f"{video_id}_seg{segment['segment_num']:03d}.wav",
                    'video_id': video_id,
                    'segment_num': segment['segment_num'],
                    'transcription': segment['transcript'],
                    'original_transcription': segment.get('original_transcript', segment['transcript']),
                    'start_time': segment['start_time'],
                    'duration': segment['duration'],
                    'timestamp_range': segment['timestamp_range'],
                }

                # Load audio if requested
                if self.include_audio:
                    audio_bytes = self.load_audio_file(segment_data['audio_filename'])
                    if audio_bytes is None:
                        self.stats['missing_audio'] += 1
                    segment_data['audio'] = audio_bytes

                segments.append(segment_data)

        return pd.DataFrame(segments)

    def export_to_parquet(
        self,
        df: pd.DataFrame,
        output_file: Path,
        split_name: str
    ):
        """
        Export DataFrame to Parquet file.

        Args:
            df: DataFrame to export
            output_file: Output file path
            split_name: Name of split (for logging)
        """
        print(f"  Writing {split_name} to Parquet: {output_file.name}")

        # Define schema
        if self.include_audio:
            schema = pa.schema([
                ('audio_filename', pa.string()),
                ('video_id', pa.string()),
                ('segment_num', pa.int64()),
                ('transcription', pa.string()),
                ('original_transcription', pa.string()),
                ('audio', pa.binary()),
                ('start_time', pa.float64()),
                ('duration', pa.float64()),
                ('timestamp_range', pa.string()),
            ])
        else:
            schema = pa.schema([
                ('audio_filename', pa.string()),
                ('video_id', pa.string()),
                ('segment_num', pa.int64()),
                ('transcription', pa.string()),
                ('original_transcription', pa.string()),
                ('start_time', pa.float64()),
                ('duration', pa.float64()),
                ('timestamp_range', pa.string()),
            ])

        # Convert to PyArrow Table
        table = pa.Table.from_pandas(df, schema=schema)

        # Write with compression
        pq.write_table(
            table,
            output_file,
            compression='snappy',
            use_dictionary=True,
        )

        file_size_mb = output_file.stat().st_size / (1024 * 1024)
        print(f"  [OK] {split_name}: {len(df):,} segments, {file_size_mb:.2f} MB")

    def create_parquet_files(self, videos_data: Dict[str, List[Dict]]) -> Dict[str, Path]:
        """
        Create Parquet files for all splits.

        Args:
            videos_data: All videos data

        Returns:
            Dictionary mapping split name to file path
        """
        print("\n" + "="*70)
        print("CREATING PARQUET FILES")
        print("="*70)

        # Split videos
        train_videos, val_videos, test_videos = self.split_videos(videos_data)

        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Create splits
        splits = {
            'train': train_videos,
            'validation': val_videos,
            'test': test_videos
        }

        parquet_files = {}

        for split_name, video_ids in splits.items():
            if not video_ids:
                print(f"  [!] Skipping {split_name} (no videos)")
                continue

            # Create DataFrame
            df = self.create_split_dataframe(videos_data, video_ids, split_name)

            # Export to Parquet
            output_file = self.output_dir / f"{split_name}.parquet"
            self.export_to_parquet(df, output_file, split_name)

            parquet_files[split_name] = output_file

        if self.stats['missing_audio'] > 0:
            print(f"\n[!] Warning: {self.stats['missing_audio']} audio files not found")

        return parquet_files

    def print_summary(self):
        """Print dataset summary."""
        print("\n" + "="*70)
        print("DATASET PREPARATION SUMMARY")
        print("="*70)

        print(f"\nTotal dataset:")
        print(f"  Videos: {self.stats['total_videos']}")
        print(f"  Segments: {self.stats['total_segments']:,}")

        print(f"\nSplit breakdown:")
        print(f"  Train:")
        print(f"    Videos: {self.stats['train_videos']} ({self.stats['train_videos']/self.stats['total_videos']*100:.1f}%)")
        print(f"    Segments: {self.stats['train_segments']:,} ({self.stats['train_segments']/self.stats['total_segments']*100:.1f}%)")

        print(f"  Validation:")
        print(f"    Videos: {self.stats['val_videos']} ({self.stats['val_videos']/self.stats['total_videos']*100:.1f}%)")
        print(f"    Segments: {self.stats['val_segments']:,} ({self.stats['val_segments']/self.stats['total_segments']*100:.1f}%)")

        print(f"  Test:")
        print(f"    Videos: {self.stats['test_videos']} ({self.stats['test_videos']/self.stats['total_videos']*100:.1f}%)")
        print(f"    Segments: {self.stats['test_segments']:,} ({self.stats['test_segments']/self.stats['total_segments']*100:.1f}%)")

        if self.include_audio:
            print(f"\nAudio:")
            print(f"  Missing files: {self.stats['missing_audio']:,}")

        print(f"\nOutput directory: {self.output_dir.absolute()}")
        print("="*70)


class HuggingFaceUploader:
    """Upload dataset to Hugging Face Hub."""

    def __init__(self, repo_id: str, private: bool = False):
        """
        Initialize uploader.

        Args:
            repo_id: Repository ID (username/dataset-name)
            private: Whether to create private repository
        """
        self.repo_id = repo_id
        self.private = private
        self.api = HfApi()

    def create_dataset_card(self, stats: dict, output_file: str = "README.md"):
        """Create comprehensive dataset card."""

        total_hours = (stats['train_segments'] + stats['val_segments'] + stats['test_segments']) * 5 / 3600  # Estimate

        card = f"""---
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
- audio
- speech
size_categories:
- 1K<n<10K
---

# ATC (Air Traffic Control) Communications Dataset

## Dataset Description

Complete ATC communications dataset with audio and transcriptions, split into train/validation/test sets.

### Dataset Summary

- **Total Segments**: {stats['total_segments']:,}
- **Total Videos**: {stats['total_videos']}
- **Estimated Duration**: ~{total_hours:.1f} hours
- **Language**: English (Aviation/ATC terminology)
- **Format**: Parquet with embedded audio
- **Splits**: Train ({stats['train_segments']:,}), Validation ({stats['val_segments']:,}), Test ({stats['test_segments']:,})

### Splits

| Split | Videos | Segments | Percentage |
|-------|--------|----------|------------|
| Train | {stats['train_videos']} | {stats['train_segments']:,} | {stats['train_segments']/stats['total_segments']*100:.1f}% |
| Validation | {stats['val_videos']} | {stats['val_segments']:,} | {stats['val_segments']/stats['total_segments']*100:.1f}% |
| Test | {stats['test_videos']} | {stats['test_segments']:,} | {stats['test_segments']/stats['total_segments']*100:.1f}% |

**Note**: Splits are by video (all segments from a video stay in the same split).

## Usage

### Load with Hugging Face Datasets

```python
from datasets import load_dataset

# Load all splits
dataset = load_dataset("{self.repo_id}")

# Access splits
train_data = dataset['train']
val_data = dataset['validation']
test_data = dataset['test']

# Access a sample
sample = train_data[0]
print(f"Transcription: {{sample['transcription']}}")
audio_bytes = sample['audio']
```

### Load with Pandas

```python
import pandas as pd
from huggingface_hub import hf_hub_download

# Download specific split
train_path = hf_hub_download(
    repo_id="{self.repo_id}",
    filename="train.parquet",
    repo_type="dataset"
)

df = pd.read_parquet(train_path)
```

### PyTorch DataLoader

```python
import torch
from torch.utils.data import Dataset, DataLoader
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
        audio_bytes = io.BytesIO(row['audio'])
        audio, sr = sf.read(audio_bytes)

        return {{
            'audio': torch.tensor(audio, dtype=torch.float32),
            'transcription': row['transcription'],
            'sample_rate': sr
        }}

# Usage
dataset = ATCDataset(train_path)
dataloader = DataLoader(dataset, batch_size=32, shuffle=True)
```

## Dataset Schema

- **audio_filename**: WAV file name
- **video_id**: Source YouTube video ID
- **segment_num**: Segment number within video
- **transcription**: Preprocessed transcription (uppercase, standardized)
- **original_transcription**: Original transcription before preprocessing
- **audio**: Binary WAV data (16-bit PCM, 44.1kHz, stereo)
- **start_time**: Start time in seconds
- **duration**: Duration in seconds
- **timestamp_range**: Human-readable timestamp

## Preprocessing

Transcriptions include:
- Uppercase normalization
- Number-to-word expansion (e.g., "118.3" → "ONE ONE EIGHT DECIMAL THREE")
- Phonetic alphabet expansion (e.g., "N" → "NOVEMBER")
- Spelling corrections
- Punctuation removal

## Citation

```bibtex
@dataset{{atc_dataset,
  title={{ATC Communications Dataset}},
  year={{2024}},
  publisher={{Hugging Face}},
  url={{https://huggingface.co/datasets/{self.repo_id}}}
}}
```

## License

CC-BY-4.0
"""

        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(card)

        print(f"[OK] Dataset card created: {output_file}")
        return output_file

    def upload(self, parquet_files: Dict[str, Path], stats: dict) -> bool:
        """
        Upload dataset to Hugging Face.

        Args:
            parquet_files: Dictionary mapping split name to file path
            stats: Dataset statistics

        Returns:
            True if successful
        """
        print("\n" + "="*70)
        print("UPLOADING TO HUGGING FACE")
        print("="*70)
        print(f"\nRepository: {self.repo_id}")
        print(f"Private: {self.private}")

        # Create repository
        try:
            self.api.repo_info(repo_id=self.repo_id, repo_type="dataset")
            print(f"[OK] Repository exists")
        except HfHubHTTPError:
            print(f"[!] Creating repository...")
            create_repo(
                repo_id=self.repo_id,
                repo_type="dataset",
                private=self.private,
                exist_ok=True
            )
            print(f"[OK] Repository created")

        # Create and upload README
        print("\nUploading README...")
        readme_path = self.create_dataset_card(stats)
        self.api.upload_file(
            path_or_fileobj=readme_path,
            path_in_repo="README.md",
            repo_id=self.repo_id,
            repo_type="dataset"
        )
        print("[OK] README uploaded")

        # Upload Parquet files
        print("\nUploading Parquet files...")
        for split_name, file_path in parquet_files.items():
            file_size_mb = file_path.stat().st_size / (1024 * 1024)
            print(f"  Uploading {split_name}.parquet ({file_size_mb:.2f} MB)...")

            self.api.upload_file(
                path_or_fileobj=str(file_path),
                path_in_repo=f"{split_name}.parquet",
                repo_id=self.repo_id,
                repo_type="dataset"
            )
            print(f"  [OK] {split_name}.parquet uploaded")

        print("\n" + "="*70)
        print("UPLOAD COMPLETE")
        print("="*70)
        print(f"\nDataset URL: https://huggingface.co/datasets/{self.repo_id}")
        print(f"\nLoad with: load_dataset('{self.repo_id}')")
        print("="*70)

        return True


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Prepare and upload ATC dataset to Hugging Face"
    )
    parser.add_argument(
        '--repo-id',
        required=True,
        help='Hugging Face repository ID (username/dataset-name)'
    )
    parser.add_argument(
        '--data-dir',
        default='data/preprocessed',
        help='Directory with preprocessed transcripts (default: data/preprocessed)'
    )
    parser.add_argument(
        '--audio-dir',
        default='data/audio_segments',
        help='Directory with audio files (default: data/audio_segments)'
    )
    parser.add_argument(
        '--output-dir',
        default='dataset_parquet',
        help='Output directory for Parquet files (default: dataset_parquet)'
    )
    parser.add_argument(
        '--train-ratio',
        type=float,
        default=0.8,
        help='Training set ratio (default: 0.8)'
    )
    parser.add_argument(
        '--val-ratio',
        type=float,
        default=0.1,
        help='Validation set ratio (default: 0.1)'
    )
    parser.add_argument(
        '--test-ratio',
        type=float,
        default=0.1,
        help='Test set ratio (default: 0.1)'
    )
    parser.add_argument(
        '--random-seed',
        type=int,
        default=42,
        help='Random seed for reproducibility (default: 42)'
    )
    parser.add_argument(
        '--no-audio',
        action='store_true',
        help='Export without audio (metadata only)'
    )
    parser.add_argument(
        '--private',
        action='store_true',
        help='Create private Hugging Face repository'
    )
    parser.add_argument(
        '--no-upload',
        action='store_true',
        help='Skip upload to Hugging Face (only create Parquet files)'
    )

    args = parser.parse_args()

    # Check transcripts directory
    transcripts_dir = Path(args.data_dir) / 'transcripts'
    if not transcripts_dir.exists():
        transcripts_dir = Path(args.data_dir)
        if not transcripts_dir.exists():
            print(f"[X] Error: Transcripts directory not found: {transcripts_dir}")
            return 1

    # Check authentication if uploading
    if not args.no_upload:
        try:
            api = HfApi()
            api.whoami()
            print("[OK] Authenticated with Hugging Face")
        except Exception:
            print("\n[X] Not authenticated with Hugging Face")
            print("Please login first: huggingface-cli login")
            return 1

    print("="*70)
    print("ATC DATASET PREPARATION AND UPLOAD")
    print("="*70)
    print(f"\nConfiguration:")
    print(f"  Transcripts: {transcripts_dir}")
    print(f"  Audio: {args.audio_dir}")
    print(f"  Output: {args.output_dir}")
    print(f"  Split: {args.train_ratio:.0%} train / {args.val_ratio:.0%} val / {args.test_ratio:.0%} test")
    print(f"  Random seed: {args.random_seed}")
    print(f"  Include audio: {not args.no_audio}")
    if not args.no_upload:
        print(f"  Upload to: {args.repo_id}")
        print(f"  Private: {args.private}")

    # Confirm
    response = input("\nProceed? (yes/no): ").strip().lower()
    if response not in ['yes', 'y']:
        print("Cancelled.")
        return 0

    # Prepare dataset
    prep = DatasetPreparation(
        transcripts_dir=str(transcripts_dir),
        audio_dir=args.audio_dir,
        output_dir=args.output_dir,
        train_ratio=args.train_ratio,
        val_ratio=args.val_ratio,
        test_ratio=args.test_ratio,
        random_seed=args.random_seed,
        include_audio=not args.no_audio
    )

    # Load transcripts
    videos_data = prep.load_transcripts()
    if not videos_data:
        print("[X] No data to process")
        return 1

    # Create Parquet files
    parquet_files = prep.create_parquet_files(videos_data)

    # Print summary
    prep.print_summary()

    # Upload to Hugging Face
    if not args.no_upload:
        uploader = HuggingFaceUploader(
            repo_id=args.repo_id,
            private=args.private
        )
        success = uploader.upload(parquet_files, prep.stats)
        if not success:
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
