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
from typing import List, Dict
from tqdm import tqdm

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from dataset import (
    load_transcripts,
    split_videos,
    DatasetStatistics,
)


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

        # Statistics
        self.stats = DatasetStatistics()

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
                    self.stats.missing_audio += 1
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

        # Split videos using shared utility
        train_videos, val_videos, test_videos = split_videos(
            videos_data,
            self.train_ratio,
            self.val_ratio,
            self.test_ratio,
            self.random_seed,
            verbose=True
        )

        # Update statistics
        self.stats.train_videos = len(train_videos)
        self.stats.train_segments = sum(len(videos_data[vid]) for vid in train_videos)
        self.stats.val_videos = len(val_videos)
        self.stats.val_segments = sum(len(videos_data[vid]) for vid in val_videos)
        self.stats.test_videos = len(test_videos)
        self.stats.test_segments = sum(len(videos_data[vid]) for vid in test_videos)

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

        if self.stats.missing_audio > 0:
            print(f"\n[!] Warning: {self.stats.missing_audio} audio files not found")

    def create_dataset_info(self):
        """Create dataset info file."""
        info_file = self.output_dir / "dataset_info.txt"

        with open(info_file, 'w', encoding='utf-8') as f:
            f.write("="*70 + "\n")
            f.write("ATC DATASET - MANIFEST FORMAT\n")
            f.write("="*70 + "\n\n")

            f.write("DATASET STATISTICS\n")
            f.write("-"*70 + "\n")
            f.write(f"Total Videos: {self.stats.total_videos}\n")
            f.write(f"Total Segments: {self.stats.total_segments:,}\n\n")

            f.write("SPLIT STATISTICS\n")
            f.write("-"*70 + "\n")
            f.write(f"Train: {self.stats.train_videos} videos, {self.stats.train_segments:,} segments\n")
            f.write(f"Validation: {self.stats.val_videos} videos, {self.stats.val_segments:,} segments\n")
            f.write(f"Test: {self.stats.test_videos} videos, {self.stats.test_segments:,} segments\n\n")

            f.write("FILES\n")
            f.write("-"*70 + "\n")
            f.write("- train_manifest.json\n")
            f.write("- validation_manifest.json\n")
            f.write("- test_manifest.json\n")

            if self.copy_audio:
                f.write("- train_audio/\n")
                f.write("- validation_audio/\n")
                f.write("- test_audio/\n")

            f.write("\n" + "="*70 + "\n")

        print(f"\n[OK] Created dataset info: {info_file}")

    def run(self):
        """Run the manifest preparation pipeline."""
        print("="*70)
        print("ATC DATASET MANIFEST PREPARATION")
        print("="*70)
        print(f"Transcripts directory: {self.transcripts_dir.absolute()}")
        print(f"Audio directory: {self.audio_dir.absolute()}")
        print(f"Output directory: {self.output_dir.absolute()}")
        print(f"Copy audio: {self.copy_audio}")

        # Load transcripts using shared utility
        videos_data = load_transcripts(self.transcripts_dir, return_grouped=True, verbose=True)

        if not videos_data:
            print("\n[X] No transcripts found")
            return False

        # Update statistics
        self.stats.total_videos = len(videos_data)
        self.stats.total_segments = sum(len(segments) for segments in videos_data.values())

        # Create manifests
        self.create_manifests(videos_data)

        # Create dataset info
        self.create_dataset_info()

        # Print summary
        print("\n" + "="*70)
        print("MANIFEST PREPARATION COMPLETE")
        print("="*70)
        print(f"Output directory: {self.output_dir.absolute()}")
        print("="*70)

        return True


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Prepare ATC dataset in manifest format"
    )
    parser.add_argument(
        '--data-dir',
        default='data/preprocessed',
        help='Directory containing preprocessed transcripts (default: data/preprocessed)'
    )
    parser.add_argument(
        '--audio-dir',
        default='data/audio_segments',
        help='Directory containing audio WAV files (default: data/audio_segments)'
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
        help='Use absolute paths instead of copying audio files'
    )

    args = parser.parse_args()

    # Check if transcripts directory exists
    transcripts_dir = Path(args.data_dir) / 'transcripts'
    if not transcripts_dir.exists():
        # Try using data_dir directly
        transcripts_dir = Path(args.data_dir)
        if not transcripts_dir.exists():
            print(f"[X] Error: Transcripts directory not found: {transcripts_dir}")
            return 1

    # Initialize preparation
    preparation = ManifestDatasetPreparation(
        transcripts_dir=str(transcripts_dir),
        audio_dir=args.audio_dir,
        output_dir=args.output_dir,
        train_ratio=args.train_ratio,
        val_ratio=args.val_ratio,
        test_ratio=args.test_ratio,
        random_seed=args.random_seed,
        copy_audio=not args.no_copy_audio
    )

    # Run preparation
    success = preparation.run()

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
