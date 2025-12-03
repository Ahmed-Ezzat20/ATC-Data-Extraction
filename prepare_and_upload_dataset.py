#!/usr/bin/env python3
"""
Prepare and Upload ATC Dataset to Hugging Face

Complete pipeline that:
1. Loads preprocessed transcripts
2. Optionally splits dataset into train/validation/test
3. Exports to Parquet or Manifest format
4. Optionally uploads to Hugging Face Hub

Usage:
    # Full pipeline with split and upload
    python prepare_and_upload_dataset.py --repo-id "username/atc-dataset"
    
    # Export single Parquet file without split
    python prepare_and_upload_dataset.py --no-split --no-upload --output dataset.parquet
    
    # Create manifest format
    python prepare_and_upload_dataset.py --format manifest --repo-id "username/atc-dataset"
    
    # Export without audio
    python prepare_and_upload_dataset.py --no-audio --repo-id "username/atc-dataset"
"""

import argparse
import sys
from pathlib import Path
from typing import List, Dict
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from tqdm import tqdm
import json
import shutil

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from dataset import (
    load_transcripts,
    split_videos,
    load_audio_file,
    DatasetStatistics,
    check_authentication,
    generate_dataset_card,
    upload_to_hub,
)


class DatasetPreparation:
    """Prepare and export ATC dataset in various formats."""
    
    def __init__(
        self,
        transcripts_dir: str,
        audio_dir: str,
        output_dir: str = "dataset_output",
        format_type: str = "parquet",
        include_audio: bool = True,
        do_split: bool = True,
        train_ratio: float = 0.95,
        val_ratio: float = 0.025,
        test_ratio: float = 0.025,
        random_seed: int = 42,
    ):
        """
        Initialize dataset preparation.
        
        Args:
            transcripts_dir: Directory containing transcript JSON files
            audio_dir: Directory containing audio WAV files
            output_dir: Output directory for dataset files
            format_type: Output format ('parquet' or 'manifest')
            include_audio: Whether to include audio in output
            do_split: Whether to split into train/val/test
            train_ratio: Ratio for training set
            val_ratio: Ratio for validation set
            test_ratio: Ratio for test set
            random_seed: Random seed for reproducibility
        """
        self.transcripts_dir = Path(transcripts_dir)
        self.audio_dir = Path(audio_dir)
        self.output_dir = Path(output_dir)
        self.format_type = format_type
        self.include_audio = include_audio
        self.do_split = do_split
        self.train_ratio = train_ratio
        self.val_ratio = val_ratio
        self.test_ratio = test_ratio
        self.random_seed = random_seed
        
        self.stats = DatasetStatistics()
        
        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def prepare_parquet_single(self, segments: List[Dict]) -> str:
        """
        Create a single Parquet file from all segments.
        
        Args:
            segments: List of segment dictionaries
            
        Returns:
            Path to created Parquet file
        """
        print("\n" + "="*70)
        print("CREATING PARQUET FILE")
        print("="*70)
        
        if self.include_audio:
            print("Loading audio files...")
            for segment in tqdm(segments, desc="Loading audio"):
                audio_path = self.audio_dir / segment['audio_filename']
                audio_bytes = load_audio_file(audio_path)
                
                if audio_bytes is None:
                    self.stats.missing_audio += 1
                    segment['audio'] = None
                else:
                    segment['audio'] = audio_bytes
                    self.stats.total_audio_size_mb += len(audio_bytes) / (1024 * 1024)
            
            if self.stats.missing_audio > 0:
                print(f"\n[!] Warning: {self.stats.missing_audio} audio files not found")
        
        # Create DataFrame
        print("\nCreating DataFrame...")
        df = pd.DataFrame(segments)
        
        # Define column order
        if self.include_audio:
            columns = [
                'audio_filename', 'video_id', 'segment_num',
                'transcription', 'original_transcription', 'audio',
                'start_time', 'duration', 'timestamp_range'
            ]
        else:
            columns = [
                'audio_filename', 'video_id', 'segment_num',
                'transcription', 'original_transcription',
                'start_time', 'duration', 'timestamp_range'
            ]
        
        df = df[columns]
        
        # Write to Parquet
        output_file = self.output_dir / "dataset.parquet"
        print(f"Writing to Parquet: {output_file}")
        
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
        
        # Convert to PyArrow Table and write
        table = pa.Table.from_pandas(df, schema=schema)
        pq.write_table(
            table,
            output_file,
            compression='snappy',
            use_dictionary=True,
        )
        
        print(f"[OK] Parquet file created: {output_file}")
        return str(output_file)
    
    def prepare_parquet_splits(
        self,
        videos_data: Dict[str, List[Dict]],
        train_videos: List[str],
        val_videos: List[str],
        test_videos: List[str]
    ) -> List[str]:
        """
        Create separate Parquet files for each split.
        
        Args:
            videos_data: Dictionary mapping video_id to segments
            train_videos: List of training video IDs
            val_videos: List of validation video IDs
            test_videos: List of test video IDs
            
        Returns:
            List of created Parquet file paths
        """
        print("\n" + "="*70)
        print("CREATING PARQUET FILES FOR SPLITS")
        print("="*70)
        
        output_files = []
        
        splits = {
            'train': train_videos,
            'validation': val_videos,
            'test': test_videos
        }
        
        for split_name, video_ids in splits.items():
            if not video_ids:
                print(f"\n[!] Skipping {split_name} (no videos)")
                continue
            
            print(f"\nCreating {split_name} split...")
            
            # Collect segments for this split
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
                    
                    # Load audio if needed
                    if self.include_audio:
                        audio_path = self.audio_dir / segment_data['audio_filename']
                        audio_bytes = load_audio_file(audio_path)
                        
                        if audio_bytes is None:
                            self.stats.missing_audio += 1
                            segment_data['audio'] = None
                        else:
                            segment_data['audio'] = audio_bytes
                            self.stats.total_audio_size_mb += len(audio_bytes) / (1024 * 1024)
                    
                    segments.append(segment_data)
            
            # Create DataFrame
            df = pd.DataFrame(segments)
            
            # Define column order
            if self.include_audio:
                columns = [
                    'audio_filename', 'video_id', 'segment_num',
                    'transcription', 'original_transcription', 'audio',
                    'start_time', 'duration', 'timestamp_range'
                ]
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
                columns = [
                    'audio_filename', 'video_id', 'segment_num',
                    'transcription', 'original_transcription',
                    'start_time', 'duration', 'timestamp_range'
                ]
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
            
            df = df[columns]
            
            # Write to Parquet
            output_file = self.output_dir / f"{split_name}.parquet"
            table = pa.Table.from_pandas(df, schema=schema)
            pq.write_table(
                table,
                output_file,
                compression='snappy',
                use_dictionary=True,
            )
            
            print(f"  [OK] {split_name}: {len(segments):,} segments → {output_file.name}")
            output_files.append(str(output_file))
        
        if self.stats.missing_audio > 0:
            print(f"\n[!] Warning: {self.stats.missing_audio} total audio files not found")
        
        return output_files
    
    def prepare_manifest_splits(
        self,
        videos_data: Dict[str, List[Dict]],
        train_videos: List[str],
        val_videos: List[str],
        test_videos: List[str]
    ) -> List[str]:
        """
        Create manifest files for each split.
        
        Args:
            videos_data: Dictionary mapping video_id to segments
            train_videos: List of training video IDs
            val_videos: List of validation video IDs
            test_videos: List of test video IDs
            
        Returns:
            List of created manifest file paths
        """
        print("\n" + "="*70)
        print("CREATING MANIFEST FILES")
        print("="*70)
        
        output_files = []
        
        splits = {
            'train': train_videos,
            'validation': val_videos,
            'test': test_videos
        }
        
        for split_name, video_ids in splits.items():
            if not video_ids:
                print(f"\n[!] Skipping {split_name} (no videos)")
                continue
            
            print(f"\nCreating {split_name} manifest...")
            
            # Create audio directory for this split if copying audio
            if self.include_audio:
                audio_output_dir = self.output_dir / f"{split_name}_audio"
                audio_output_dir.mkdir(parents=True, exist_ok=True)
            
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
                    
                    # Copy audio file if needed
                    if self.include_audio:
                        new_audio_filename = f"audio_{audio_counter:06d}.wav"
                        output_audio_path = audio_output_dir / new_audio_filename
                        shutil.copy2(original_audio_path, output_audio_path)
                        audio_filepath = f"{split_name}_audio/{new_audio_filename}"
                    else:
                        audio_filepath = str(original_audio_path.absolute())
                    
                    # Create manifest entry
                    manifest_entry = {
                        "audio_filepath": audio_filepath,
                        "text": segment['transcript'],
                        "duration": segment['duration']
                    }
                    
                    manifest_entries.append(manifest_entry)
                    audio_counter += 1
            
            # Write manifest file
            manifest_file = self.output_dir / f"{split_name}_manifest.json"
            with open(manifest_file, 'w', encoding='utf-8') as f:
                for entry in manifest_entries:
                    f.write(json.dumps(entry, ensure_ascii=False) + '\n')
            
            print(f"  [OK] {split_name}: {len(manifest_entries):,} entries → {manifest_file.name}")
            output_files.append(str(manifest_file))
        
        return output_files
    
    def run(self) -> Dict:
        """
        Run the dataset preparation pipeline.
        
        Returns:
            Dictionary with statistics and output file paths
        """
        print("="*70)
        print("ATC DATASET PREPARATION")
        print("="*70)
        print(f"Transcripts directory: {self.transcripts_dir.absolute()}")
        print(f"Audio directory: {self.audio_dir.absolute()}")
        print(f"Output directory: {self.output_dir.absolute()}")
        print(f"Format: {self.format_type.upper()}")
        print(f"Include audio: {self.include_audio}")
        print(f"Split dataset: {self.do_split}")
        
        # Load transcripts
        if self.do_split:
            videos_data = load_transcripts(self.transcripts_dir, return_grouped=True)
            self.stats.total_videos = len(videos_data)
            self.stats.total_segments = sum(len(segs) for segs in videos_data.values())
            
            # Split videos
            train_videos, val_videos, test_videos = split_videos(
                videos_data,
                self.train_ratio,
                self.val_ratio,
                self.test_ratio,
                self.random_seed
            )
            
            # Update stats
            self.stats.train_videos = len(train_videos)
            self.stats.train_segments = sum(len(videos_data[vid]) for vid in train_videos)
            self.stats.val_videos = len(val_videos)
            self.stats.val_segments = sum(len(videos_data[vid]) for vid in val_videos)
            self.stats.test_videos = len(test_videos)
            self.stats.test_segments = sum(len(videos_data[vid]) for vid in test_videos)
            
            # Create output files based on format
            if self.format_type == "parquet":
                output_files = self.prepare_parquet_splits(
                    videos_data, train_videos, val_videos, test_videos
                )
            else:  # manifest
                output_files = self.prepare_manifest_splits(
                    videos_data, train_videos, val_videos, test_videos
                )
        
        else:
            # Single file export (no split)
            segments = load_transcripts(self.transcripts_dir, return_grouped=False)
            self.stats.total_segments = len(segments)
            self.stats.total_videos = len(set(seg['video_id'] for seg in segments))
            
            if self.format_type == "parquet":
                output_file = self.prepare_parquet_single(segments)
                output_files = [output_file]
            else:
                raise ValueError("Manifest format requires --split option")
        
        # Print summary
        print("\n" + "="*70)
        print("PREPARATION COMPLETE")
        print("="*70)
        print(f"Total videos: {self.stats.total_videos}")
        print(f"Total segments: {self.stats.total_segments:,}")
        if self.do_split:
            print(f"Train: {self.stats.train_segments:,} segments")
            print(f"Validation: {self.stats.val_segments:,} segments")
            print(f"Test: {self.stats.test_segments:,} segments")
        if self.include_audio:
            print(f"Missing audio: {self.stats.missing_audio}")
            print(f"Total audio size: {self.stats.total_audio_size_mb:.2f} MB")
        print(f"\nOutput files:")
        for f in output_files:
            print(f"  - {f}")
        print("="*70)
        
        return {
            'stats': self.stats.to_dict(),
            'output_files': output_files
        }


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Prepare and upload ATC dataset to Hugging Face"
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
        default='dataset_output',
        help='Output directory for dataset files (default: dataset_output)'
    )
    parser.add_argument(
        '--format',
        choices=['parquet', 'manifest'],
        default='parquet',
        help='Output format (default: parquet)'
    )
    parser.add_argument(
        '--no-audio',
        action='store_true',
        help='Export without embedding audio files (metadata only)'
    )
    parser.add_argument(
        '--no-split',
        action='store_true',
        help='Export as single file without train/val/test split'
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
        '--repo-id',
        help='Hugging Face repository ID (e.g., "username/dataset-name")'
    )
    parser.add_argument(
        '--no-upload',
        action='store_true',
        help='Skip uploading to Hugging Face'
    )
    parser.add_argument(
        '--private',
        action='store_true',
        help='Create private repository on Hugging Face'
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    if not args.no_upload and not args.repo_id:
        parser.error("--repo-id is required when uploading (use --no-upload to skip)")
    
    if args.no_split and args.format == 'manifest':
        parser.error("Manifest format requires dataset splitting (remove --no-split)")
    
    # Check if transcripts directory exists
    transcripts_dir = Path(args.data_dir) / 'transcripts'
    if not transcripts_dir.exists():
        transcripts_dir = Path(args.data_dir)
        if not transcripts_dir.exists():
            print(f"[X] Error: Transcripts directory not found: {transcripts_dir}")
            return 1
    
    # Initialize and run preparation
    preparation = DatasetPreparation(
        transcripts_dir=str(transcripts_dir),
        audio_dir=args.audio_dir,
        output_dir=args.output_dir,
        format_type=args.format,
        include_audio=not args.no_audio,
        do_split=not args.no_split,
        train_ratio=args.train_ratio,
        val_ratio=args.val_ratio,
        test_ratio=args.test_ratio,
        random_seed=args.random_seed,
    )
    
    result = preparation.run()
    
    # Generate dataset card if uploading
    if not args.no_upload:
        readme_path = Path(args.output_dir) / "README.md"
        generate_dataset_card(
            stats=result['stats'],
            output_file=str(readme_path),
            has_audio=not args.no_audio,
            format_type=args.format,
            splits=['train', 'validation', 'test'] if not args.no_split else None
        )
        print(f"\n[OK] Generated dataset card: {readme_path}")
        
        # Upload to Hugging Face
        files_to_upload = result['output_files'] + [str(readme_path)]
        success = upload_to_hub(
            repo_id=args.repo_id,
            files_to_upload=files_to_upload,
            repo_type="dataset",
            private=args.private,
            commit_message="Upload ATC dataset"
        )
        
        if not success:
            return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
