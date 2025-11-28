#!/usr/bin/env python3
"""
Prepare ATC Dataset in Manifest Format

Creates train/validation/test splits and exports in manifest.json format.
Each line in the manifest is a JSON object with:
- audio_filepath: Path to WAV file (relative to manifest location)
- text: Transcription
- duration: Duration in seconds

Audio files are organized into split-specific directories (train_audio/, validation_audio/, test_audio/)
and referenced with relative paths in the manifest files.

Usage:
    python prepare_manifest_dataset.py --data-dir data/preprocessed --audio-dir data/audio_segments --output-dir dataset_manifest
"""

import argparse
import json
import sys
import shutil
from pathlib import Path
from typing import List, Dict, Tuple
from tqdm import tqdm
import random


class ManifestDatasetPreparation:
    """Prepare dataset in manifest format."""

    def __init__(
        self,
        transcripts_dir: str,
        audio_dir: str,
        output_dir: str = "dataset_manifest",
        train_ratio: float = 0.95,
        val_ratio: float = 0.025,
        test_ratio: float = 0.025,
        random_seed: int = 42,
        copy_audio: bool = True
    ):
        """
        Initialize dataset preparation.

        Args:
            transcripts_dir: Directory containing transcript JSON files
            audio_dir: Directory containing audio WAV files
            output_dir: Output directory for manifest files
            train_ratio: Ratio for training set (default: 0.95)
            val_ratio: Ratio for validation set (default: 0.025)
            test_ratio: Ratio for test set (default: 0.025)
            random_seed: Random seed for reproducibility
            copy_audio: Whether to copy audio files to output directories
        """
        self.transcripts_dir = Path(transcripts_dir)
        self.audio_dir = Path(audio_dir)
        self.output_dir = Path(output_dir)
        self.train_ratio = train_ratio
        self.val_ratio = val_ratio
        self.test_ratio = test_ratio
        self.random_seed = random_seed
        self.copy_audio = copy_audio

        # Validate split ratios
        total_ratio = train_ratio + val_ratio + test_ratio
        if not (0.99 < total_ratio < 1.01):
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

    def create_manifest(
        self,
        videos_data: Dict[str, List[Dict]],
        video_ids: List[str],
        split_name: str
    ) -> List[Dict]:
        """
        Create manifest entries for a specific split.

        Args:
            videos_data: All videos data
            video_ids: Video IDs for this split
            split_name: Name of the split

        Returns:
            List of manifest entries
        """
        print(f"\n  Creating {split_name} manifest...")

        # Create output audio directory if copying files
        if self.copy_audio:
            audio_output_dir = self.output_dir / f"{split_name}_audio"
            audio_output_dir.mkdir(parents=True, exist_ok=True)
        else:
            audio_output_dir = None

        manifest_entries = []
        audio_counter = 0

        for video_id in tqdm(video_ids, desc=f"  Processing {split_name}"):
            for segment in videos_data[video_id]:
                # Original audio filename
                original_audio_filename = f"{video_id}_seg{segment['segment_num']:03d}.wav"
                original_audio_path = self.audio_dir / original_audio_filename

                # Check if audio exists
                if not original_audio_path.exists():
                    self.stats['missing_audio'] += 1
                    continue

                # Determine output audio path
                if self.copy_audio:
                    # Sequential naming: audio_000000.wav, audio_000001.wav, etc.
                    new_audio_filename = f"audio_{audio_counter:06d}.wav"
                    output_audio_path = audio_output_dir / new_audio_filename

                    # Copy audio file
                    shutil.copy2(original_audio_path, output_audio_path)

                    # Audio filepath for manifest (relative to manifest file location)
                    # Both manifest and audio directory are in output_dir
                    audio_filepath = f"{split_name}_audio/{new_audio_filename}"
                else:
                    # Use original audio path (absolute)
                    audio_filepath = str(original_audio_path.absolute())

                # Create manifest entry
                manifest_entry = {
                    "audio_filepath": audio_filepath,
                    "text": segment['transcript'],
                    "duration": segment['duration']
                }

                manifest_entries.append(manifest_entry)
                audio_counter += 1

        return manifest_entries

    def write_manifest(self, manifest_entries: List[Dict], split_name: str):
        """
        Write manifest to file in JSONL format.

        Args:
            manifest_entries: List of manifest entries
            split_name: Name of the split
        """
        manifest_file = self.output_dir / f"{split_name}_manifest.json"

        print(f"  Writing {split_name} manifest: {manifest_file.name}")

        with open(manifest_file, 'w', encoding='utf-8') as f:
            for entry in manifest_entries:
                f.write(json.dumps(entry, ensure_ascii=False) + '\n')

        print(f"  [OK] {split_name}: {len(manifest_entries):,} entries")

    def create_manifests(self, videos_data: Dict[str, List[Dict]]):
        """
        Create manifest files for all splits.

        Args:
            videos_data: All videos data
        """
        print("\n" + "="*70)
        print("CREATING MANIFEST FILES")
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

        for split_name, video_ids in splits.items():
            if not video_ids:
                print(f"  [!] Skipping {split_name} (no videos)")
                continue

            # Create manifest entries
            manifest_entries = self.create_manifest(videos_data, video_ids, split_name)

            # Write manifest file
            if manifest_entries:
                self.write_manifest(manifest_entries, split_name)

        if self.stats['missing_audio'] > 0:
            print(f"\n[!] Warning: {self.stats['missing_audio']} audio files not found")

    def create_dataset_info(self):
        """Create dataset info file."""
        info_file = self.output_dir / "dataset_info.txt"

        info_content = f"""ATC Dataset - Manifest Format
{'='*70}

Dataset Statistics:
  Total videos: {self.stats['total_videos']}
  Total segments: {self.stats['total_segments']:,}

Split Breakdown:
  Train:
    Videos: {self.stats['train_videos']} ({self.stats['train_videos']/self.stats['total_videos']*100:.1f}%)
    Segments: {self.stats['train_segments']:,} ({self.stats['train_segments']/self.stats['total_segments']*100:.1f}%)
    File: train_manifest.json

  Validation:
    Videos: {self.stats['val_videos']} ({self.stats['val_videos']/self.stats['total_videos']*100:.1f}%)
    Segments: {self.stats['val_segments']:,} ({self.stats['val_segments']/self.stats['total_segments']*100:.1f}%)
    File: validation_manifest.json

  Test:
    Videos: {self.stats['test_videos']} ({self.stats['test_videos']/self.stats['total_videos']*100:.1f}%)
    Segments: {self.stats['test_segments']:,} ({self.stats['test_segments']/self.stats['total_segments']*100:.1f}%)
    File: test_manifest.json

Configuration:
  Random seed: {self.random_seed}
  Audio copied: {self.copy_audio}
  Audio paths: Relative to manifest file location
  Missing audio files: {self.stats['missing_audio']:,}

Manifest Format:
  Each line is a JSON object with:
  - audio_filepath: Path to WAV file
  - text: Transcription
  - duration: Duration in seconds

Usage Example (Python):
  import json

  # Load manifest
  with open('train_manifest.json', 'r') as f:
      data = [json.loads(line) for line in f]

  # Access first sample
  sample = data[0]
  print(f"Audio: {{sample['audio_filepath']}}")
  print(f"Text: {{sample['text']}}")
  print(f"Duration: {{sample['duration']}} seconds")

Usage Example (NeMo):
  from nemo.collections.asr.data import audio_to_text_dataset

  dataset = audio_to_text_dataset.get_audio_to_text_char_dataset_from_manifest(
      manifest_filepath='train_manifest.json',
      labels=labels,
      ...
  )

{'='*70}
"""

        with open(info_file, 'w', encoding='utf-8') as f:
            f.write(info_content)

        print(f"\n[OK] Dataset info created: {info_file}")

    def print_summary(self):
        """Print dataset summary."""
        print("\n" + "="*70)
        print("DATASET PREPARATION SUMMARY")
        print("="*70)

        print(f"\nTotal dataset:")
        print(f"  Videos: {self.stats['total_videos']}")
        print(f"  Segments: {self.stats['total_segments']:,}")

        print(f"\nSplit breakdown:")
        print(f"  Train: {self.stats['train_segments']:,} segments ({self.stats['train_segments']/self.stats['total_segments']*100:.1f}%)")
        print(f"  Validation: {self.stats['val_segments']:,} segments ({self.stats['val_segments']/self.stats['total_segments']*100:.1f}%)")
        print(f"  Test: {self.stats['test_segments']:,} segments ({self.stats['test_segments']/self.stats['total_segments']*100:.1f}%)")

        if self.stats['missing_audio'] > 0:
            print(f"\nWarning: {self.stats['missing_audio']:,} audio files not found")

        print(f"\nOutput directory: {self.output_dir.absolute()}")
        print(f"\nManifest files:")
        print(f"  - train_manifest.json")
        print(f"  - validation_manifest.json")
        print(f"  - test_manifest.json")

        if self.copy_audio:
            print(f"\nAudio directories:")
            print(f"  - train_audio/")
            print(f"  - validation_audio/")
            print(f"  - test_audio/")

        print("="*70)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Prepare ATC dataset in manifest format"
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
        default='dataset_manifest',
        help='Output directory for manifest files (default: dataset_manifest)'
    )
    parser.add_argument(
        '--train-ratio',
        type=float,
        default=0.95,
        help='Training set ratio (default: 0.95)'
    )
    parser.add_argument(
        '--val-ratio',
        type=float,
        default=0.025,
        help='Validation set ratio (default: 0.025)'
    )
    parser.add_argument(
        '--test-ratio',
        type=float,
        default=0.025,
        help='Test set ratio (default: 0.025)'
    )
    parser.add_argument(
        '--random-seed',
        type=int,
        default=42,
        help='Random seed for reproducibility (default: 42)'
    )
    parser.add_argument(
        '--no-copy-audio',
        action='store_true',
        help='Do not copy audio files (use original paths in manifest)'
    )

    args = parser.parse_args()

    # Check transcripts directory
    transcripts_dir = Path(args.data_dir) / 'transcripts'
    if not transcripts_dir.exists():
        transcripts_dir = Path(args.data_dir)
        if not transcripts_dir.exists():
            print(f"[X] Error: Transcripts directory not found: {transcripts_dir}")
            return 1

    # Check audio directory
    audio_dir = Path(args.audio_dir)
    if not audio_dir.exists():
        print(f"[X] Error: Audio directory not found: {audio_dir}")
        return 1

    print("="*70)
    print("ATC DATASET PREPARATION - MANIFEST FORMAT")
    print("="*70)
    print(f"\nConfiguration:")
    print(f"  Transcripts: {transcripts_dir}")
    print(f"  Audio: {audio_dir}")
    print(f"  Output: {args.output_dir}")
    print(f"  Split: {args.train_ratio:.0%} train / {args.val_ratio:.0%} val / {args.test_ratio:.0%} test")
    print(f"  Random seed: {args.random_seed}")
    print(f"  Copy audio: {not args.no_copy_audio}")
    print(f"  Audio paths: Relative to manifest file")

    # Confirm
    response = input("\nProceed? (yes/no): ").strip().lower()
    if response not in ['yes', 'y']:
        print("Cancelled.")
        return 0

    # Prepare dataset
    prep = ManifestDatasetPreparation(
        transcripts_dir=str(transcripts_dir),
        audio_dir=str(audio_dir),
        output_dir=args.output_dir,
        train_ratio=args.train_ratio,
        val_ratio=args.val_ratio,
        test_ratio=args.test_ratio,
        random_seed=args.random_seed,
        copy_audio=not args.no_copy_audio
    )

    # Load transcripts
    videos_data = prep.load_transcripts()
    if not videos_data:
        print("[X] No data to process")
        return 1

    # Create manifests
    prep.create_manifests(videos_data)

    # Create dataset info
    prep.create_dataset_info()

    # Print summary
    prep.print_summary()

    print("\n[OK] Dataset preparation complete!")

    return 0


if __name__ == "__main__":
    sys.exit(main())
