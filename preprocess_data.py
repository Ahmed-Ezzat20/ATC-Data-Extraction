#!/usr/bin/env python3
"""
ATC Data Preprocessing Script

Preprocesses ATC transcriptions with:
- Spelling corrections
- Diacritic normalization
- Letter-to-phonetic word mappings
- Number-to-word conversions
- Capitalization normalization
- Tag removal and filtering

Usage:
    python preprocess_data.py --data-dir data [options]
"""

import argparse
import json
import csv
import sys
from pathlib import Path
from typing import Dict, List
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.preprocessing.normalizer import ATCTextNormalizer
from src.preprocessing.filters import TransmissionFilter


class DataPreprocessor:
    """Preprocess ATC dataset with normalization and filtering."""

    def __init__(
        self,
        data_dir: str = "data",
        output_dir: str = "data/preprocessed",
        normalizer: ATCTextNormalizer = None,
        filter: TransmissionFilter = None,
    ):
        """
        Initialize the preprocessor.

        Args:
            data_dir: Input data directory
            output_dir: Output directory for preprocessed data
            normalizer: Text normalizer (uses default if None)
            filter: Transmission filter (uses default if None)
        """
        self.data_dir = Path(data_dir)
        self.output_dir = Path(output_dir)
        self.transcripts_dir = self.data_dir / "transcripts"

        # Initialize normalizer and filter
        self.normalizer = normalizer or ATCTextNormalizer()
        self.filter = filter or TransmissionFilter()

        # Statistics
        self.stats = {
            "total_videos": 0,
            "total_segments": 0,
            "filtered_segments": 0,
            "normalization_changes": 0,
            "videos_processed": 0,
        }

    def preprocess_transcript(self, transcript_data: dict) -> dict:
        """
        Preprocess a single transcript.

        Args:
            transcript_data: Transcript dictionary

        Returns:
            Preprocessed transcript dictionary
        """
        video_id = transcript_data["video_id"]
        original_segments = transcript_data["segments"]

        processed_segments = []
        filtered_count = 0

        for segment in original_segments:
            original_text = segment["transcript"]

            # Check if should be excluded
            should_exclude, reason = self.filter.should_exclude(original_text)
            if should_exclude:
                filtered_count += 1
                continue

            # Normalize text
            normalized_text = self.normalizer.normalize_text(original_text)

            # Track changes
            if normalized_text != original_text:
                self.stats["normalization_changes"] += 1

            # Update segment
            processed_segment = segment.copy()
            processed_segment["transcript"] = normalized_text
            processed_segment["original_transcript"] = original_text

            processed_segments.append(processed_segment)

        # Update statistics
        self.stats["total_segments"] += len(original_segments)
        self.stats["filtered_segments"] += filtered_count

        # Create preprocessed transcript
        preprocessed = transcript_data.copy()
        preprocessed["segments"] = processed_segments
        preprocessed["total_segments"] = len(processed_segments)
        preprocessed["filtered_segments"] = filtered_count
        preprocessed["preprocessing_date"] = datetime.now().isoformat()

        return preprocessed

    def process_all_transcripts(self):
        """Process all transcript JSON files."""
        print("\n" + "=" * 70)
        print("PREPROCESSING TRANSCRIPTS")
        print("=" * 70)

        # Get all transcript files
        transcript_files = sorted(self.transcripts_dir.glob("*.json"))
        transcript_files = [f for f in transcript_files if not f.stem.endswith("_raw")]

        if not transcript_files:
            print("[!] No transcript files found")
            return

        print(f"Found {len(transcript_files)} transcript files")

        # Create output directory
        output_transcripts_dir = self.output_dir / "transcripts"
        output_transcripts_dir.mkdir(parents=True, exist_ok=True)

        # Process each file
        for i, transcript_file in enumerate(transcript_files, 1):
            video_id = transcript_file.stem

            print(f"\n[{i}/{len(transcript_files)}] Processing {video_id}...")

            try:
                # Load transcript
                with open(transcript_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                # Preprocess
                preprocessed = self.preprocess_transcript(data)

                # Save
                output_file = output_transcripts_dir / f"{video_id}.json"
                with open(output_file, "w", encoding="utf-8") as f:
                    json.dump(preprocessed, f, indent=2, ensure_ascii=False)

                original_count = len(data["segments"])
                kept_count = len(preprocessed["segments"])
                filtered_count = preprocessed["filtered_segments"]

                print(f"  Original: {original_count} segments")
                print(f"  Kept: {kept_count} segments")
                print(f"  Filtered: {filtered_count} segments")

                self.stats["videos_processed"] += 1

            except Exception as e:
                print(f"  [X] Error: {e}")
                continue

        self.stats["total_videos"] = len(transcript_files)

    def generate_preprocessed_csvs(self):
        """Generate CSV files from preprocessed transcripts."""
        print("\n" + "=" * 70)
        print("GENERATING PREPROCESSED CSV FILES")
        print("=" * 70)

        output_transcripts_dir = self.output_dir / "transcripts"
        transcript_files = sorted(output_transcripts_dir.glob("*.json"))

        if not transcript_files:
            print("[!] No preprocessed transcript files found")
            return

        # Prepare CSV data
        all_segments = []

        for transcript_file in transcript_files:
            with open(transcript_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            video_id = data["video_id"]

            for segment in data["segments"]:
                all_segments.append(
                    {
                        "video_id": video_id,
                        "segment_num": segment["segment_num"],
                        "audio_filename": f"{video_id}_seg{segment['segment_num']:03d}.wav",
                        "transcription": segment["transcript"],
                        "original_transcription": segment.get(
                            "original_transcript", ""
                        ),
                        "start_time": segment["start_time"],
                        "duration": segment["duration"],
                        "timestamp_range": segment["timestamp_range"],
                    }
                )

        # Generate basic CSV
        basic_csv_path = self.output_dir / "all_segments.csv"
        with open(basic_csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["audio_filename", "transcription"])
            writer.writeheader()
            for seg in all_segments:
                writer.writerow(
                    {
                        "audio_filename": seg["audio_filename"],
                        "transcription": seg["transcription"],
                    }
                )

        print(f"[OK] Created: {basic_csv_path}")
        print(f"     {len(all_segments):,} rows")

        # Generate detailed CSV
        detailed_csv_path = self.output_dir / "all_segments_detailed.csv"
        fieldnames = [
            "audio_filename",
            "transcription",
            "original_transcription",
            "video_id",
            "segment_num",
            "start_time",
            "duration",
            "timestamp_range",
        ]
        with open(detailed_csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(all_segments)

        print(f"[OK] Created: {detailed_csv_path}")
        print(f"     {len(all_segments):,} rows")

    def generate_report(self):
        """Generate preprocessing report."""
        print("\n" + "=" * 70)
        print("GENERATING PREPROCESSING REPORT")
        print("=" * 70)

        report_path = self.output_dir / "preprocessing_report.txt"

        with open(report_path, "w", encoding="utf-8") as f:
            f.write("=" * 70 + "\n")
            f.write("ATC DATA PREPROCESSING REPORT\n")
            f.write("=" * 70 + "\n\n")

            f.write(
                f"Preprocessing Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            )

            f.write("STATISTICS\n")
            f.write("-" * 70 + "\n")
            f.write(f"Total Videos: {self.stats['total_videos']}\n")
            f.write(f"Videos Processed: {self.stats['videos_processed']}\n")
            f.write(f"Total Segments (original): {self.stats['total_segments']:,}\n")
            f.write(f"Filtered Segments: {self.stats['filtered_segments']:,}\n")
            f.write(
                f"Kept Segments: {self.stats['total_segments'] - self.stats['filtered_segments']:,}\n"
            )
            f.write(
                f"Normalization Changes: {self.stats['normalization_changes']:,}\n\n"
            )

            if self.stats["total_segments"] > 0:
                filter_rate = (
                    self.stats["filtered_segments"] / self.stats["total_segments"]
                ) * 100
                change_rate = (
                    self.stats["normalization_changes"] / self.stats["total_segments"]
                ) * 100
                f.write(f"Filtering Rate: {filter_rate:.2f}%\n")
                f.write(f"Change Rate: {change_rate:.2f}%\n\n")

            f.write("NORMALIZATION SETTINGS\n")
            f.write("-" * 70 + "\n")
            f.write(
                f"Spelling Corrections: {self.normalizer.apply_spelling_corrections}\n"
            )
            f.write(
                f"Diacritic Normalization: {self.normalizer.normalize_diacritics}\n"
            )
            f.write(
                f"Phonetic Letter Expansion: {self.normalizer.expand_phonetic_letters}\n"
            )
            f.write(f"Number Expansion: {self.normalizer.expand_numbers}\n")
            f.write(f"Uppercase Conversion: {self.normalizer.uppercase}\n")
            f.write(f"Tag Removal: {self.normalizer.remove_tags}\n\n")

            f.write("FILTERING SETTINGS\n")
            f.write("-" * 70 + "\n")
            f.write(f"Exclusion Tags: {len(self.filter.exclusion_tags)}\n")
            f.write(
                f"Quality Pattern Filtering: {self.filter.exclude_quality_issues}\n"
            )
            f.write(f"Minimum Length: {self.filter.min_length} words\n")
            f.write(f"Maximum Length: {self.filter.max_length or 'None'}\n")
            f.write(f"Manual Exclusions: {len(self.filter.manual_exclusions)}\n")

            f.write("\n" + "=" * 70 + "\n")

        print(f"[OK] Report saved to: {report_path}")

    def print_summary(self):
        """Print processing summary."""
        print("\n" + "=" * 70)
        print("PREPROCESSING COMPLETE")
        print("=" * 70)

        print(
            f"\nProcessed: {self.stats['videos_processed']}/{self.stats['total_videos']} videos"
        )
        print(f"Original segments: {self.stats['total_segments']:,}")
        print(f"Filtered out: {self.stats['filtered_segments']:,}")
        print(
            f"Kept: {self.stats['total_segments'] - self.stats['filtered_segments']:,}"
        )
        print(f"Normalized: {self.stats['normalization_changes']:,} changes")

        if self.stats["total_segments"] > 0:
            filter_rate = (
                self.stats["filtered_segments"] / self.stats["total_segments"]
            ) * 100
            print(f"Filtering rate: {filter_rate:.2f}%")

        print(f"\nOutput directory: {self.output_dir.absolute()}")
        print("=" * 70)

    def run(self):
        """Run the complete preprocessing pipeline."""
        start_time = datetime.now()

        print("=" * 70)
        print("ATC DATA PREPROCESSING PIPELINE")
        print("=" * 70)
        print(f"Input directory: {self.data_dir.absolute()}")
        print(f"Output directory: {self.output_dir.absolute()}")
        print(f"Start time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")

        # Process transcripts
        self.process_all_transcripts()

        # Generate CSVs
        self.generate_preprocessed_csvs()

        # Generate report
        self.generate_report()

        # Print summary
        end_time = datetime.now()
        duration = end_time - start_time
        print(f"\nDuration: {duration}")

        self.print_summary()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Preprocess ATC transcription data")
    parser.add_argument(
        "--data-dir", default="data", help="Input data directory (default: data)"
    )
    parser.add_argument(
        "--output-dir",
        default="data/preprocessed",
        help="Output directory (default: data/preprocessed)",
    )
    parser.add_argument(
        "--no-spelling-corrections",
        action="store_true",
        help="Disable spelling corrections",
    )
    parser.add_argument(
        "--no-diacritics", action="store_true", help="Disable diacritic normalization"
    )
    parser.add_argument(
        "--no-phonetic-expansion",
        action="store_true",
        help="Disable phonetic letter expansion",
    )
    parser.add_argument(
        "--no-number-expansion",
        action="store_true",
        help="Disable number-to-word expansion",
    )
    parser.add_argument(
        "--no-uppercase", action="store_true", help="Disable uppercase conversion"
    )
    parser.add_argument(
        "--no-tag-removal", action="store_true", help="Disable tag removal"
    )
    parser.add_argument(
        "--no-filtering", action="store_true", help="Disable transmission filtering"
    )
    parser.add_argument(
        "--min-length",
        type=int,
        default=3,
        help="Minimum text length in words (default: 3)",
    )
    parser.add_argument(
        "--max-length",
        type=int,
        help="Maximum text length in words (default: no limit)",
    )
    parser.add_argument("--manual-exclusions", help="Path to manual exclusions file")

    args = parser.parse_args()

    # Initialize normalizer
    normalizer = ATCTextNormalizer(
        apply_spelling_corrections=not args.no_spelling_corrections,
        normalize_diacritics=not args.no_diacritics,
        expand_phonetic_letters=not args.no_phonetic_expansion,
        expand_numbers=not args.no_number_expansion,
        uppercase=not args.no_uppercase,
        remove_tags=not args.no_tag_removal,
    )

    # Initialize filter
    if args.no_filtering:
        # Minimal filtering (only empty texts)
        filter = TransmissionFilter(
            exclusion_tags=[],
            exclude_quality_issues=False,
            min_length=0,
            max_length=None,
        )
    else:
        filter = TransmissionFilter(
            min_length=args.min_length,
            max_length=args.max_length,
            manual_exclusions_file=args.manual_exclusions,
        )

    # Initialize preprocessor
    preprocessor = DataPreprocessor(
        data_dir=args.data_dir,
        output_dir=args.output_dir,
        normalizer=normalizer,
        filter=filter,
    )

    # Run preprocessing
    preprocessor.run()


if __name__ == "__main__":
    main()
