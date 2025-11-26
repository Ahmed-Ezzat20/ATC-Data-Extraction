#!/usr/bin/env python3
"""
Data Validation Script

Validates that all data components are properly synchronized across the pipeline phases.
Checks:
- Transcript files exist and are valid JSON
- Audio segments exist for each transcript segment
- CSV outputs match transcript data
- Analysis reports are present and consistent

Usage:
    python validate_data.py [--data-dir DATA_DIR]
"""

import json
import csv
import sys
from pathlib import Path
from typing import Dict, List, Tuple
from collections import defaultdict


class DataValidator:
    """Validates synchronization across all pipeline data components."""

    def __init__(self, data_dir: str = "data"):
        """
        Initialize validator.

        Args:
            data_dir: Base data directory
        """
        self.data_dir = Path(data_dir)
        self.transcripts_dir = self.data_dir / "transcripts"
        self.audio_segments_dir = self.data_dir / "audio_segments"
        self.raw_audio_dir = self.data_dir / "raw_audio"
        self.visualizations_dir = self.data_dir / "visualizations"

        self.errors = []
        self.warnings = []
        self.info = []

    def validate_transcripts(self) -> Tuple[int, int, Dict]:
        """
        Validate transcript files.

        Returns:
            Tuple of (video_count, segment_count, transcript_data)
        """
        print("\n[1/6] Validating Transcripts...")
        print("-" * 70)

        transcript_files = sorted(self.transcripts_dir.glob("*.json"))
        # Exclude raw files
        transcript_files = [f for f in transcript_files if not f.stem.endswith('_raw')]

        if not transcript_files:
            self.errors.append("No transcript files found")
            return 0, 0, {}

        video_count = len(transcript_files)
        total_segments = 0
        transcript_data = {}

        for json_file in transcript_files:
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # Validate structure
                required_keys = ['video_id', 'segments']
                missing_keys = [k for k in required_keys if k not in data]
                if missing_keys:
                    self.errors.append(
                        f"{json_file.name}: Missing required keys: {missing_keys}"
                    )
                    continue

                # Validate segments
                segments = data['segments']
                if not segments:
                    self.warnings.append(f"{json_file.name}: No segments found")
                    continue

                video_id = data['video_id']
                transcript_data[video_id] = segments
                total_segments += len(segments)

                # Validate each segment
                for i, seg in enumerate(segments):
                    required_seg_keys = [
                        'segment_num', 'start_time', 'duration', 'transcript'
                    ]
                    missing_seg_keys = [k for k in required_seg_keys if k not in seg]
                    if missing_seg_keys:
                        self.errors.append(
                            f"{json_file.name} segment {i}: Missing keys: {missing_seg_keys}"
                        )

            except json.JSONDecodeError as e:
                self.errors.append(f"{json_file.name}: Invalid JSON - {e}")
            except Exception as e:
                self.errors.append(f"{json_file.name}: Error - {e}")

        self.info.append(f"Found {video_count} transcript files")
        self.info.append(f"Total segments in transcripts: {total_segments:,}")
        print(f"  [OK] {video_count} transcript files")
        print(f"  [OK] {total_segments:,} total segments")

        return video_count, total_segments, transcript_data

    def validate_audio_segments(self, transcript_data: Dict) -> int:
        """
        Validate audio segment files match transcripts.

        Args:
            transcript_data: Dictionary of video_id -> segments

        Returns:
            Count of audio files
        """
        print("\n[2/6] Validating Audio Segments...")
        print("-" * 70)

        if not self.audio_segments_dir.exists():
            self.errors.append("Audio segments directory does not exist")
            return 0

        audio_files = list(self.audio_segments_dir.glob("*.wav"))
        audio_count = len(audio_files)

        if not audio_files:
            self.warnings.append("No audio segment files found")
            return 0

        # Check that each transcript segment has corresponding audio
        expected_segments = 0
        missing_audio = []

        for video_id, segments in transcript_data.items():
            for seg in segments:
                expected_segments += 1
                seg_num = seg['segment_num']
                audio_filename = f"{video_id}_seg{seg_num:03d}.wav"
                audio_path = self.audio_segments_dir / audio_filename

                if not audio_path.exists():
                    missing_audio.append(audio_filename)

        if missing_audio:
            self.errors.append(
                f"Missing {len(missing_audio)} audio files for transcript segments"
            )
            if len(missing_audio) <= 10:
                for fname in missing_audio:
                    self.errors.append(f"  - {fname}")
            else:
                self.errors.append(f"  - First 10: {', '.join(missing_audio[:10])}")

        # Check for orphaned audio files (audio without transcript)
        expected_filenames = set()
        for video_id, segments in transcript_data.items():
            for seg in segments:
                seg_num = seg['segment_num']
                expected_filenames.add(f"{video_id}_seg{seg_num:03d}.wav")

        actual_filenames = {f.name for f in audio_files}
        orphaned = actual_filenames - expected_filenames

        if orphaned:
            self.warnings.append(
                f"Found {len(orphaned)} orphaned audio files (no matching transcript)"
            )
            if len(orphaned) <= 10:
                for fname in orphaned:
                    self.warnings.append(f"  - {fname}")

        self.info.append(f"Found {audio_count:,} audio segment files")
        print(f"  [OK] {audio_count:,} audio segment files")

        if missing_audio:
            print(f"  [X] {len(missing_audio)} missing audio files")

        if orphaned:
            print(f"  ! {len(orphaned)} orphaned audio files")

        return audio_count

    def validate_csv_outputs(self, expected_segments: int) -> bool:
        """
        Validate CSV output files.

        Args:
            expected_segments: Expected number of segments

        Returns:
            True if valid
        """
        print("\n[3/6] Validating CSV Outputs...")
        print("-" * 70)

        csv_files = {
            'all_segments.csv': ['audio_filename', 'transcription'],
            'all_segments_detailed.csv': [
                'audio_filename', 'transcription', 'video_id',
                'segment_num', 'start_time', 'duration', 'timestamp_range'
            ]
        }

        all_valid = True

        for csv_name, expected_cols in csv_files.items():
            csv_path = self.data_dir / csv_name

            if not csv_path.exists():
                self.warnings.append(f"CSV file not found: {csv_name}")
                print(f"  ! {csv_name} not found")
                all_valid = False
                continue

            try:
                with open(csv_path, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)

                    # Check columns
                    if reader.fieldnames != expected_cols:
                        self.errors.append(
                            f"{csv_name}: Unexpected columns. "
                            f"Expected {expected_cols}, got {reader.fieldnames}"
                        )
                        all_valid = False

                    # Count rows
                    rows = list(reader)
                    row_count = len(rows)

                    if row_count != expected_segments:
                        self.errors.append(
                            f"{csv_name}: Row count mismatch. "
                            f"Expected {expected_segments:,}, got {row_count:,}"
                        )
                        all_valid = False
                    else:
                        print(f"  [OK] {csv_name}: {row_count:,} rows")
                        self.info.append(f"{csv_name}: {row_count:,} rows")

            except Exception as e:
                self.errors.append(f"{csv_name}: Error reading - {e}")
                all_valid = False

        return all_valid

    def validate_analysis_report(self) -> bool:
        """
        Validate analysis report exists and has expected structure.

        Returns:
            True if valid
        """
        print("\n[4/6] Validating Analysis Report...")
        print("-" * 70)

        report_path = self.data_dir / "analysis_report.txt"

        if not report_path.exists():
            self.warnings.append("Analysis report not found")
            print("  ! analysis_report.txt not found")
            return False

        try:
            with open(report_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Check for expected sections
            expected_sections = [
                "DURATION STATISTICS",
                "VOCABULARY STATISTICS",
                "TOP 30 MOST COMMON WORDS"
            ]

            for section in expected_sections:
                if section not in content:
                    self.errors.append(
                        f"Analysis report missing section: {section}"
                    )
                    return False

            print(f"  [OK] analysis_report.txt exists and is valid")
            self.info.append("Analysis report is valid")
            return True

        except Exception as e:
            self.errors.append(f"Error reading analysis report: {e}")
            return False

    def validate_raw_audio(self, video_count: int) -> int:
        """
        Validate raw audio files.

        Args:
            video_count: Expected number of videos

        Returns:
            Count of raw audio files
        """
        print("\n[5/6] Validating Raw Audio Files...")
        print("-" * 70)

        if not self.raw_audio_dir.exists():
            self.warnings.append("Raw audio directory does not exist")
            return 0

        audio_files = list(self.raw_audio_dir.glob("*.wav"))
        audio_count = len(audio_files)

        if audio_count == 0:
            self.warnings.append("No raw audio files found")
            print("  ! No raw audio files")
        else:
            print(f"  [OK] {audio_count} raw audio files")
            self.info.append(f"Found {audio_count} raw audio files")

            if audio_count != video_count:
                self.warnings.append(
                    f"Raw audio count ({audio_count}) doesn't match "
                    f"video count ({video_count})"
                )

        return audio_count

    def validate_visualizations(self) -> bool:
        """
        Validate visualization files exist.

        Returns:
            True if visualizations found
        """
        print("\n[6/6] Validating Visualizations...")
        print("-" * 70)

        if not self.visualizations_dir.exists():
            self.warnings.append("Visualizations directory does not exist")
            print("  ! Visualizations directory not found")
            return False

        viz_files = list(self.visualizations_dir.glob("*.png"))
        viz_count = len(viz_files)

        if viz_count == 0:
            self.warnings.append("No visualization files found")
            print("  ! No visualization files")
            return False

        print(f"  [OK] {viz_count} visualization files")
        self.info.append(f"Found {viz_count} visualization files")
        return True

    def print_summary(self, video_count: int, segment_count: int,
                     audio_count: int):
        """
        Print validation summary.

        Args:
            video_count: Number of videos
            segment_count: Number of segments
            audio_count: Number of audio files
        """
        print("\n" + "=" * 70)
        print("VALIDATION SUMMARY")
        print("=" * 70)

        print(f"\nData Components:")
        print(f"  Videos: {video_count}")
        print(f"  Transcript segments: {segment_count:,}")
        print(f"  Audio segments: {audio_count:,}")

        if segment_count == audio_count and segment_count > 0:
            print(f"\n[OK] SYNC STATUS: All components synchronized")
        else:
            print(f"\n[ERROR] SYNC STATUS: Components NOT synchronized")

        if self.errors:
            print(f"\n[X] ERRORS ({len(self.errors)}):")
            for error in self.errors:
                print(f"  - {error}")

        if self.warnings:
            print(f"\n! WARNINGS ({len(self.warnings)}):")
            for warning in self.warnings:
                print(f"  - {warning}")

        if self.info:
            print(f"\n[i] INFO:")
            for info_msg in self.info:
                print(f"  - {info_msg}")

        print("\n" + "=" * 70)

        # Return exit code
        if self.errors:
            return 1
        return 0

    def validate_all(self) -> int:
        """
        Run all validations.

        Returns:
            Exit code (0 = success, 1 = errors found)
        """
        print("=" * 70)
        print("DATA SYNCHRONIZATION VALIDATOR")
        print("=" * 70)
        print(f"Data directory: {self.data_dir.absolute()}")

        # Phase 1: Transcripts
        video_count, segment_count, transcript_data = self.validate_transcripts()

        # Phase 2: Audio segments
        audio_count = self.validate_audio_segments(transcript_data)

        # Phase 3: CSV outputs
        self.validate_csv_outputs(segment_count)

        # Phase 4: Analysis report
        self.validate_analysis_report()

        # Phase 5: Raw audio
        self.validate_raw_audio(video_count)

        # Phase 6: Visualizations
        self.validate_visualizations()

        # Summary
        return self.print_summary(video_count, segment_count, audio_count)


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Validate data synchronization across pipeline phases"
    )
    parser.add_argument(
        '--data-dir',
        default='data',
        help='Base data directory (default: data)'
    )

    args = parser.parse_args()

    validator = DataValidator(args.data_dir)
    exit_code = validator.validate_all()

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
