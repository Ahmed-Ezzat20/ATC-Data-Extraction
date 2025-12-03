#!/usr/bin/env python3
"""
Export ATC Dataset to Parquet Format

Exports the dataset to Parquet format with embedded audio files.
Each record contains:
- audio_filename: Name of the WAV file
- video_id: YouTube video ID
- transcription: Preprocessed/final transcription
- original_transcription: Original transcription (if available)
- audio: Binary audio data (WAV file bytes)
- segment_num: Segment number
- start_time: Start time in seconds
- duration: Duration in seconds
- timestamp_range: Human-readable timestamp

Usage:
    python export_to_parquet.py --data-dir data/preprocessed --audio-dir data/audio_segments --output dataset.parquet
"""

import argparse
import json
import sys
from pathlib import Path
from typing import List, Dict
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from tqdm import tqdm


class ParquetExporter:
    """Export ATC dataset to Parquet format with embedded audio."""

    def __init__(
        self,
        transcripts_dir: str,
        audio_dir: str,
        output_file: str,
        include_audio: bool = True
    ):
        """
        Initialize the Parquet exporter.

        Args:
            transcripts_dir: Directory containing transcript JSON files
            audio_dir: Directory containing audio WAV files
            output_file: Output Parquet file path
            include_audio: Whether to include audio binary data (default: True)
        """
        self.transcripts_dir = Path(transcripts_dir)
        self.audio_dir = Path(audio_dir)
        self.output_file = Path(output_file)
        self.include_audio = include_audio

        # Statistics
        self.stats = {
            'total_segments': 0,
            'missing_audio': 0,
            'total_audio_size_mb': 0,
        }

    def load_transcripts(self) -> List[Dict]:
        """
        Load all transcript files.

        Returns:
            List of all segments from all transcripts
        """
        print("\n" + "="*70)
        print("LOADING TRANSCRIPTS")
        print("="*70)

        transcript_files = sorted(self.transcripts_dir.glob("*.json"))
        transcript_files = [f for f in transcript_files if not f.stem.endswith('_raw')]

        if not transcript_files:
            print("[!] No transcript files found")
            return []

        print(f"Found {len(transcript_files)} transcript files")

        all_segments = []

        for transcript_file in tqdm(transcript_files, desc="Loading transcripts"):
            with open(transcript_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            video_id = data['video_id']

            for segment in data['segments']:
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
                all_segments.append(segment_data)

        print(f"Loaded {len(all_segments):,} segments from {len(transcript_files)} videos")
        return all_segments

    def load_audio_file(self, audio_filename: str) -> bytes | None:
        """
        Load audio file as binary data.

        Args:
            audio_filename: Audio file name

        Returns:
            Audio file bytes or None if not found
        """
        audio_path = self.audio_dir / audio_filename

        if not audio_path.exists():
            return None

        with open(audio_path, 'rb') as f:
            return f.read()

    def create_parquet(self, segments: List[Dict]):
        """
        Create Parquet file from segments.

        Args:
            segments: List of segment dictionaries
        """
        print("\n" + "="*70)
        print("CREATING PARQUET FILE")
        print("="*70)

        if self.include_audio:
            print("Loading audio files...")
            audio_data = []
            missing_count = 0

            for segment in tqdm(segments, desc="Loading audio"):
                audio_bytes = self.load_audio_file(segment['audio_filename'])

                if audio_bytes is None:
                    missing_count += 1
                    audio_data.append(None)
                else:
                    audio_data.append(audio_bytes)
                    self.stats['total_audio_size_mb'] += len(audio_bytes) / (1024 * 1024)

            # Add audio to segments
            for i, segment in enumerate(segments):
                segment['audio'] = audio_data[i]

            self.stats['missing_audio'] = missing_count

            if missing_count > 0:
                print(f"\n[!] Warning: {missing_count} audio files not found")

        # Create DataFrame
        print("\nCreating DataFrame...")
        df = pd.DataFrame(segments)

        # Define column order
        if self.include_audio:
            columns = [
                'audio_filename',
                'video_id',
                'segment_num',
                'transcription',
                'original_transcription',
                'audio',
                'start_time',
                'duration',
                'timestamp_range'
            ]
        else:
            columns = [
                'audio_filename',
                'video_id',
                'segment_num',
                'transcription',
                'original_transcription',
                'start_time',
                'duration',
                'timestamp_range'
            ]

        df = df[columns]

        # Create output directory
        self.output_file.parent.mkdir(parents=True, exist_ok=True)

        # Write to Parquet
        print(f"Writing to Parquet: {self.output_file}")

        # Define schema with binary audio column if included
        if self.include_audio:
            schema = pa.schema([
                ('audio_filename', pa.string()),
                ('video_id', pa.string()),
                ('segment_num', pa.int64()),
                ('transcription', pa.string()),
                ('original_transcription', pa.string()),
                ('audio', pa.binary()),  # Binary audio data
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
            self.output_file,
            compression='snappy',  # Good balance of speed and compression
            use_dictionary=True,   # Compress repeated strings
        )

        self.stats['total_segments'] = len(segments)

        print(f"[OK] Parquet file created: {self.output_file}")

    def print_summary(self):
        """Print export summary."""
        print("\n" + "="*70)
        print("EXPORT SUMMARY")
        print("="*70)

        print(f"\nTotal segments: {self.stats['total_segments']:,}")

        if self.include_audio:
            print(f"Missing audio files: {self.stats['missing_audio']:,}")
            print(f"Total audio size: {self.stats['total_audio_size_mb']:.2f} MB")

        file_size = self.output_file.stat().st_size / (1024 * 1024)
        print(f"Parquet file size: {file_size:.2f} MB")

        if self.include_audio and self.stats['total_audio_size_mb'] > 0:
            compression_ratio = (self.stats['total_audio_size_mb'] / file_size) if file_size > 0 else 0
            print(f"Compression ratio: {compression_ratio:.2f}x")

        print(f"\nOutput file: {self.output_file.absolute()}")
        print("="*70)

    def export(self):
        """Run the export process."""
        print("="*70)
        print("ATC DATASET PARQUET EXPORT")
        print("="*70)
        print(f"Transcripts directory: {self.transcripts_dir.absolute()}")
        print(f"Audio directory: {self.audio_dir.absolute()}")
        print(f"Output file: {self.output_file.absolute()}")
        print(f"Include audio: {self.include_audio}")

        # Load transcripts
        segments = self.load_transcripts()

        if not segments:
            print("\n[X] No segments to export")
            return False

        # Create Parquet file
        self.create_parquet(segments)

        # Print summary
        self.print_summary()

        return True


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Export ATC dataset to Parquet format with embedded audio"
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
        '--output',
        default='atc_dataset.parquet',
        help='Output Parquet file path (default: atc_dataset.parquet)'
    )
    parser.add_argument(
        '--no-audio',
        action='store_true',
        help='Export without embedding audio files (metadata only)'
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

    # Initialize exporter
    exporter = ParquetExporter(
        transcripts_dir=str(transcripts_dir),
        audio_dir=args.audio_dir,
        output_file=args.output,
        include_audio=not args.no_audio
    )

    # Run export
    success = exporter.export()

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
